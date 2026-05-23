"""任务章节 → 完整 task JSON"""

CHUNK_TASK_PROMPT = """你是一个教育PPT内容提取助手。请从以下任务章节内容中提取信息，生成完整的结构化JSON。

## 共享素材（来自chunk1，供填充使用）
chunk1_project_name: "{project_name}"
chunk1_introduction_case: "{introduction_case}"
chunk1_guiding_problem1: "{guiding_problem1}"
chunk1_guiding_problem2: "{guiding_problem2}"
chunk1_guiding_problem3: "{guiding_problem3}"

## 本任务章节内容
标题: {title}
内容:
{content}

## 输出要求
请按以下JSON结构输出。**严格遵守每个字段的mode模式和字数限制**：

{{
  "cover": {{
    "project_name": "copy模式，直接复制chunk1提取的项目名称，15-20字",
    "task_num": "copy模式，从标题2提取任务编号（如'一'），1-3字",
    "task_name": "copy模式，从标题2提取任务名称（去掉\"任务X\"编号前缀和多余空格），5-30字"
  }},
  "introduction": {{
    "introduction_case": "直接引用chunk1提取的引导案例（已由LLM重新撰写为200-220字完整版本），1-220字"
  }},
  "thinking": {{
    "guiding_problem1": "summary模式，引用chunk1素材（必须以问号结尾），1-30字",
    "guiding_problem2": "summary模式，引用chunk1素材（必须以问号结尾），1-30字",
    "guiding_problem3": "summary模式，引用chunk1素材（必须以问号结尾），1-30字"
  }},
  "start": {{
    "task_num": "copy模式，从标题2提取，1-3字",
    "task_name": "copy模式，从标题2提取（去掉\"任务X\"编号前缀），5-30字"
  }},
  "catalog_one": {{
    "task_num": "copy模式，1-3字",
    "task_name": "copy模式，20-40字"
  }},
  "catalog_two": {{
    "task_num": "copy模式，1-3字",
    "task_name": "copy模式，20-40字"
  }},
  "catalog_three": {{
    "task_num": "copy模式，1-3字",
    "task_name": "copy模式，20-40字"
  }},
  "catalog_four": {{
    "task_num": "copy模式，1-3字",
    "task_name": "copy模式，20-40字"
  }},
  "catalog_five": {{
    "task_num": "copy模式，1-3字",
    "task_name": "copy模式，20-40字"
  }},
  "catalog_six": {{
    "task_num": "copy模式，1-3字",
    "task_name": "copy模式，20-40字"
  }},
  "description": {{
    "task_description": "raw_copy模式，从【任务分析】提取任务描述部分（去掉"任务要求"段落），1-110字",
    "task_requirements1": "copy模式，1-30字（必须以分号结尾）",
    "task_requirements2": "copy模式，1-30字（必须以分号结尾）",
    "task_requirements3": "copy模式，1-30字（必须以分号结尾）",
    "task_requirements4": "copy模式，1-30字（必须以分号结尾，没有则填空字符串）",
    "task_requirements5": "copy模式，1-30字（必须以分号结尾，没有则填空字符串）"
  }},
  "target": {{
    "task_target1": "copy模式，从【学习目标】提取，1-30字（必须以分号结尾）",
    "task_target2": "copy模式，1-30字（必须以分号结尾）",
    "task_target3": "copy模式，1-30字（必须以分号结尾）",
    "task_target4": "copy模式，1-30字（必须以分号结尾）",
    "task_focus": "copy模式，综合学习目标和任务描述总结重点，1-30字（必须以分号结尾）",
    "task_difficulty": "copy模式，综合学习目标和任务描述总结难点，1-30字（必须以分号结尾）"
  }},
  "summary": {{
    "task_summary": "raw_copy模式，从【任务小结】第一段直接复制原文，不做任何提炼改写，1-140字"
  }},
  "key_difficulties_summary": {{
    "key_summary1": "summary模式，跨三块内容总结关键点，1-20字（必须以分号结尾）",
    "key_summary2": "summary模式，1-20字（必须以分号结尾）",
    "key_summary3": "summary模式，1-20字（必须以分号结尾）",
    "difficulties_summary1": "summary模式，跨三块内容总结难点，1-20字（必须以分号结尾）",
    "difficulties_summary2": "summary模式，1-20字（必须以分号结尾）",
    "difficulties_summary3": "summary模式，1-20字（必须以分号结尾）"
  }},
  "expansion": {{
    "skill_practice": "raw_copy模式，从【技能实践题】提取（去掉\"1.\"、\"2.\"等编号前缀），1-125字",
    "solving_ideas": "summary模式，1-125字"
  }}
}}

## 严格遵守以下规则：
1. **copy模式**：直接复制原文对应内容，不要改写或总结
2. **summary模式**：提炼/压缩原文核心意思，不能直接复制
3. **raw_copy模式**：直接复制原文，不要改写
4. **字数限制**：严格遵守每个字段的 min_length ~ max_length 范围
5. 只输出JSON，不要其他文字"""
