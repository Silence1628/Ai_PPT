"""
Checker - 独立的 JSON 字数检查与修正模块
从 Processor 剥离，专门负责 Stage 2 的长度验证和修正

总体流程：
1. Validator 检查 JSON 文件，识别所有超长字段
2. Corrector 统一调用一次 LLM 压缩所有超长字段
3. 迭代：Checker 再验证 → 仍超长则再调用一次 LLM → 最多2次
4. 两次后仍超长 → 不再做修改，正常进入 PPT 渲染
"""
from .validator import validate_lengths, format_constraints_table
from .corrector import Corrector, check_and_correct

__all__ = ["validate_lengths", "format_constraints_table", "Corrector", "check_and_correct"]