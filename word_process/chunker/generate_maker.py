"""
Generate Maker - base md 解析 + JSON 生成

从 original/项目*/base/task*_base.md 提取内容，生成 JSON。

用法：
    python scripts/base_json.py
"""
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))


class BaseMdParser:
    """解析 base md 文件，按七个章节拆分内容"""

    # 七个关键标题
    HEADERS = [
        '【任务描述】', '【任务能力目标】', '【任务重难点】',
        '【任务小结】', '【任务拓展】'
    ]

    @staticmethod
    def parse(task_md_path: Path, project_name: str) -> dict:
        """解析 base md，返回各章节内容"""
        content = task_md_path.read_text(encoding='utf-8')
        lines = content.split('\n')

        sections = {h: [] for h in BaseMdParser.HEADERS}
        current = None

        for line in lines:
            matched = False
            for h in BaseMdParser.HEADERS:
                if h in line:
                    current = h
                    matched = True
                    break
            if matched:
                continue
            if current:
                sections[current].append(line)

        # 提取主标题
        task_num = ""
        task_name = ""
        for line in lines:
            m = re.match(r'^# +任务([一二三四五六\d]) +(.*)$', line.strip())
            if m:
                task_num = m.group(1)
                task_name = m.group(2).strip()
                break

        # 解析 before_task.md 获取情境导入内容
        before_task_path = task_md_path.parent.parent / "before_task.md"
        situation_import = ""
        guiding_questions = []
        if before_task_path.exists():
            situation_import, guiding_questions = BaseMdParser._parse_before_task(before_task_path)

        return {
            "project_name": project_name,
            "task_num": task_num,
            "task_name": task_name,
            "task_description": '\n'.join(sections['【任务描述】']).strip(),
            "task_ability": '\n'.join(sections['【任务能力目标】']).strip(),
            "task_focus_difficulty": '\n'.join(sections['【任务重难点】']).strip(),
            "task_summary": '\n'.join(sections['【任务小结】']).strip(),
            "task_expansion": '\n'.join(sections['【任务拓展】']).strip(),
            "situation_import": situation_import,
            "guiding_questions": guiding_questions,
        }

    @staticmethod
    def _parse_before_task(before_task_path: Path) -> tuple:
        """解析 before_task.md，提取情境导入内容和请思考问题"""
        content = before_task_path.read_text(encoding='utf-8')
        lines = content.split('\n')

        situation_import_lines = []
        guiding_questions = []
        in_situation = False
        in_thinking = False
        current = None

        for line in lines:
            stripped = line.strip()
            if '【情境导入】' in line:
                in_situation = True
                in_thinking = False
                continue
            if '请思考' in line or '请思考：' in line:
                in_situation = False
                in_thinking = True
                continue
            if in_situation:
                situation_import_lines.append(line)
            if in_thinking:
                # 提取问题行（数字编号开头的问题）
                m = re.match(r'^\d+[．.、]\s*(.+)', stripped)
                if m:
                    guiding_questions.append(m.group(1).strip())
                elif stripped and not stripped.startswith('请思考'):
                    guiding_questions.append(stripped)

        situation_import = '\n'.join(situation_import_lines).strip()
        return situation_import, guiding_questions[:3]


