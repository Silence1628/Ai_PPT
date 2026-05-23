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
  "introduction_case": "根据原文案例内容，重新撰写一段完整的引导案例叙述。必须包含：场景描述、矛盾冲突、3个思考问题。要求200-220字，内容丰满细节充实，不要干瘪概括，1-220字",
  "guiding_problem1": "从案例提炼的第1个引导思考问题（必须以问号结尾），summary模式，1-30字",
  "guiding_problem2": "从案例提炼的第2个引导思考问题（必须以问号结尾），summary模式，1-30字",
  "guiding_problem3": "从案例提炼的第3个引导思考问题（必须以问号结尾），summary模式，1-30字"
}}

## 严格遵守以下规则：
1. project_name：copy模式，直接提取标题中的项目名称，不要"项目一"等前缀，15-20字
2. introduction_case：summary模式，需要压缩/提炼案例核心内容，1-210字
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


# =============================================================================
# Perception Semantic Chunking: LLM理解+重构段落
# =============================================================================

SEMANTIC_CHUNK_PROMPT = """你是一个教育PPT内容编辑。请理解以下教材内容的知识逻辑，然后将每个小节的内容重构为独立的PPT页面段落。

## 当前主题：{parent_title}

{content}

## 重构要求
1. **理解优先**：先理解每个小节讲的是什么知识点，知识点之间有什么逻辑关系（递进/并列/对比/因果）
2. **独立成段**：每个小节独立输出，重构为1~3个段落，每个段落约300字。内容少的1个段落就够了，内容丰富的可以2~3个段落
3. **保留知识点**：原文中的所有关键概念、定义、对比关系、例子必须保留，不能遗漏
4. **流畅叙述**：用连贯的叙述重组内容，而非简单拼接原文；表结构转为文字描述
5. **去冗余**：删除"如图X-X-X所示""从下表可以看出"等指向性语句和图表编号引用

## 输出格式
只返回 JSON：
{{
  "h4_sections": [
    {{
      "title": "小节标题（原文H4标题）",
      "paragraphs": [
        "重构后的段落1（约300字）",
        "重构后的段落2（约300字）"
      ]
    }}
  ]
}}"""


SEMANTIC_CHUNK_RECURSIVE_PROMPT = """你是一个教育PPT内容编辑。以下段落需要拆分为多个约300字的独立段落。

## 待处理段落
{content}

## 要求
1. 在语义完整处拆分，每个段落约300字
2. 不能用截断的方式，必须重新组织语言
3. 每个段落是一个自洽的知识单元

## 输出格式
只返回 JSON：
{{
  "paragraphs": ["段落1", "段落2", ...]
}}"""


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
