"""
Corrector - LLM 精确字段替换（并行分组优化版）
同一 section 的字段合并到一个 prompt，不相关的 section 并行处理
"""
import json
import re
import time
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from LLM.client import MiniMaxClient
from .validator import validate_lengths, write_json


# 字段分组配置：哪些 section 可以并行处理
# 按语义分组，无依赖关系的 section 可并行
PARALLEL_GROUPS = [
    ["introduction", "thinking"],          # 引言和引导问题可并行
    ["description", "target"],             # 描述和目标可并行
    ["summary", "key_difficulties_summary"],  # 小结和重难点可并行
    ["expansion"],                        # 拓展单独一组
]


# Checker 的 LLM prompt - 同一 section 的超长字段批量处理
CHECKER_PROMPT_SECTION = """你是一个教育PPT内容审核助手。请压缩以下【{section}】区块中的超长字段，使其符合字数限制。

【字数限制】
{constraints_table}

【待压缩字段】（只有这些字段需要处理，其他字段请忽略）
{too_long_fields_detail}

【处理要求】
1. 只返回修改后的字段，格式：{{"section.field": "修正后的内容", ...}}
2. 不要返回完整JSON，只返回修改的字段
3. 修正后的内容必须语义完整、语句通顺
4. 字数必须在规定范围内
5. 输出一行JSON，不要有markdown标记"""


