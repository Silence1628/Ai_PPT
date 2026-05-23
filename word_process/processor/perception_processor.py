"""
PerceptionProcessor - Perception 内容处理器（Stage 1）

读取 markdown_cut 中已分割的 knowledge.md / implementation.md，
按 H3/H4 构建 AST 树，输出 JSON。

输入：word_process/llm_input/perception/markdown_cut/{project}/{task_num}/*.md
输出：word_process/llm_input/perception/original_markdown/{project}/
"""
import re
import json
from pathlib import Path
from typing import List, Dict, Optional


class PerceptionProcessor:
    """Stage 1: 解析分割后的 knowledge/implementation md → H3/H4 AST JSON"""

    CODE_BLOCK_PATTERN = re.compile(r'^```(\w*)\s*$')
    CHART_REF_PATTERN = re.compile(r'图\s*\d+[-‐]\d+[-‐]\s*\d+|表\s*\d+[-‐]\d+[-‐]\s*\d+')
    H1_TITLE_PATTERN = re.compile(r'^#\s+')

    def __init__(self, input_dir: Path, output_dir: Path, source_dir: Path = None):
        self.input_dir = Path(input_dir)        # markdown_cut/
        self.output_dir = Path(output_dir)       # original_markdown/
        self.source_dir = Path(source_dir) if source_dir else None  # original/ for task titles

    def process(self, project_folder: Path) -> dict:
        """处理一个项目文件夹的所有 split knowledge/implementation md 文件"""
        project_name = project_folder.name
        split_dir = self.input_dir / project_name

        if not split_dir.exists():
            raise FileNotFoundError(f"分割目录不存在: {split_dir}")

        task_dirs = sorted([d for d in split_dir.iterdir() if d.is_dir() and d.name.isdigit()])
        if not task_dirs:
            raise FileNotFoundError(f"未找到 task 目录: {split_dir}")

        results = {"project": project_name, "files": []}

        for task_dir in task_dirs:
            task_num = task_dir.name
            task_title = self._extract_task_title(project_name, task_num)

            knowledge_path = task_dir / "knowledge.md"
            implementation_path = task_dir / "implementation.md"

            if knowledge_path.exists():
                out_path = self.output_dir / project_name / "knowledge" / f"task{task_num}_knowledge.json"
                out_path.parent.mkdir(parents=True, exist_ok=True)
                data = self._parse_markdown_file(knowledge_path, task_num, task_title, "knowledge")
                out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
                results["files"].append(str(out_path))

            if implementation_path.exists():
                out_path = self.output_dir / project_name / "task" / f"task{task_num}_implementation.json"
                out_path.parent.mkdir(parents=True, exist_ok=True)
                data = self._parse_markdown_file(implementation_path, task_num, task_title, "task")
                out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
                results["files"].append(str(out_path))

        return results

    def _extract_task_title(self, project_name: str, task_num: str) -> str:
        """从原始 task{N}.md 的 H1 提取任务标题"""
        if self.source_dir is None:
            return f"任务{task_num}"

        task_file = self.source_dir / project_name / f"task{task_num}.md"
        if not task_file.exists():
            return f"任务{task_num}"

        first_line = task_file.read_text(encoding='utf-8').split('\n')[0].strip()
        if first_line.startswith('# '):
            return first_line.lstrip('# ').strip()
        return f"任务{task_num}"

    def _extract_task_num(self, filename: str) -> str:
        match = re.search(r'task(\d+)_perception\.md', filename)
        return match.group(1) if match else "0"

    def _parse_markdown_file(self, file_path: Path, task_num: str,
                             task_title: str, section: str) -> dict:
        """解析单个 md 文件，按 H3/H4 构建 AST"""
        content = file_path.read_text(encoding='utf-8')
        lines = content.split('\n')

        result = {
            "task_num": task_num,
            "task_title": task_title,
            "section": section,
            "chunks": []
        }

        current_h3 = None   # #### XXXX topic
        current_h3_content = []  # content for current_h3 (when no H4 children)
        current_h4 = None   # ##### X.X leaf
        in_code_block = False
        code_blocks = []
        current_content_lines = []

        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.rstrip()

            # 代码块状态切换
            if stripped.startswith('```'):
                cb_match = self.CODE_BLOCK_PATTERN.match(stripped)
                if cb_match:
                    if not in_code_block:
                        in_code_block = True
                        code_blocks = []
                    else:
                        in_code_block = False
                    i += 1
                    continue

            if in_code_block:
                code_blocks.append(stripped)
                i += 1
                continue

            # H3: #### XXXX（topic 级别，如 "一、智能体的概念"）
            if stripped.startswith('#### '):
                # 保存前一个 H4
                if current_h4 is not None:
                    self._finalize_h4(current_h4, current_content_lines, code_blocks)
                    code_blocks = []
                    current_content_lines = []

                # 保存前一个 H3
                if current_h3 is not None:
                    if "_body" in current_h3:
                        current_h3["content"] = '\n'.join(current_h3["_body"]).strip()
                        del current_h3["_body"]
                    result["chunks"].append(current_h3)

                h3_title = self._strip_heading_number(stripped.lstrip('# ').strip())
                current_h3 = {
                    "id": f"h3_{len(result['chunks'])}",
                    "level": 3,
                    "title": h3_title,
                    "content": "",
                    "children": []
                }
                current_h4 = None
                i += 1
                continue

            # H4: ##### X.X（leaf 级别，如 "1. 工作流和智能体"）
            # 如果标题是中文数字序号（如"一、"、"二、"），实际上是 H3 topic
            if stripped.startswith('##### '):
                # 保存前一个 H4
                if current_h4 is not None:
                    self._finalize_h4(current_h4, current_content_lines, code_blocks)
                    code_blocks = []
                    current_content_lines = []

                h4_title = stripped.lstrip('# ').strip()
                # 检查是否是中文数字序号（表示这是个 topic 级别的标题）
                import re as re_module
                if re_module.match(r'^[一二三四五六七八九十]+、', h4_title):
                    # 实际上是 H3 级别，提升为 current_h3
                    if current_h4 is not None:
                        self._finalize_h4(current_h4, current_content_lines, code_blocks)
                        code_blocks = []
                        current_content_lines = []

                    if current_h3 is not None:
                        if "_body" in current_h3:
                            current_h3["content"] = '\n'.join(current_h3["_body"]).strip()
                            del current_h3["_body"]
                        result["chunks"].append(current_h3)

                    current_h3 = {
                        "id": f"h3_{len(result['chunks'])}",
                        "level": 3,
                        "title": self._strip_heading_number(h4_title),
                        "content": "",
                        "children": []
                    }
                    current_h4 = None
                    i += 1
                    continue

                # 如果没有 current_h3，创建一个虚拟的
                if current_h3 is None:
                    current_h3 = {
                        "id": f"h3_{len(result['chunks'])}",
                        "level": 3,
                        "title": "知识储备",
                        "children": []
                    }

                current_h4 = {
                    "id": f"h4_{len(current_h3['children'])}",
                    "level": 4,
                    "title": h4_title,
                    "content": "",
                    "code_blocks": [],
                    "chart_refs": []
                }
                current_h3["children"].append(current_h4)
                i += 1
                continue

            # H3: ### 【知识储备】/【任务实施】 → section 标记
            if stripped.startswith('### ') and ('【知识储备】' in stripped or '【任务实施】' in stripped):
                # 保存前一个 H4
                if current_h4 is not None:
                    self._finalize_h4(current_h4, current_content_lines, code_blocks)
                    code_blocks = []
                    current_content_lines = []

                result["section"] = "knowledge" if '【知识储备】' in stripped else "task"
                i += 1
                continue

            # 内容行：如果有 current_h4，收集到 H4；否则收集到 current_h3
            if stripped and not stripped.startswith('#'):
                if current_h4 is not None:
                    current_content_lines.append(stripped)
                elif current_h3 is not None:
                    # H3 without H4 children - content goes directly to h3
                    current_h3.setdefault("_body", []).append(stripped)

            i += 1

        # 保存最后一个 H4
        if current_h4 is not None:
            self._finalize_h4(current_h4, current_content_lines, code_blocks)

        # 保存最后一个 H3：处理无 H4 的情况，将 _body 合并到 content
        if current_h3 is not None:
            if "_body" in current_h3:
                current_h3["content"] = '\n'.join(current_h3["_body"]).strip()
                del current_h3["_body"]
            result["chunks"].append(current_h3)

        return result

    def _finalize_h4(self, h4: dict, content_lines: list, code_blocks: list):
        """将收集的内容 finalize 到 H4 节点"""
        content_text = '\n'.join(content_lines).strip()
        h4["content"] = content_text
        h4["code_blocks"] = list(code_blocks)
        h4["chart_refs"] = self._extract_chart_refs(content_text)
        content_lines.clear()

    @staticmethod
    def _strip_heading_number(title: str) -> str:
        """去掉标题中的序号前缀，如 '一、智能体的概念' → '智能体的概念'"""
        import re as _re
        # 中文数字序号: 一、二、... 十、十一、
        m = _re.match(r'^[一二三四五六七八九十]+、\s*', title)
        if m:
            return title[m.end():]
        # 阿拉伯数字序号: 1. 1、
        m = _re.match(r'^\d+[.、]\s*', title)
        if m:
            return title[m.end():]
        return title

    def _extract_chart_refs(self, text: str) -> List[str]:
        return self.CHART_REF_PATTERN.findall(text)


def main():
    from pathlib import Path

    PROJECT_ROOT = Path(__file__).parent.parent.parent
    input_dir = PROJECT_ROOT / "word_process" / "llm_input" / "perception" / "markdown_cut"
    output_dir = PROJECT_ROOT / "word_process" / "llm_input" / "perception" / "original_markdown"
    source_dir = PROJECT_ROOT / "word_process" / "original"

    processor = PerceptionProcessor(input_dir, output_dir, source_dir)

    project_folders = [d for d in input_dir.iterdir() if d.is_dir() and d.name.startswith('项目')]

    for project_folder in sorted(project_folders):
        print(f"\n处理项目: {project_folder.name}")
        try:
            result = processor.process(project_folder)
            print(f"  生成文件: {len(result['files'])}")
            for f in result['files']:
                print(f"    - {f}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"  错误: {e}")


if __name__ == "__main__":
    main()