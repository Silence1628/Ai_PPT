"""
Corrector - LLM 精确字段替换
每次只上传超长字段给 LLM，LLM 返回修正后的字段，只替换这些字段
"""
import json
import re
from pathlib import Path
from LLM.client import MiniMaxClient
from .validator import validate_lengths, format_constraints_table, format_too_long_fields, write_json


# Checker 的 LLM prompt - 只上传超长字段，LLM 返回部分修改
CHECKER_PROMPT = """你是一个教育PPT内容审核助手。请压缩以下超长字段，使其符合字数限制。

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
    精确字段替换：每次只修改超长字段，不影响其他字段。
    """

    def __init__(self, client: MiniMaxClient):
        self.client = client

    def correct(self, problems: dict[str, dict]) -> dict[str, str]:
        """
        调用 LLM 修正超长字段。

        Args:
            problems: validate_lengths() 返回的超长字段信息

        Returns:
            只返回修改的字段，格式：{"section.field": "修正后的内容", ...}
        """
        # 构建 prompt
        prompt = self._build_prompt(problems)

        # 调用 LLM
        messages = [{"role": "user", "content": prompt}]
        response = self.client.chat(messages, temperature=0.3, reasoning_split=True, max_tokens=4000)

        # 提取并解析 JSON
        corrected_fields = self._extract_json(response)
        if corrected_fields is None:
            print("[CHECKER] LLM 输出无法解析或返回类型错误，保留原字段")
            return {}

        if not corrected_fields:
            print("[CHECKER] LLM 返回空字典，无需修改")

        return corrected_fields

    def _build_prompt(self, problems: dict[str, dict]) -> str:
        """构建 Checker prompt - 只上传超长字段。"""
        return CHECKER_PROMPT.format(
            constraints_table=format_constraints_table(),
            too_long_fields_detail=format_too_long_fields(problems)
        )

    def _extract_json(self, text: str) -> dict | None:
        """从 LLM 输出中提取 JSON（只包含修改的字段）。"""
        text = text.strip()

        # 移除 markdown 代码块
        if text.startswith("```"):
            text = re.sub(r"^```json?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        text = text.strip()

        # 查找 JSON 边界
        first_brace = text.find("{")
        last_brace = text.rfind("}")

        if first_brace == -1 or last_brace == -1 or last_brace <= first_brace:
            return None

        extracted = text[first_brace:last_brace + 1]

        # 尝试解析提取的内容
        try:
            result = json.loads(extracted)
        except json.JSONDecodeError:
            # 解析失败，尝试渐进扩展（处理截断情况）
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

        # 检查返回值类型（必须是 dict）
        if not isinstance(result, dict):
            print(f"[CHECKER] LLM 返回类型错误: {type(result).__name__}，期望 dict")
            return None

        return result


def check_and_correct(json_path: Path, client: MiniMaxClient, max_retries: int = 1) -> bool:
    """
    检查并修正 JSON 文件 - 精确字段替换。

    流程：
    1. 读取 JSON → 验证字数
    2. 如有超长字段 → 只上传超长字段给 LLM → LLM 返回修正后的字段 → 只替换这些字段
    3. 再次验证 → 仍超长 → 重复
    4. 两次后仍超长 → 不再修改

    Args:
        json_path: JSON 文件路径
        client: MiniMaxClient 实例
        max_retries: 最多 LLM 调用次数（默认1次，即最多2次调用）

    Returns:
        True if all fields are within limits, False if some fields still too long
    """
    corrector = Corrector(client)

    # 第1次检查
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    problems = validate_lengths(data)
    if not problems:
        print(f"[CHECKER] {json_path.name} - 全部合格，跳过")
        return True

    print(f"[CHECKER] {json_path.name} - 发现 {len(problems)} 个超长字段")

    # 最多 max_retries + 1 次调用（初始一次 + max_retries 次重试）
    for attempt in range(max_retries + 1):
        if attempt > 0:
            print(f"[CHECKER] {json_path.name} - 第 {attempt} 次修正...")
            # 重新读取最新的 JSON（已被部分修改）
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

        # 调用 LLM 修正超长字段（只上传超长字段）
        corrected_fields = corrector.correct(problems)

        if corrected_fields:
            # 只替换超长字段，不覆盖整个 JSON
            for field_path, corrected_value in corrected_fields.items():
                section, field = field_path.split(".", 1)
                if section in data and field in data[section]:
                    data[section][field] = corrected_value
                    print(f"[CHECKER] {json_path.name} - 修正: {field_path}")

            # 写回文件（只替换字段，其他字段不变）
            write_json(data, str(json_path))

        # 再次验证
        problems = validate_lengths(data)
        if not problems:
            print(f"[CHECKER] {json_path.name} - 修正完成，全部合格")
            return True

        if attempt < max_retries:
            print(f"[CHECKER] {json_path.name} - 仍有 {len(problems)} 个字段超长，继续...")

    # 两次后仍超长，不再修改
    print(f"[CHECKER] {json_path.name} - 仍有 {len(problems)} 个字段超长，不再修改")
    return False