class Corrector:
    """
    精确字段替换：同 section 字段批量处理，不同 section 并行调用。
    """

    def __init__(self, client: MiniMaxClient):
        self.client = client

    def correct(self, problems: dict[str, dict]) -> tuple[dict[str, str], dict | None, float]:
        """
        并行修正超长字段。

        Args:
            problems: validate_lengths() 返回的超长字段信息

        Returns:
            tuple: (所有修改的字段汇总, LLM使用统计信息, 耗时秒数)
        """
        start_time = time.time()

        # 按 section 分组
        section_groups = self._group_by_section(problems)

        # 确定并行组
        parallel_groups = self._build_parallel_groups(section_groups)

        all_corrected = {}
        total_usage = None

        # 并行执行各组
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(self._process_group, group_sections, section_groups): group_sections
                for group_sections in parallel_groups
            }
            for future in as_completed(futures):
                group_corrected, group_usage, _ = future.result()
                all_corrected.update(group_corrected)
                if total_usage is None:
                    total_usage = group_usage
                else:
                    if group_usage:
                        for k in total_usage:
                            total_usage[k] += group_usage.get(k, 0)

        elapsed = time.time() - start_time
        return all_corrected, total_usage, elapsed

    def _group_by_section(self, problems: dict[str, dict]) -> dict[str, dict]:
        """按 section 分组超长字段"""
        groups = defaultdict(dict)
        for field_path, info in problems.items():
            section, field = field_path.split(".", 1)
            groups[section][field] = info
        return groups

    def _build_parallel_groups(self, section_groups: dict[str, dict]) -> list[list[str]]:
        """根据实际有问题的 section 构建并行组"""
        active_sections = set(section_groups.keys())
        result = []
        for group_sections in PARALLEL_GROUPS:
            # 只保留实际有超长字段的 section
            filtered = [s for s in group_sections if s in active_sections]
            if filtered:
                result.append(filtered)
        return result

    def _process_group(self, sections: list[str], section_groups: dict[str, dict]) -> tuple[dict, dict | None, float]:
        """处理一组 section（串行调用 LLM，每 section 一个 prompt）"""
        group_corrected = {}
        group_usage = None
        start_time = time.time()

        for section in sections:
            fields = section_groups[section]
            prompt = self._build_section_prompt(section, fields)
            messages = [{"role": "user", "content": prompt}]
            result = self.client.chat_with_stats(messages, temperature=0.3, max_tokens=4000)
            usage = result.get("usage")
            response = result["content"]

            if usage:
                if group_usage is None:
                    group_usage = usage.copy()
                else:
                    for k in group_usage:
                        group_usage[k] += usage.get(k, 0)

            corrected = self._extract_json(response)
            if corrected:
                for field_path, value in corrected.items():
                    group_corrected[field_path] = value

        elapsed = time.time() - start_time
        return group_corrected, group_usage, elapsed

    def _build_section_prompt(self, section: str, fields: dict) -> str:
        """为单个 section 构建 prompt"""
        too_long_detail = []
        constraints_lines = []
        for field, info in fields.items():
            field_path = f"{section}.{field}"
            too_long_detail.append(f"【{field_path}】当前字数: {info['current_len']}，限制: {info['min_len']}-{info['max_len']} 字")
            too_long_detail.append(f"  当前内容: {info['current']}")
            too_long_detail.append("")
            constraints_lines.append(f"  {field_path}: {info['min_len']}-{info['max_len']} 字")

        return CHECKER_PROMPT_SECTION.format(
            section=section,
            constraints_table="\n".join(constraints_lines),
            too_long_fields_detail="\n".join(too_long_detail)
        )

    def _extract_json(self, text: str) -> dict | None:
        """从 LLM 输出中提取 JSON（只包含修改的字段）。"""
        text = text.strip()

        if text.startswith("```"):
            text = re.sub(r"^```json?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        text = text.strip()

        first_brace = text.find("{")
        last_brace = text.rfind("}")

        if first_brace == -1 or last_brace == -1 or last_brace <= first_brace:
            return None

        extracted = text[first_brace:last_brace + 1]

        try:
            result = json.loads(extracted)
        except json.JSONDecodeError:
            base_end = last_brace
            for extension in range(1, 10):
                extended = text[first_brace:base_end + extension + 1]
                try:
                    result = json.loads(extended)
                    extracted = extended
                    break
                except json.JSONDecodeError:
                    continue
            else:
                return None

        if not isinstance(result, dict):
            return None

        return result


def check_and_correct(json_path: Path, client: MiniMaxClient, max_retries: int = 1) -> tuple[bool, int, float]:
    """
    检查并修正 JSON 文件 - 并行分组修正。

    流程：
    1. 读取 JSON → 验证字数
    2. 如有超长字段 → 按 section 分组 → 并行调用 LLM → 只替换这些字段
    3. 再次验证 → 仍超长 → 重复
    4. max_retries 次后仍超长 → 不再修改
    """
    corrector = Corrector(client)
    start_time = time.time()
    total_tokens = 0

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    problems = validate_lengths(data)
    if not problems:
        elapsed = time.time() - start_time
        print(f"[CHECKER] {json_path.name} - 全部合格，跳过")
        return True, 0, elapsed

    print(f"[CHECKER] {json_path.name} - 发现 {len(problems)} 个超长字段")

    for attempt in range(max_retries + 1):
        if attempt > 0:
            print(f"[CHECKER] {json_path.name} - 第 {attempt} 次修正...")
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

        corrected_fields, usage, _ = corrector.correct(problems)

        if usage:
            total_tokens += usage.get("total_tokens", 0)

        if corrected_fields:
            for field_path, corrected_value in corrected_fields.items():
                section, field = field_path.split(".", 1)
                if section in data and field in data[section]:
                    data[section][field] = corrected_value
                    print(f"[CHECKER] {json_path.name} - 修正: {field_path}")
            write_json(data, str(json_path))

        problems = validate_lengths(data)
        if not problems:
            elapsed = time.time() - start_time
            print(f"[CHECKER] {json_path.name} - 修正完成，全部合格，消耗 tokens: {total_tokens}，耗时: {elapsed:.1f}s")
            return True, total_tokens, elapsed

        if attempt < max_retries:
            print(f"[CHECKER] {json_path.name} - 仍有 {len(problems)} 个字段超长，继续...")

    elapsed = time.time() - start_time
    print(f"[CHECKER] {json_path.name} - 仍有 {len(problems)} 个字段超长，不再修改，消耗 tokens: {total_tokens}，耗时: {elapsed:.1f}s")
    return False, total_tokens, elapsed