"""
Stage 1a: Perception 文件分割

将 perception/*.md 按 ### 【知识储备】/### 【任务实施】分割为两个文件：
- knowledge/*.md — 知识储备部分
- implementation/*.md — 任务实施部分

输出到：word_process/llm_input/perception/markdown_cut/{project}/{task_num}/
"""
import re
from pathlib import Path


class PerceptionSplitter:
    """将 perception.md 分割为 knowledge 和 implementation 两个文件"""

    SECTION_PATTERN = re.compile(r'^### 【(知识储备|任务实施)】\s*$')

    def __init__(self, input_dir: Path, output_dir: Path):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)

    def process(self, project_folder: Path) -> dict:
        """处理单个项目文件夹"""
        project_name = project_folder.name
        perception_dir = project_folder / "perception"

        if not perception_dir.exists():
            raise FileNotFoundError(f"perception 目录不存在: {perception_dir}")

        perception_files = sorted(perception_dir.glob("task*_perception.md"))
        if not perception_files:
            raise FileNotFoundError(f"未找到 perception 文件: {perception_dir}")

        results = {"project": project_name, "files": []}

        for pf in perception_files:
            task_num = self._extract_task_num(pf.name)
            self._split_file(pf, project_name, task_num)
            results["files"].append({
                "task_num": task_num,
                "knowledge": str(self.output_dir / project_name / task_num / "knowledge.md"),
                "implementation": str(self.output_dir / project_name / task_num / "implementation.md")
            })

        return results

    def _extract_task_num(self, filename: str) -> str:
        match = re.search(r'task(\d+)_perception\.md', filename)
        return match.group(1) if match else "0"

    def _split_file(self, file_path: Path, project_name: str, task_num: str):
        """将单个 perception 文件分割为 knowledge 和 implementation"""
        content = file_path.read_text(encoding='utf-8')
        lines = content.split('\n')

        knowledge_lines = []
        implementation_lines = []
        current_section = None

        for line in lines:
            stripped = line.rstrip()
            match = self.SECTION_PATTERN.match(stripped)

            if match:
                section_name = match.group(1)
                if section_name == '知识储备':
                    current_section = 'knowledge'
                else:
                    current_section = 'implementation'
                # 保留 section 标题作为分割标记
                if current_section == 'knowledge':
                    knowledge_lines.append(line.rstrip())
                else:
                    implementation_lines.append(line.rstrip())
            elif current_section == 'knowledge':
                knowledge_lines.append(line)
            elif current_section == 'implementation':
                implementation_lines.append(line)
            else:
                # 文件开头还没遇到 section，先跳过或归到 knowledge
                knowledge_lines.append(line)

        # 输出
        out_dir = self.output_dir / project_name / task_num
        out_dir.mkdir(parents=True, exist_ok=True)

        knowledge_path = out_dir / "knowledge.md"
        implementation_path = out_dir / "implementation.md"

        knowledge_path.write_text('\n'.join(knowledge_lines), encoding='utf-8')
        implementation_path.write_text('\n'.join(implementation_lines), encoding='utf-8')


def main():
    from pathlib import Path

    PROJECT_ROOT = Path(__file__).parent.parent.parent
    input_dir = PROJECT_ROOT / "word_process" / "original"
    output_dir = PROJECT_ROOT / "word_process" / "llm_input" / "perception" / "markdown_cut"

    splitter = PerceptionSplitter(input_dir, output_dir)

    project_folders = [d for d in input_dir.iterdir() if d.is_dir() and d.name.startswith('项目')]

    for project_folder in sorted(project_folders):
        print(f"\n分割项目: {project_folder.name}")
        try:
            result = splitter.process(project_folder)
            for f in result['files']:
                print(f"  task{f['task_num']}: knowledge + implementation")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"  错误: {e}")


if __name__ == "__main__":
    main()