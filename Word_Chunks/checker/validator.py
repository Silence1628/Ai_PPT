"""
Validator - JSON 字段长度验证器
只检查超长(too_long)，不足的不处理
"""
import json
from typing import Dict
from .FIELD_CONSTRAINTS import FIELD_CONSTRAINTS

def validate_lengths(data: Dict) -> Dict[str, Dict]:
    """
    检查 JSON 数据中所有超长字段。

    Args:
        data: JSON 数据字典

    Returns:
        超长字段信息字典，格式：
        {section.field: {
            "current": str,       # 当前值
            "current_len": int,   # 当前长度
            "min_len": int,       # 最小限制
            "max_len": int        # 最大限制
        }}
        如果没有超长字段，返回空字典。
    """
    problems = {}
    for (section, field), (min_len, max_len) in FIELD_CONSTRAINTS.items():
        if section in data and field in data[section]:
            value = data[section][field]
            if isinstance(value, str) and len(value) > max_len:
                problems[f"{section}.{field}"] = {
                    "current": value,
                    "current_len": len(value),
                    "min_len": min_len,
                    "max_len": max_len
                }
    return problems


def format_constraints_table() -> str:
    """
    生成字数限制表格字符串，用于 Checker 的 LLM prompt。
    """
    lines = []
    for (section, field), (min_len, max_len) in FIELD_CONSTRAINTS.items():
        lines.append(f"  {section}.{field}: {min_len}-{max_len} 字")
    return "\n".join(lines)


def format_too_long_fields(problems: Dict[str, Dict]) -> str:
    """
    格式化超长字段详情，用于 Checker 的 LLM prompt。
    """
    lines = []
    for field_path, info in problems.items():
        section, field = field_path.split(".", 1)
        lines.append(f"【{section}.{field}】当前字数: {info['current_len']}，限制: {info['min_len']}-{info['max_len']}")
        lines.append(f"  当前内容: {info['current']}")
        lines.append("")
    return "\n".join(lines)


def write_json(data: Dict, json_path: str):
    """写回 JSON 文件。"""
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)