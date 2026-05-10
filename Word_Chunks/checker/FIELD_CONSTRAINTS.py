"""
字段约束配置 - 与 PPT_Framework/schemas/schemas.py 中的 max_length 保持同步
仅包含需要字数检查的字段（不含无限制的 copy 模式字段）
"""

# 需要检查的字段约束：(section, field) -> (min_len, max_len)
# min_len 默认为 1，max_len 与 schemas.py 的 max_length 一致
FIELD_CONSTRAINTS = {
    # description 部分
    ("description", "task_description"): (1, 110),    # raw_copy, max_length=110
    ("description", "task_requirements1"): (1, 30),
    ("description", "task_requirements2"): (1, 30),
    ("description", "task_requirements3"): (1, 30),
    ("description", "task_requirements4"): (1, 30),   # optional
    ("description", "task_requirements5"): (1, 30),   # optional
    # target 部分
    ("target", "task_target1"): (1, 30),
    ("target", "task_target2"): (1, 30),
    ("target", "task_target3"): (1, 30),
    ("target", "task_target4"): (1, 30),
    ("target", "task_focus"): (1, 30),
    ("target", "task_difficulty"): (1, 30),
    # summary 部分
    ("summary", "task_summary"): (1, 140),             # summary, max_length=140
    # key_difficulties_summary 部分
    ("key_difficulties_summary", "key_summary1"): (1, 20),
    ("key_difficulties_summary", "key_summary2"): (1, 20),
    ("key_difficulties_summary", "key_summary3"): (1, 20),
    ("key_difficulties_summary", "difficulties_summary1"): (1, 20),
    ("key_difficulties_summary", "difficulties_summary2"): (1, 20),
    ("key_difficulties_summary", "difficulties_summary3"): (1, 20),
    # expansion 部分
    ("expansion", "skill_practice"): (1, 125),        # raw_copy, max_length=125
    ("expansion", "solving_ideas"): (1, 125),          # summary, max_length=125
}