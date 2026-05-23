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
        original_lines = content.split('\n')
        changes = []

        # 检查是否在代码块内
        in_code_block = False
        code_block_start = None
        cleaned_lines = []

        for line in original_lines:
            stripped = line.rstrip()

            # 跟踪代码块状态
            if stripped.startswith('```'):
                if not in_code_block:
                    in_code_block = True
                    code_block_start = len(cleaned_lines)
                else:
                    in_code_block = False

            # 规则1：图表标题行（代码块内不过滤）
            if not in_code_block:
                if (self.CHART_TITLE_PATTERN.match(stripped) or
                    self.TABLE_TITLE_PATTERN.match(stripped)):
                    changes.append(f"  删除图表标题行: {stripped[:60]}")
                    continue

            # 规则6：行尾空格
            if ' \t' in line and not stripped.startswith('```'):
                changes.append(f"  去除行尾空格: {stripped[:60]}")

            cleaned_lines.append(line)

        content = '\n'.join(cleaned_lines)

        # 规则2：压缩连续空行
        before = len(content)
        content = self.MULTI_BLANK_PATTERN.sub('\n\n', content)
        if len(content) != before:
            changes.append(f"  压缩连续空行: -{before - len(content)} chars")

        # 规则2b：正文中的图表引用编号清洗（保留后面文字）
        # "如图 1-1- 1" → "如图 "
        new_content = self.FIGURE_REF_PATTERN.sub('如图 ', content)
        if new_content != content:
            changes.append(f"  清洗正文图表引用编号")
        content = new_content

        # 规则2c：清洗正文中独立的 x-x-x 或 x-x- x 格式编号
        count = len(self.REF_NUM_PATTERN.findall(content))
        count2 = len(self.REF_NUM_PATTERN_NOSPACE.findall(content))
        new_content = self.REF_NUM_PATTERN.sub('', content)
        new_content = self.REF_NUM_PATTERN_NOSPACE.sub('', new_content)
        if new_content != content:
            changes.append(f"  清洗正文图表编号: {count + count2}处")
        content = new_content

        # 规则3：清除标题末尾标点
        lines = content.split('\n')
        new_lines = []
        for line in lines:
            stripped = line.rstrip()
            # 检查是否是标题行
            m = re.match(r'^(#{1,6}\s*)(.+)', stripped)
            if m:
                prefix, text = m.group(1), m.group(2)
                # 去除末尾的 。 ；
                if text and text[-1] in ('。', '；', '，'):
                    orig = text
                    text = text[:-1]
                    changes.append(f"  清除标题末尾标点: {prefix}{orig} → {prefix}{text}")
            new_lines.append(line)
        content = '\n'.join(new_lines)

        # 规则4：列表标记统一（只在非代码块行处理）
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
                # 普通列表项
                m = self.LIST_MARKER_LINE.match(stripped)
                if m:
                    indent, marker = m.group(1), m.group(2)
                    if marker in ('*', '+'):
                        orig = line
                        line = indent + '- ' + line[indent.end():]
                        changes.append(f"  统一列表标记: '{marker}' → '-' in: {stripped[:50]}")
                # 任务列表 - 保持 - [ ] 不变，只处理 - [x] → - [x] (已是标准格式)
            new_lines.append(line)
        content = '\n'.join(new_lines)

        # 规则5：代码块语言标注
        lines = content.split('\n')
        new_lines = []
        in_code_block = False
        code_lang = None
        for i, line in enumerate(lines):
            stripped = line.rstrip()
            if stripped.startswith('```'):
                if not in_code_block:
                    in_code_block = True
                    # 提取语言标识
                    lang = stripped[3:].strip()
                    if lang:
                        code_lang = lang
                    else:
                        # 尝试从下一行推断语言
                        code_lang = None
                    new_lines.append(line)
                else:
                    in_code_block = False
                    code_lang = None
                    new_lines.append(line)
            elif in_code_block and code_lang is None and stripped:
                # 上一个代码块开始没有语言，尝试推断
                prev = new_lines[-1] if new_lines else ''
                if prev.startswith('```'):
                    # 常见语言推断
                    inferred = None
                    # Python
                    if 'import ' in stripped and ('def ' in stripped or 'class ' in stripped):
                        inferred = 'python'
                    # JavaScript
                    elif 'function ' in stripped or 'const ' in stripped or 'let ' in stripped:
                        inferred = 'javascript'
                    # JSON
                    elif stripped.strip().startswith('{') and stripped.strip().endswith('}'):
                        inferred = 'json'
                    # Bash
                    elif stripped.startswith('# ') or 'echo ' in stripped:
                        inferred = 'bash'

                    if inferred:
                        orig_lang = prev[3:].strip() or '(none)'
                        new_lines[-1] = f'```{inferred}'
                        changes.append(f"  补全代码块语言: {orig_lang} → {inferred}")
                        code_lang = inferred  # 保持这个语言直到代码块结束
                    new_lines.append(line)
            else:
                new_lines.append(line)
        content = '\n'.join(new_lines)

        # 规则6：去除行尾空格（再次）
        content = self.TRAILING_SPACE_PATTERN.sub('\n', content)

        # 规则7：文件末尾保证一个换行
        if content and not content.endswith('\n'):
            content += '\n'
        # 去除末尾多余空行（超过1个）
        while content.endswith('\n\n\n'):
            content = content[:-1]
        # 补一个换行
        if not content.endswith('\n'):
            content += '\n'

        return content, changes

    def process_all(self):
        """处理所有 md 文件（只处理项目级 md，如 项目一 xxx.md）"""
        md_files = list(self.input_path.rglob("*.md"))
        # 只处理项目级 md 文件（文件名含"项目"且直接在项目文件夹下）
        project_md_files = [f for f in md_files if f.name.startswith('项目') and f.parent.name != 'base' and f.parent.name != 'perception']
        print(f"找到 {len(md_files)} 个 MD 文件，其中项目级 {len(project_md_files)} 个")

        for md_file in sorted(project_md_files):
            try:
                cleaned, changes = self.clean_file(md_file)
                md_file.write_text(cleaned, encoding='utf-8')
                self.stats["files_processed"] += 1
                if changes:
                    print(f"\n[PASS] {md_file.relative_to(self.input_path)}")
                    for c in changes:
                        print(c)
                else:
                    print(f"\n[PASS] {md_file.relative_to(self.input_path)} (no change)")
            except Exception as e:
                print(f"\n[FAIL] {md_file}: {e}")

        print(f"\n完成: {self.stats['files_processed']} 个文件")


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