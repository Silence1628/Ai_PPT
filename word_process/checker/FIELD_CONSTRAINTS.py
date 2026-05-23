"""
字段约束配置 - 与 word_process/llm_input/base/prompts/base_prompts.py 中的约束保持同步
仅包含需要字数检查的字段（copy模式字段如task_num/task_name无需检查）
"""

# 需要检查的字段约束：(section, field) -> (min_len, max_len)
# min_len 默认为 1，max_len 与 base_prompts.py SYSTEM_PROMPT 一致
FIELD_CONSTRAINTS = {
    # introduction
    ("introduction", "introduction_case"): (1, 190),   # summary, max_length=190
    # thinking (guiding_problems)
    ("thinking", "guiding_problem1"): (1, 30),          # summary, max_length=30
    ("thinking", "guiding_problem2"): (1, 30),          # summary, max_length=30
    ("thinking", "guiding_problem3"): (1, 30),          # summary, max_length=30
    # description 部分 - task_description 无字数限制（raw_copy模式）
    ("description", "task_requirements1"): (1, 30),
    ("description", "task_requirements2"): (1, 30),
    ("description", "task_requirements3"): (1, 30),
    ("description", "task_requirements4"): (1, 30),   # optional
    ("description", "task_requirements5"): (1, 30),    # optional
    # target 部分
    ("target", "task_target1"): (1, 30),
    ("target", "task_target2"): (1, 30),
    ("target", "task_target3"): (1, 30),
    ("target", "task_target4"): (1, 30),
    ("target", "task_focus"): (1, 30),
    ("target", "task_difficulty"): (1, 30),
    # summary 部分
    ("summary", "task_summary"): (1, 140),              # summary, max_length=140
    # key_difficulties_summary 部分
    ("key_difficulties_summary", "key_summary1"): (1, 20),
    ("key_difficulties_summary", "key_summary2"): (1, 20),
    ("key_difficulties_summary", "key_summary3"): (1, 20),
    ("key_difficulties_summary", "difficulties_summary1"): (1, 20),
    ("key_difficulties_summary", "difficulties_summary2"): (1, 20),
    ("key_difficulties_summary", "difficulties_summary3"): (1, 20),
    # expansion 部分
    ("expansion", "skill_practice"): (1, 125),          # raw_copy, max_length=125
    ("expansion", "solving_ideas"): (1, 125),            # summary, max_length=125
}