class BaseJsonGenerator:
    """生成 base_json"""

    # 直接提取字段（copy 模式）
    COPY_FIELDS = ["project_name", "task_num", "task_name"]

    # raw_copy 截取字段 (max_length, field_key_in_sections)
    RAW_COPY_FIELDS = [
        ("task_description", 110, "task_description"),
        ("skill_practice", 125, "task_expansion"),
    ]

    def __init__(self):
        # PROJECT_ROOT 在这里重新解析，因为文件位置变了
        project_root = Path(__file__).parent.parent.parent.resolve()
        json_template = project_root / "word_process" / "base_reference" / "task1.json"
        with open(json_template, "r", encoding="utf-8") as f:
            self.template_json = json.load(f)

    def generate(self, md_sections: dict) -> dict:
        """
        直接提取填充模式：所有字段从 md 直接提取，
        超长字段由 Checker + Corrector 后续处理
        """
        result = {}

        # copy 字段
        result["project_name"] = md_sections.get("project_name", "")
        result["task_num"] = md_sections.get("task_num", "")
        result["task_name"] = md_sections.get("task_name", "")

        # raw_copy 字段（直接填充，超长部分由 Checker 截断）
        result["task_description"] = md_sections.get("task_description", "")

        # thinking: LLM 后续生成，此处先置空
        result["guiding_problems"] = ["", "", ""]

        # target 字段 - 直接从 task_ability 提取
        targets = self._extract_targets(md_sections.get("task_ability", ""))
        result["task_targets"] = targets

        focus, difficulty = self._extract_focus_difficulty(md_sections.get("task_focus_difficulty", ""))
        result["task_focus"] = focus
        result["task_difficulty"] = difficulty

        # description.task_requirements - 直接从 task_ability 提取多条
        result["task_requirements"] = self._extract_task_requirements(md_sections.get("task_ability", ""))

        # introduction_case - 直接从 task_description 截取（取前200字）
        desc = md_sections.get("task_description", "")
        result["introduction_case"] = desc[:200] if desc else ""

        # summary - 直接从 task_summary 填充
        result["task_summary"] = md_sections.get("task_summary", "")

        # key_difficulties - LLM 后续生成，此处先置空
        result["key_difficulties"] = {}

        # expansion - 固定选择技能实践题第 1 题
        expansion_text = md_sections.get("task_expansion", "")
        result["skill_practice"] = self._extract_skill_practice(expansion_text)

        # solving_ideas - LLM 后续生成，此处先置空
        result["solving_ideas"] = ""

        return result

    def _extract_targets(self, text: str) -> list:
        """从任务能力目标中提取目标"""
        return self._extract_task_requirements(text)

    def _extract_focus_difficulty(self, text: str) -> tuple:
        """提取重点和难点"""
        focus = ""
        difficulty = ""
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        for line in lines:
            if line.startswith('重点'):
                focus = re.sub(r'^重点[：:；]\s*', '', line)
            elif line.startswith('难点'):
                difficulty = re.sub(r'^难点[：:；]\s*', '', line)
        return focus, difficulty

    def _extract_task_requirements(self, text: str) -> list:
        """从任务能力目标文本中提取多条要求（按换行切分，不限制字数）"""
        results = []
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
            # 去除编号前缀
            line = re.sub(r'^[a-zA-Z0-9][\.\)、\s]*', '', line)
            if line:
                results.append(line)
        return results[:5]

    def _extract_key_difficulties(self, text: str) -> dict:
        """从 task_focus_difficulty 提取关键点和难点"""
        key_lines = []
        diff_lines = []
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        for line in lines:
            if line.startswith('重点'):
                key_lines.append(re.sub(r'^重点[：:]\s*', '', line))
            elif line.startswith('难点'):
                diff_lines.append(re.sub(r'^难点[：:]\s*', '', line))
        # 补足3条
        while len(key_lines) < 3:
            key_lines.append("")
        while len(diff_lines) < 3:
            diff_lines.append("")
        return {
            "key_summary1": key_lines[0] if len(key_lines) > 0 else "",
            "key_summary2": key_lines[1] if len(key_lines) > 1 else "",
            "key_summary3": key_lines[2] if len(key_lines) > 2 else "",
            "difficulties_summary1": diff_lines[0] if len(diff_lines) > 0 else "",
            "difficulties_summary2": diff_lines[1] if len(diff_lines) > 1 else "",
            "difficulties_summary3": diff_lines[2] if len(diff_lines) > 2 else "",
        }

    def _extract_skill_practice(self, expansion: str) -> str:
        """提取 #### 二、技能实践题 的第 1 题"""
        lines = expansion.split('\n')
        capture = False
        result = []
        for line in lines:
            if '#### 二、技能实践题' in line or '#### 二、技能实践' in line:
                capture = True
                continue
            if capture:
                if line.startswith('####'):
                    break
                if line.strip():
                    if re.match(r'^\d+[．.、]', line.strip()):
                        if len(result) == 0:
                            result.append(line)
                            continue
                        break
                    elif result:
                        break
        return '\n'.join(result).strip() if result else ""

    def _extract_solving_ideas(self, expansion: str) -> str:
        """从 task_expansion 提取解题思路部分"""
        lines = expansion.split('\n')
        solving_text = ""
        capture = False
        for line in lines:
            if '解题思路' in line or '思路' in line:
                capture = True
                continue
            if capture and line.strip():
                solving_text += line + "\n"
        if not solving_text:
            solving_text = expansion[:200]
        return solving_text[:125] if len(solving_text) > 125 else solving_text

    def build_json(self, generated: dict, sections: dict) -> dict:
        """组装完整 JSON（复用 template_schema 结构）"""
        tmpl = self.template_json

        # cover
        cover = {
            "project_name": generated.get("project_name", ""),
            "task_num": generated.get("task_num", ""),
            "task_name": generated.get("task_name", ""),
        }

        # introduction
        introduction = {
            "introduction_case": generated.get("introduction_case", ""),
        }

        # thinking
        problems = generated.get("guiding_problems", ["", "", ""])
        thinking = {
            "guiding_problem1": problems[0] if len(problems) > 0 else "",
            "guiding_problem2": problems[1] if len(problems) > 1 else "",
            "guiding_problem3": problems[2] if len(problems) > 2 else "",
        }

        # start / catalog_one~six
        task_num = generated.get("task_num", "")
        task_name = generated.get("task_name", "")
        start = {"task_num": task_num, "task_name": task_name}
        catalog_one = {"task_num": task_num, "task_name": task_name}
        catalog_two = {"task_num": task_num, "task_name": task_name}
        catalog_three = {"task_num": task_num, "task_name": task_name}
        catalog_four = {"task_num": task_num, "task_name": task_name}
        catalog_five = {"task_num": task_num, "task_name": task_name}
        catalog_six = {"task_num": task_num, "task_name": task_name}

        # description
        requirements = generated.get("task_requirements", [])
        description = {
            "task_description": generated.get("task_description", ""),
            "task_requirements1": requirements[0] if len(requirements) > 0 else "",
            "task_requirements2": requirements[1] if len(requirements) > 1 else "",
            "task_requirements3": requirements[2] if len(requirements) > 2 else "",
            "task_requirements4": requirements[3] if len(requirements) > 3 else "",
            "task_requirements5": requirements[4] if len(requirements) > 4 else "",
        }

        # target
        targets = generated.get("task_targets", [])
        target = {
            "task_target1": targets[0] if len(targets) > 0 else "",
            "task_target2": targets[1] if len(targets) > 1 else "",
            "task_target3": targets[2] if len(targets) > 2 else "",
            "task_target4": targets[3] if len(targets) > 3 else "",
            "task_focus": generated.get("task_focus", ""),
            "task_difficulty": generated.get("task_difficulty", ""),
        }

        # summary
        summary = {"task_summary": generated.get("task_summary", "")}

        # key_difficulties_summary
        kd = generated.get("key_difficulties", {})
        key_difficulties_summary = {
            "key_summary1": kd.get("key_summary1", ""),
            "key_summary2": kd.get("key_summary2", ""),
            "key_summary3": kd.get("key_summary3", ""),
            "difficulties_summary1": kd.get("difficulties_summary1", ""),
            "difficulties_summary2": kd.get("difficulties_summary2", ""),
            "difficulties_summary3": kd.get("difficulties_summary3", ""),
        }

        # expansion
        expansion = {
            "skill_practice": generated.get("skill_practice", ""),
            "solving_ideas": generated.get("solving_ideas", ""),
        }

        return {
            "cover": cover,
            "introduction": introduction,
            "thinking": thinking,
            "start": start,
            "catalog_one": catalog_one,
            "description": description,
            "catalog_two": catalog_two,
            "target": target,
            "catalog_three": catalog_three,
            "catalog_four": catalog_four,
            "catalog_five": catalog_five,
            "summary": summary,
            "key_difficulties_summary": key_difficulties_summary,
            "catalog_six": catalog_six,
            "expansion": expansion,
        }


