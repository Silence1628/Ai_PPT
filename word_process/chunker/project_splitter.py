"""
Markdown Project Splitter - 项目md第一次分块

将项目md按 # before task、# 任务一、# 任务二 等标题拆分为独立md文件。

输出结构：
项目文件夹/
├── 项目名.md
├── before_task.md
├── task1.md
├── task2.md
└── task3.md

分块完成后自动调用 MarkdownCleaner 清洗分块数据。
"""
import re
from pathlib import Path
from typing import List, Tuple, Dict


class ProjectMdSplitter:
    """将项目md按一级标题拆分为多个md文件"""

    # 匹配顶级标题（# before task、# 任务一 等）
    HEADING_PATTERN = re.compile(r'^# +(.*)$', re.UNICODE)
    # 任务标题提取：任务 + 数字/中文数字
    TASK_HEADING_PATTERN = re.compile(r'^# +任务([一二三四五六\d]+)', re.UNICODE)
    BEFORE_TASK_HEADING = '# before task'

    def __init__(self, input_path: str = None):
        if input_path is None:
            self.input_path = Path(__file__).parent.parent / "original"
        else:
            self.input_path = Path(input_path)

    def split_all(self):
        """处理所有项目md文件"""
        # 找项目级md（文件名以"项目"开头）
        project_files = []
        for item in self.input_path.iterdir():
            if item.is_dir() and item.name.startswith('项目'):
                md_files = list(item.glob("*.md"))
                for mf in md_files:
                    if mf.name.startswith('项目') and mf.name.endswith('.md'):
                        project_files.append(mf)

        print(f"找到 {len(project_files)} 个项目md文件")
        for pf in sorted(project_files):
            print(f"  - {pf.name}")
            self.split_file(pf)

    def split_file(self, project_md: Path) -> Dict:
        """拆分单个项目md文件，返回拆分信息"""
        content = project_md.read_text(encoding='utf-8')
        lines = content.split('\n')

        chunks = []  # List[Tuple[title, content]]
        current_title = None
        current_lines = []

        for line in lines:
            m = self.HEADING_PATTERN.match(line)
            if m:
                heading_text = m.group(1).strip()
                # 检查是否是任务标题
                task_m = self.TASK_HEADING_PATTERN.match(line)
                if task_m or heading_text == 'before task':
                    # 保存前一个块
                    if current_title is not None:
                        chunks.append((current_title, '\n'.join(current_lines)))
                    current_title = heading_text
                    current_lines = [line]
                else:
                    # 其他标题（如 # 项目名），归到当前块
                    current_lines.append(line)
            else:
                current_lines.append(line)

        # 最后一个块
        if current_title is not None:
            chunks.append((current_title, '\n'.join(current_lines)))

        # 确定输出文件名
        output_dir = project_md.parent

        for title, chunk_content in chunks:
            # 决定文件名
            if title == 'before task':
                filename = "before_task.md"
            else:
                # 提取任务编号
                m = self.TASK_HEADING_PATTERN.match(f"# {title}")
                if m:
                    num = self._chinese_to_arabic(m.group(1))
                    filename = f"task{num}.md"
                else:
                    # fallback：用标题前几个字
                    safe_name = re.sub(r'[^\w]', '', title[:6])
                    filename = f"task_{safe_name}.md"

            output_path = output_dir / filename
            output_path.write_text(chunk_content + '\n', encoding='utf-8')
            print(f"    -> {filename}")

        return {"file": project_md.name, "chunks": len(chunks)}

    def _chinese_to_arabic(self, cn: str) -> str:
        mapping = {"一": "1", "二": "2", "三": "3", "四": "4", "五": "5", "六": "6"}
        return mapping.get(cn, cn)


def main():
    import sys
    from pathlib import Path as PathBase
    if len(sys.argv) > 1:
        target = PathBase(sys.argv[1])
    else:
        target = PathBase(__file__).parent.parent.parent / "word_process" / "original"

    splitter = ProjectMdSplitter(str(target))
    splitter.split_all()

    # 第二次分块：task md → base + perception
    print("\n进行第二次分块...")
    from task_splitter import TaskMdSplitter
    task_splitter = TaskMdSplitter(str(target))
    task_splitter.split_all()

    print("\n全部完成")


if __name__ == "__main__":
    main()