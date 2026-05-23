"""Prompt templates for Word chunks → JSON conversion.
All prompt strings are stored in prompts/ at project root for easy viewing.
"""

from prompts.extraction_prompt import CHUNK1_PROMPT
from prompts.base_prompt import CHUNK_TASK_PROMPT
from prompts.fix_prompt import CORRECT_FIELD_PROMPT
from prompts.reconstruction_prompt import SEMANTIC_CHUNK_PROMPT, SEMANTIC_CHUNK_RECURSIVE_PROMPT


def build_chunk1_prompt(content: str) -> str:
    """Build prompt for chunk1 processing."""
    return CHUNK1_PROMPT.replace('{content}', content)


def build_task_prompt(title: str, content: str, chunk1_data: dict) -> str:
    """Build prompt for task chunk (chunk2-4) processing."""
    prompt = CHUNK_TASK_PROMPT
    prompt = prompt.replace('{project_name}', chunk1_data.get("project_name", ""))
    prompt = prompt.replace('{introduction_case}', chunk1_data.get("introduction_case", ""))
    prompt = prompt.replace('{guiding_problem1}', chunk1_data.get("guiding_problem1", ""))
    prompt = prompt.replace('{guiding_problem2}', chunk1_data.get("guiding_problem2", ""))
    prompt = prompt.replace('{guiding_problem3}', chunk1_data.get("guiding_problem3", ""))
    prompt = prompt.replace('{title}', title)
    prompt = prompt.replace('{content}', content)
    return prompt


def build_correct_field_prompt(
    section: str,
    field: str,
    current_value: str,
    min_len: int,
    max_len: int,
    mode: str
) -> str:
    """Build prompt for single field correction (Stage 2)."""
    current_len = len(current_value)
    issue = "too_long" if current_len > max_len else "too_short"
    prompt = CORRECT_FIELD_PROMPT
    prompt = prompt.replace('{section}', section)
    prompt = prompt.replace('{field}', field)
    prompt = prompt.replace('{current_value}', current_value)
    prompt = prompt.replace('{current_len}', str(current_len))
    prompt = prompt.replace('{issue}', issue)
    prompt = prompt.replace('{min_len}', str(min_len))
    prompt = prompt.replace('{max_len}', str(max_len))
    prompt = prompt.replace('{mode}', mode)
    return prompt


def build_semantic_chunk_prompt(parent_title: str, h4_contents: list[dict]) -> str:
    """Build prompt for semantic restructuring. Sends all H4s under one H3 together."""
    parts = []
    for h4 in h4_contents:
        parts.append(f"### {h4['title']}\n{h4['content']}")
    content_block = '\n\n'.join(parts)
    prompt = SEMANTIC_CHUNK_PROMPT
    prompt = prompt.replace('{parent_title}', parent_title)
    prompt = prompt.replace('{content}', content_block)
    return prompt


def build_semantic_chunk_recursive_prompt(content: str) -> str:
    """Build prompt for recursive paragraph splitting."""
    prompt = SEMANTIC_CHUNK_RECURSIVE_PROMPT
    prompt = prompt.replace('{content}', content)
    return prompt
