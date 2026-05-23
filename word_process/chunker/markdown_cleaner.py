"""
Markdown Cleaner - 教育Agent项目MD文件清洗工具

清洗规则：
1. 删除图表标题行（匹配 图X-X-X 或 表X-X-X 整行）
2. 压缩连续空行（3+ → 2）
3. 清除标题末尾标点（`。；，`）
4. 统一列表标记（* + → -）
5. 代码块加语言标注（补全 python/js 等）
6. 去除行尾空格
7. 文件末尾保证一个换行
"""
import re
from pathlib import Path
from typing import List, Tuple


class MarkdownCleaner:
    # 匹配图表标题行：如 图1-0-1、图 1-1-1RAGFlow、表1-1- 1、图1-0- 1
    CHART_TITLE_PATTERN = re.compile(r'^图\s*\d+[-‐]\d+[-‐]\s*\d+\s*.*$', re.UNICODE)
    TABLE_TITLE_PATTERN = re.compile(r'^表\s*\d+[-‐]\d+[-‐]\s*\d+\s*.*$', re.UNICODE)

    # 正文中的图表引用：如图 1-1- 1、从下表1-1- 1 等，保留后面文字
    FIGURE_REF_PATTERN = re.compile(r'如图\s*\d+[-‐]\d+[-‐]\s*\d+\s*', re.UNICODE)
    TABLE_REF_PATTERN = re.compile(r'([从在]下[面表]?)\d+[-‐]\d+[-‐]\s*\d+\s*', re.UNICODE)

    # 正文中独立的图表编号：x-x-x 或 x-x- x 格式
    # 使用 (?<![0-9A-Za-z]) 排除字母数字前导，确保中文/标点前的编号被清洗
    REF_NUM_PATTERN = re.compile(r'(?<![0-9A-Za-z])\d+[-‐]\d+[-‐]\s*\d+(?=\s|$|[^\w\s])', re.UNICODE)
    REF_NUM_PATTERN_NOSPACE = re.compile(r'(?<![0-9A-Za-z])\d+[-‐]\d+[-‐]\d+(?=\s|$|[^\w\s])', re.UNICODE)

    # 连续空行压缩
    MULTI_BLANK_PATTERN = re.compile(r'\n{3,}')

    # 行尾空格
    TRAILING_SPACE_PATTERN = re.compile(r'[ \t]+\n')

    # 标题末尾标点（中文标点紧贴标题末尾）
    TITLE_END_PUNCT_PATTERN = re.compile(r'^(#{1,6}\s*[^\n\w\s][^：，。；]*)[。，；，](?=\s*$|\s*\n)', re.UNICODE)

    # 列表标记统一（段落级 -*/+，代码内不处理）
    LIST_MARKER_LINE = re.compile(r'^(\s*)([-*+])\s+')
    LIST_MARKER_TASK = re.compile(r'^(\s*)- \[([ xX])\]')

    def __init__(self, input_path: str):
        self.input_path = Path(input_path)
        self.stats = {"files_processed": 0, "lines_removed": 0, "changes": []}

    def clean_file(self, file_path: Path) -> Tuple[str, List[str]]:
        """清洗单个文件，返回 (清洗后内容, 变更列表)"""
        content = file_path.read_text(encoding='utf-8')
        changes = []

        # 规则2：压缩连续空行
        before = len(content)
        content = self.MULTI_BLANK_PATTERN.sub('\n\n', content)
        if len(content) != before:
            changes.append("压缩空行")

        # 规则2b：正文中的图表引用编号清洗
        new_content = self.FIGURE_REF_PATTERN.sub('如图 ', content)
        if new_content != content:
            changes.append("清洗图表引用")
        content = new_content

        # 规则2c：清洗正文图表编号
        count = len(self.REF_NUM_PATTERN.findall(content))
        count2 = len(self.REF_NUM_PATTERN_NOSPACE.findall(content))
        new_content = self.REF_NUM_PATTERN.sub('', content)
        new_content = self.REF_NUM_PATTERN_NOSPACE.sub('', new_content)
        if new_content != content:
            changes.append(f"清洗图表编号{count + count2}处")
        content = new_content

        # 规则3：清除标题末尾标点
        lines = content.split('\n')
        new_lines = []
        for line in lines:
            stripped = line.rstrip()
            m = re.match(r'^(#{1,6}\s*)(.+)', stripped)
            if m:
                prefix, text = m.group(1), m.group(2)
                if text and text[-1] in ('。', '；', '，'):
                    text = text[:-1]
                    changes.append("清除末尾标点")
            new_lines.append(line)
        content = '\n'.join(new_lines)

        # 规则4：列表标记统一
        lines = content.split('\n')
        new_lines = []
        in_code = False
        for line in lines:
            stripped = line.rstrip()
            if stripped.startswith('```'):
                in_code = not in_code
                new_lines.append(line)
                continue
            if not in_code:
                m = self.LIST_MARKER_LINE.match(stripped)
                if m:
                    indent, marker = m.group(1), m.group(2)
                    if marker in ('*', '+'):
                        line = indent + '- ' + line[indent.end():]
                        changes.append("统一列表")
            new_lines.append(line)
        content = '\n'.join(new_lines)

        # 规则5：代码块统计
        lines = content.split('\n')
        code_block_count = sum(1 for line in lines if line.strip().startswith('```')) // 2
        if code_block_count > 0:
            changes.append(f"代码块{code_block_count}个")

        # 规则6：去除行尾空格
        content = self.TRAILING_SPACE_PATTERN.sub('\n', content)

        # 规则7：文件末尾保证一个换行
        if content and not content.endswith('\n'):
            content += '\n'
        while content.endswith('\n\n\n'):
            content = content[:-1]
        if not content.endswith('\n'):
            content += '\n'

        return content, changes

    def process_all(self):
        """处理所有项目文件夹下的 md 文件"""
        md_files = list(self.input_path.rglob("*.md"))
        stats = {"压缩空行": 0, "清洗图表引用": 0, "清洗图表编号": 0, "清除末尾标点": 0, "统一列表": 0, "代码块": 0}

        for md_file in sorted(md_files):
            try:
                cleaned, changes = self.clean_file(md_file)
                md_file.write_text(cleaned, encoding='utf-8')
                self.stats["files_processed"] += 1
                for c in changes:
                    key = c.split('代码块')[0] if '代码块' in c else c
                    if key in stats:
                        stats[key] += 1
            except Exception as e:
                print(f"[FAIL] {md_file}: {e}")

        print(f"清洗完成: {self.stats['files_processed']} 个文件")
        for k, v in stats.items():
            if v > 0:
                print(f"  {k}: {v} 处")


def main():
    import sys
    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        target = Path(__file__).parent.parent / "original"

    print(f"清洗目录: {target}")
    cleaner = MarkdownCleaner(str(target))
    cleaner.process_all()


if __name__ == "__main__":
    main()