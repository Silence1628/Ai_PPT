"""
Task Md Splitter - task md第二次分块

将task md文件按以下标题拆分为 base 和 perception 两个文件：
- base: 【任务描述】【任务能力目标】【任务重难点】【任务小结】【任务拓展】
- perception: 【知识储备】【任务实施】

输出结构：
项目文件夹/
├── before_task.md (如有)
├── task1.md
├── task1_base.md      ← 新增
├── task1_perception.md ← 新增
├── task2.md
├── task2_base.md
├── task2_perception.md
└── ...
"""
import re
from pathlib import Path
from typing import List, Tuple, Dict


class TaskMdSplitter:
    """将task md按章节标题拆分为base和perception"""

    # 七个关键标题（按文档顺序）
    ALL_HEADERS = [
        '【任务描述】',
        '【任务能力目标】',
        '【任务重难点】',
        '【知识储备】',
        '【任务实施】',
        '【任务小结】',
        '【任务拓展】',
    ]

    # base类标题
    BASE_HEADERS = {'【任务描述】', '【任务能力目标】', '【任务重难点】', '【任务小结】', '【任务拓展】'}
    # perception类标题
    PERCEPTION_HEADERS = {'【知识储备】', '【任务实施】'}

    # 匹配 ### 或 ## 标题行
    SECTION_PATTERN = re.compile(r'^#{2,3}\s*(' + '|'.join(re.escape(h) for h in ALL_HEADERS) + r')', re.UNICODE)

    def __init__(self, input_path: str = None):
        if input_path is None:
            self.input_path = Path(__file__).parent.parent / "original"
        else:
            self.input_path = Path(input_path)

    def split_all(self):
        """处理所有项目文件夹下的task md文件"""
        task_files = []
        for item in self.input_path.iterdir():
            if item.is_dir() and item.name.startswith('项目'):
                md_files = list(item.glob("*.md"))
                for mf in md_files:
                    # 只处理原始 task md，不处理已分块的 base/perception
                    if mf.name.startswith('task') and mf.name.endswith('.md') and '_' not in mf.name:
                        task_files.append(mf)

        print(f"找到 {len(task_files)} 个task md文件")
        for tf in sorted(task_files):
            print(f"  - {tf.parent.name}/{tf.name}")
            self.split_file(tf)

    def split_file(self, task_md: Path) -> Dict:
        """拆分单个task md文件，返回拆分信息"""
        content = task_md.read_text(encoding='utf-8')
        lines = content.split('\n')

        # 收集所有标题位置
        sections = []  # List[Tuple(line_number, header_name)]

        for i, line in enumerate(lines):
            m = self.SECTION_PATTERN.match(line.strip())
            if m:
                header_name = m.group(1)
                sections.append((i, header_name))

        if not sections:
            print(f"    [WARN] 未找到任何章节标题")
            return {"file": task_md.name, "chunks": 0}

        # 主标题行（第一个标题之前的行）
        first_header_idx = sections[0][0] if sections else 0
        main_title_lines = lines[:first_header_idx]

        # 按顺序分配每段内容到 base 或 perception
        base_sections = []
        perception_sections = []

        for i, line in enumerate(lines):
            m = self.SECTION_PATTERN.match(line.strip())
            if m:
                header_name = m.group(1)
                if header_name in self.BASE_HEADERS:
                    target = base_sections
                else:
                    target = perception_sections
                target.append(i)
            elif base_sections and i > base_sections[-1]:
                # 继续补充到最后一个section
                pass
            elif perception_sections and i > perception_sections[-1]:
                pass

        # 构建内容：根据当前 bucket 决定行归属哪个文件
        # 每个标题行只归入对应文件，不重复归入
        base_line_indices = set()
        perception_line_indices = set()

        current_bucket = None  # None -> 'base' or 'perception'
        for i, line in enumerate(lines):
            m = self.SECTION_PATTERN.match(line.strip())
            if m:
                header_name = m.group(1)
                if header_name in self.BASE_HEADERS:
                    current_bucket = 'base'
                    base_line_indices.add(i)
                elif header_name in self.PERCEPTION_HEADERS:
                    current_bucket = 'perception'
                    perception_line_indices.add(i)
            else:
                if current_bucket == 'base':
                    base_line_indices.add(i)
                elif current_bucket == 'perception':
                    perception_line_indices.add(i)

        # 主标题行（第一个标题之前的行）归入 base
        for i in range(first_header_idx):
            base_line_indices.add(i)

        base_lines = [lines[i] for i in sorted(base_line_indices)]
        perception_lines = [lines[i] for i in sorted(perception_line_indices)]

        base_content = '\n'.join(base_lines)
        perception_content = '\n'.join(perception_lines)

        # 输出文件到 base/ 和 perception/ 子文件夹
        task_name = task_md.stem  # e.g. "task1"
        output_dir = task_md.parent

        base_dir = output_dir / "base"
        perception_dir = output_dir / "perception"
        base_dir.mkdir(exist_ok=True)
        perception_dir.mkdir(exist_ok=True)

        base_path = base_dir / f"{task_name}_base.md"
        perception_path = perception_dir / f"{task_name}_perception.md"

        base_path.write_text(base_content + '\n', encoding='utf-8')
        perception_path.write_text(perception_content + '\n', encoding='utf-8')

        print(f"    -> {base_path.name}")
        print(f"    -> {perception_path.name}")

        return {
            "file": task_md.name,
            "base_lines": len(base_lines),
            "perception_lines": len(perception_lines),
        }


def main():
    import sys
    from pathlib import Path as PathBase
    if len(sys.argv) > 1:
        target = PathBase(sys.argv[1])
    else:
        target = PathBase(__file__).parent.parent.parent / "word_process" / "original"

    splitter = TaskMdSplitter(str(target))
    splitter.split_all()

    print("\n全部完成")


if __name__ == "__main__":
    main()