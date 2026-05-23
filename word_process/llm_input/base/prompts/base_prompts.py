"""
Base JSON Prompts - base_ppt JSON 生成所需的 prompt 模板

定义各 page 字段的 prompt 模板和约束。
"""

# 各 summary 类字段的生成 prompt 模板
INTRODUCTION_PROMPT = """你是一个教育内容摘要助手。请根据以下【任务描述】内容，生成一段{max_length}字以内的引言案例。

要求：
- 以一个有趣的业务场景或案例开篇
- 简要说明本任务要解决的核心问题
- 突出学习本任务的实际价值

内容：
{content}

请直接输出摘要文字，不要有多余说明。"""

THINKING_PROMPT = """你是一个教学设计助手。请根据以下【任务实施】内容，生成3个引导问题。

要求：
- 每个问题{max_length}字以内
- 问题要有启发性，能引发学员思考
- 三个问题要有层次，体现从浅入深的学习路径
- 直接输出3行，每行一个问题，不要编号

内容：
{content}

请直接输出3个问题，每行一个。"""

SUMMARY_PROMPT = """你是一个教学总结助手。请根据以下【任务小结】内容，生成一段{max_length}字以内的总结。

要求：
- 概括本任务的核心知识点和技能
- 突出实践环节的关键收获
- 说明学习本任务的意义

内容：
{content}

请直接输出总结文字，不要有多余说明。"""

KEY_DIFFICULTIES_PROMPT = """你是一个教学分析助手。请根据以下【任务描述】【任务能力目标】【任务重难点】【任务小结】内容，提取关键点和难点。

要求：
- 提取3个关键点，每个{max_length}字以内
- 提取3个难点摘要，每个{max_length}字以内
- 关键点要概括核心技能或知识点
- 难点要指出学员容易遇到的问题
- 直接输出6行，不要编号

内容：
{content}

请直接输出6行（3行关键点+3行难点），每行一个。"""

SOLVING_IDEAS_PROMPT = """你是一个教学设计助手。请根据以下【任务拓展】中的解题思路内容，生成一段{max_length}字以内的解题思路摘要。

要求：
- 概括解决技能实践题的核心思路和方法
- 说明关键步骤和技术要点
- 突出实践中的重点注意事项

内容：
{content}

请直接输出解题思路摘要，不要有多余说明。"""

TASK_REQUIREMENTS_PROMPT = """你是一个教学设计助手。请根据以下内容，结合【任务描述】【任务能力目标】【任务重难点】，生成5条任务要求。

要求：
- 每条要求不超过30字
- 要求要具体、可操作
- 体现任务的完整流程
- 直接输出5行，每行一条要求，不要编号

内容：
{content}

请直接输出5条要求，每行一条。"""

SKILL_PRACTICE_PROMPT = """你是一个教学设计助手。请从以下【任务拓展】的技能实践题中，选择最有价值的一道题目。

要求：
- 选择最有代表性、最能体现本任务核心技能的题目
- 直接输出选中的题目内容，不要多余说明

内容：
{content}

请直接输出选中的题目。"""

# 全量 JSON 生成的 system prompt
SYSTEM_PROMPT = """你是一个教育内容结构化助手。你的任务是将学员的 base 内容填充到指定的 JSON 结构中。

JSON 结构包含以下页面字段：
- cover: {project_name, task_num, task_name}
- introduction: {introduction_case}
- thinking: {guiding_problem1, guiding_problem2, guiding_problem3}
- start: {task_num, task_name}
- catalog_one/two/three/four/five: {task_num, task_name}
- description: {task_description, task_requirements1~5}
- target: {task_target1~4, task_focus, task_difficulty}
- summary: {task_summary}
- key_difficulties_summary: {key_summary1~3, difficulties_summary1~3}
- catalog_six: {task_num, task_name}
- expansion: {skill_practice, solving_ideas}

字段约束：
- introduction_case: max 190字，summary模式
- guiding_problem1~3: max 30字，summary模式
- task_description: max 110字，raw_copy模式
- task_requirements1~5: max 30字，copy模式
- task_target1~4: max 30字，copy模式
- task_focus/task_difficulty: max 30字，copy模式
- task_summary: max 140字，summary模式
- key_summary1~3: max 20字，summary模式
- difficulties_summary1~3: max 20字，summary模式
- skill_practice: max 125字，raw_copy模式
- solving_ideas: max 125字，summary模式

注意：
- 直接复制字段（如 task_num、task_name）直接提取，不要调用 LLM
- summary 模式字段调用 LLM 生成简洁摘要
- raw_copy 模式字段直接截取原文指定长度
- 严格遵守 max_length 限制
- 输出必须是合法 JSON 格式"""

USER_PROMPT_TEMPLATE = """请根据以下 base md 内容，生成完整的 JSON 数据。

项目名称：{project_name}
任务编号：{task_num}
任务名称：{task_name}

任务描述：
{task_description}

任务能力目标：
{task_ability}

任务重难点：
{task_focus_difficulty}

任务小结：
{task_summary}

任务拓展：
{task_expansion}

请严格按照 JSON 结构输出，不要有多余文字。"""


def build_user_prompt(md_sections: dict) -> str:
    """构建用户 prompt"""
    return USER_PROMPT_TEMPLATE.format(
        project_name=md_sections.get("project_name", ""),
        task_num=md_sections.get("task_num", ""),
        task_name=md_sections.get("task_name", ""),
        task_description=md_sections.get("task_description", ""),
        task_ability=md_sections.get("task_ability", ""),
        task_focus_difficulty=md_sections.get("task_focus_difficulty", ""),
        task_summary=md_sections.get("task_summary", ""),
        task_expansion=md_sections.get("task_expansion", ""),
    )