def main():
    import unicodedata, re

    print("=" * 60)
    print("Base JSON Generator")
    print("=" * 60)

    # 确保输出目录存在
    LLM_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 扫描所有 base md 文件
    base_files = []
    for item in ORIGINAL_DIR.iterdir():
        if not item.is_dir():
            continue
        raw_name = item.name
        collapsed = re.sub(r' {2,}', ' ', raw_name)
        project_dir_name = unicodedata.normalize('NFC', collapsed)
        if not re.match(r'^项目', project_dir_name):
            continue
        base_dir = item / "base"
        if base_dir.exists():
            for mf in base_dir.glob("task*_base.md"):
                base_files.append((mf, project_dir_name))

    print(f"找到 {len(base_files)} 个 base md 文件")

    client = MiniMaxClient()
    generator = BaseJsonGenerator()
    parser = BaseMdParser()

    for md_path, project_name in sorted(base_files):
        print(f"\n处理: {md_path.parent.parent.name}/{md_path.name}")

        # 解析 md
        sections = parser.parse(md_path, project_name)
        print(f"  - task_num: {sections['task_num']}")
        print(f"  - task_name: {sections['task_name']}")

        # 生成 JSON
        generated = generator.generate(sections)
        output_json = generator.build_json(generated, sections)

        # 输出
        task_name = md_path.stem  # e.g. task1_base
        output_path = LLM_OUTPUT_DIR / f"{task_name}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_json, f, ensure_ascii=False, indent=2)

        print(f"  -> {output_path.name}")

    print("\n" + "=" * 60)
    print("完成")
    print("=" * 60)


if __name__ == "__main__":
    main()