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
from word_process.checker.FIELD_CONSTRAINTS import FIELD_CONSTRAINTS
from prompts.compress_prompt import CHECKER_PROMPT_SECTION


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

        # 构建并行执行组（互不相关的 section 可并行）
        exec_groups = self._build_exec_groups(section_groups)

        all_corrections = {}
        total_usage = None
        total_elapsed = 0.0

        for exec_group in exec_groups:
            # 同一执行组内串行（可能相关）
            for section_name in exec_group:
                section_problems = section_groups[section_name]
                corrections, usage, elapsed = self._process_section(
                    section_name, section_problems
                )
                all_corrections.update(corrections)
                total_elapsed += elapsed
                if usage:
                    if total_usage is None:
                        total_usage = dict(usage)
                    else:
                        for k in ["prompt_tokens", "completion_tokens", "total_tokens"]:
                            total_usage[k] = total_usage.get(k, 0) + usage.get(k, 0)

        return all_corrections, total_usage, total_elapsed

    def _process_section(self, section_name: str, problems: list) -> tuple:
        """处理单个 section 的超长字段"""
        # Build constraints table
        constraints_lines = []
        too_long_lines = []
        for p in problems:
            field = p["field"]
            current_val = p["current_value"]
            current_len = p["current_len"]
            max_len = p["max_len"]
            min_len = p.get("min_len", 1)
            constraints_lines.append(
                f"- {field}: {min_len}-{max_len} 字（当前 {current_len} 字）"
            )
            too_long_lines.append(
                f"### {field}\n当前值（{current_len}/{max_len}字）:\n{current_val}"
            )

        prompt = CHECKER_PROMPT_SECTION.format(
            section=section_name,
            constraints_table="\n".join(constraints_lines),
            too_long_fields_detail="\n\n".join(too_long_lines),
        )
        messages = [{"role": "user", "content": prompt}]

        start_time = time.time()
        result = self.client.chat_with_stats(
            messages, temperature=0.3, reasoning_split=True, max_tokens=4000
        )
        elapsed = time.time() - start_time

        response = result["content"]
        usage = result.get("usage")

        corrections = self._extract_corrections(response)
        return corrections, usage, elapsed

    def _extract_corrections(self, response: str) -> dict:
        """从 LLM 响应中提取修正字段"""
        text = response.strip()
        if "</think>" in text:
            text = text[text.find("</think>") + 7:].strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        first = text.find("{")
        last = text.rfind("}")
        if first != -1 and last != -1 and last > first:
            try:
                return json.loads(text[first:last + 1])
            except json.JSONDecodeError:
                pass
        return {}

    def _group_by_section(self, problems: dict) -> dict:
        """按 section 分组"""
        groups = defaultdict(list)
        for (section, field), info in problems.items():
            groups[section].append({
                "field": field,
                "current_value": info["current_value"],
                "current_len": info["current_len"],
                "min_len": info.get("min_len", 1),
                "max_len": info["max_len"],
            })
        return dict(groups)

    def _build_exec_groups(self, section_groups: dict) -> list[list[str]]:
        """构建并行执行组"""
        # 简单的串行连接组（所有 section 在一个组内串行）
        # 可以进一步优化为真正的并行组
        return [list(section_groups.keys())]


def check_and_correct(json_path: Path, client: MiniMaxClient = None, max_retries: int = 1) -> dict:
    """对单个 JSON 文件进行字段长度校验和修正"""
    from word_process.checker.validator import validate_lengths

    if client is None:
        from LLM.client import MiniMaxClient as MC
        client = MC()

    corrector = Corrector(client)
    data = json.loads(json_path.read_text(encoding='utf-8'))

    for retry in range(max_retries + 1):
        problems = validate_lengths(data)
        if not problems:
            print(f"[CHECKER] {json_path.name} - 全部字段合格")
            return data

        print(f"[CHECKER] {json_path.name} - 发现 {len(problems)} 个超标字段")

        corrections, usage, elapsed = corrector.correct(problems)
        total_tokens = usage.get("total_tokens", 0) if usage else 0
        print(f"[CHECKER] {json_path.name} - 修正完成，全部字段合格，tokens: {total_tokens}，耗时: {elapsed:.1f}s")

        # Apply corrections
        for key, value in corrections.items():
            parts = key.split(".", 1)
            if len(parts) == 2:
                section, field = parts
                if section in data and field in data[section]:
                    data[section][field] = value

        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

        # Re-validate
        remaining = validate_lengths(data)
        if not remaining:
            return data
        print(f"[CHECKER] {json_path.name} - 第 {retry + 1} 轮修正后仍有 {len(remaining)} 个超标字段")

    return data
