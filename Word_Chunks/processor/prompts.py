"""Prompt templates for Word chunks → JSON conversion.

Schema constraints from PPT_Framework/schemas/schemas.py:
- mode="copy": 直接复制对应内容，不要改写
- mode="summary": 从原文提炼总结，不要直接复制
- 每个字段有 min_length ~ max_length 字数限制
"""

# =============================================================================
# Chunk1: 项目介绍+引导案例 → 共享素材提取
# =============================================================================

CHUNK1_PROMPT = """你是一个教育PPT内容提取助手。请从以下 Word 文档的【项目介绍+引导案例】部分提取信息，生成结构化JSON。

## 内容来源
{content}

## 输出要求
请从内容中提取以下信息，返回JSON。注意严格遵守字段的字数限制：

{{
  "project_name": "项目名称（从【标题1】提取，去掉前缀如"项目一"），copy模式，15-20字",
  "introduction_case": "引导案例完整内容，summary模式，1-190字",
  "guiding_problem1": "从案例提炼的第1个引导思考问题，summary模式，1-30字",
  "guiding_problem2": "从案例提炼的第2个引导思考问题，summary模式，1-30字",
  "guiding_problem3": "从案例提炼的第3个引导思考问题，summary模式，1-30字"
}}

## 严格遵守以下规则：
1. project_name：copy模式，直接提取标题中的项目名称，不要"项目一"等前缀，15-20字
2. introduction_case：summary模式，需要压缩/提炼案例核心内容，1-190字
3. guiding_problem1/2/3：summary模式，从案例延伸思考，不要直接复制原文，1-30字
4. 只输出JSON，不要其他文字"""

# =============================================================================
# Chunk2-4: 任务章节 → 完整 task JSON
# =============================================================================

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
    "task_name": "copy模式，从标题2提取任务名称，20-40字"
  }},
  "introduction": {{
    "introduction_case": "summary模式，引用chunk1素材，1-190字"
  }},
  "thinking": {{
    "guiding_problem1": "summary模式，引用chunk1素材，1-30字",
    "guiding_problem2": "summary模式，引用chunk1素材，1-30字",
    "guiding_problem3": "summary模式，引用chunk1素材，1-30字"
  }},
  "start": {{
    "task_num": "copy模式，从标题2提取，1-3字",
    "task_name": "copy模式，从标题2提取，20-40字"
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
    "task_requirements1": "copy模式，1-30字",
    "task_requirements2": "copy模式，1-30字",
    "task_requirements3": "copy模式，1-30字",
    "task_requirements4": "copy模式，1-30字（没有则填空字符串）",
    "task_requirements5": "copy模式，1-30字（没有则填空字符串）"
  }},
  "target": {{
    "task_target1": "copy模式，从【学习目标】提取，1-30字",
    "task_target2": "copy模式，1-30字",
    "task_target3": "copy模式，1-30字",
    "task_target4": "copy模式，1-30字",
    "task_focus": "copy模式，综合学习目标和任务描述总结重点，1-30字",
    "task_difficulty": "copy模式，综合学习目标和任务描述总结难点，1-30字"
  }},
  "summary": {{
    "task_summary": "summary模式，从【任务小结】第一段提炼，1-140字"
  }},
  "key_difficulties_summary": {{
    "key_summary1": "summary模式，跨三块内容总结关键点，1-20字",
    "key_summary2": "summary模式，1-20字",
    "key_summary3": "summary模式，1-20字",
    "difficulties_summary1": "summary模式，跨三块内容总结难点，1-20字",
    "difficulties_summary2": "summary模式，1-20字",
    "difficulties_summary3": "summary模式，1-20字"
  }},
  "expansion": {{
    "skill_practice": "raw_copy模式，从【技能实践题】提取，1-125字",
    "solving_ideas": "summary模式，1-125字"
  }}
}}

## 严格遵守以下规则：
1. **copy模式**：直接复制原文对应内容，不要改写或总结
2. **summary模式**：提炼/压缩原文核心意思，不能直接复制
3. **raw_copy模式**：直接复制原文，不要改写
4. **字数限制**：严格遵守每个字段的 min_length ~ max_length 范围
5. 只输出JSON，不要其他文字"""


def build_chunk1_prompt(content: str) -> str:
    """Build prompt for chunk1 processing."""
    return CHUNK1_PROMPT.format(content=content)


def build_task_prompt(title: str, content: str, chunk1_data: dict) -> str:
    """Build prompt for task chunk (chunk2-4) processing."""
    return CHUNK_TASK_PROMPT.format(
        project_name=chunk1_data.get("project_name", ""),
        introduction_case=chunk1_data.get("introduction_case", ""),
        guiding_problem1=chunk1_data.get("guiding_problem1", ""),
        guiding_problem2=chunk1_data.get("guiding_problem2", ""),
        guiding_problem3=chunk1_data.get("guiding_problem3", ""),
        title=title,
        content=content,
    )


# =============================================================================
# Field Correction: Stage 2 — targeted single-field fix
# =============================================================================

CORRECT_FIELD_PROMPT = """你是一个教育PPT内容校正助手。请根据以下信息校正指定字段的文本。

## 待校正字段
- 章节: {section}
- 字段名: {field}
- 当前值: "{current_value}"
- 当前字数: {current_len} 字
- 问题: {issue}（限制范围: {min_len}-{max_len} 字）
- 原文模式: {mode}

## 字数统计规则
- 中文字符每字=1，英文每字母=1
- 空格和标点符号不计入字数
- 输出时不要将标点符号或空格算作字数

## 压缩技巧（字数 > {max_len} 时使用）
1. 删除冗余修饰词（的、了、在）
2. 合并重复或相近的表达
3. 使用更简短的同义词替换
4. 删除举例说明，保留核心定义
5. 删除重复说明的内容

## 扩充技巧（字数 < {min_len} 时使用）
1. 添加必要的连接词（和、以及、同时）
2. 将短句改为复合句丰富表达
3. 补充必要的限定语使表达更完整

## 校正要求
1. 严格遵守字数限制：最终结果必须在 {min_len} 到 {max_len} 字之间
2. 保持原文模式：copy 模式不改变原文意思，summary 模式提炼核心
3. 不要改变原文的核心语义

## 输出格式
只输出JSON，不要其他文字：
{{
  "corrected_value": "校正后的文本（字数必须在{min_len}-{max_len}字之间）"
}}"""



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
    return CORRECT_FIELD_PROMPT.format(
        section=section,
        field=field,
        current_value=current_value,
        current_len=current_len,
        issue=issue,
        min_len=min_len,
        max_len=max_len,
        mode=mode
    )