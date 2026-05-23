"""
Word to Markdown splitter (项目md专用版).
使用 zipfile + lxml 直接解析 XML，跳过 python-docx 的抽象层，
以解决圆角文本框（textbox）内容无法提取的问题。
"""
import zipfile
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from lxml import etree


class WordToMarkdown:
    """
    Word → Markdown 项目专用切分器。

    输出目录结构：
    original/
    ├── 项目一 xxx/
    │   ├── base/           (任务基础内容)
    │   │   ├── task1.md
    │   │   └── task2.md
    │   ├── perception/     (任务感知内容)
    │   │   ├── task1.md
    │   │   └── task2.md
    │   └── 项目一.md       (完整内容)
    │
    └── 项目二 xxx/
        └── ...
    """

    PERCEPTION_SECTION_MARKERS = {'【知识储备】', '【任务实施】'}
    BASE_SECTION_MARKERS = {'【任务描述】', '【任务能力目标】', '【任务重难点】', '【任务小结】', '【任务拓展】'}
    PROJECT_LEVEL_HEADING3 = {'【情境导入】'}

    # 命名空间
    NS = {
        'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
        'v': 'urn:schemas-microsoft-com:vml',
        'mc': 'http://schemas.openxmlformats.org/markup-compatibility/2006',
        'wps': 'http://schemas.microsoft.com/office/word/2010/wordprocessingShape',
        'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
    }

    def __init__(self, output_base: str = None):
        if output_base is None:
            self.output_base = Path(__file__).parent.parent / "original"
        else:
            self.output_base = Path(output_base)
        self._style_cache = {}  # styleId -> styleName

    def _load_styles(self, doc_path: str):
        """加载 styles.xml，构建 styleId -> styleName 的映射"""
        self._style_cache = {}
        with zipfile.ZipFile(doc_path, 'r') as zf:
            styles_xml = zf.read('word/styles.xml')
        tree = etree.fromstring(styles_xml)
        for style in tree.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}style'):
            style_id = style.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}styleId')
            name_elem = style.find('w:name', self.NS)
            if name_elem is not None:
                style_name = name_elem.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val')
                self._style_cache[style_id] = style_name

    def _resolve_style(self, style_id: str) -> str:
        """将 styleId 解析为 styleName"""
        if style_id in self._style_cache:
            return self._style_cache[style_id]
        return style_id or 'Normal'

    def split(self, doc_path: str, output_dir: str = None) -> Dict:
        """
        执行切分，只输出项目md文件。
        """
        doc_name = Path(doc_path).stem

        if output_dir is None:
            output_dir = self.output_base
        else:
            output_dir = Path(output_dir)

        # 加载样式映射
        self._load_styles(doc_path)

        # 解析 docx
        paragraphs, textboxes = self._parse_docx(doc_path)

        # 按 Heading 1 分项目
        projects = self._split_by_heading1(paragraphs, textboxes)

        all_files = []
        for project_name, project_data in projects.items():
            project_dir = output_dir / project_name
            files = self._create_project_output(project_dir, project_name, project_data)
            all_files.extend(files)

        return {
            "output_dir": str(output_dir),
            "project_count": len(projects),
            "files": all_files
        }

    def _parse_docx(self, doc_path: str) -> Tuple[List[dict], Dict[int, str]]:
        """
        使用 zipfile + lxml 直接解析 document.xml，
        返回 (paragraphs, textboxes) 元组。

        paragraphs: list of {style, text, body_index}
        textboxes: dict of {body_index: text}
        """
        paragraphs = []
        textboxes = {}

        with zipfile.ZipFile(doc_path, 'r') as zf:
            # 读取 document.xml
            xml_data = zf.read('word/document.xml')

        # 解析 XML
        tree = etree.fromstring(xml_data)

        # 获取 body
        body = tree.find('.//w:body', self.NS)
        if body is None:
            body = tree

        body_index = 0
        for child in body:
            tag_local = etree.QName(child).localname

            if tag_local == 'p':
                # 普通段落
                para = self._parse_paragraph(child)
                if para:
                    para['body_index'] = body_index
                    paragraphs.append(para)
                body_index += 1

            elif tag_local == 'tbl':
                # 表格 - 遍历所有段落
                for p in child.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'):
                    para = self._parse_paragraph(p)
                    if para:
                        para['body_index'] = body_index
                        paragraphs.append(para)
                    body_index += 1

            elif tag_local == 'sdt':
                # Structured document tag (可能包含 textbox)
                content = child.find('.//w:t', self.NS)
                if content is not None and content.text:
                    textboxes[body_index] = content.text.strip()
                body_index += 1

        return paragraphs, textboxes

    def _parse_paragraph(self, p_elem) -> Optional[dict]:
        """解析单个段落元素"""
        # 获取样式（可能是 ID，需要解析）
        pPr = p_elem.find('w:pPr', self.NS)
        style = None
        if pPr is not None:
            pStyle = pPr.find('w:pStyle', self.NS)
            if pStyle is not None:
                style_id = pStyle.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val')
                style = self._resolve_style(style_id)

        # 检测代码样式（代码、代码2）
        is_code = False
        if style:
            style_lower = style.lower()
            if '代码' in style_lower:
                is_code = True

        # 获取文本内容
        texts = []
        for t in p_elem.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'):
            if t.text:
                texts.append(t.text)

        text = ''.join(texts).strip()

        # 判断是否为空段落（只有空白字符）
        full_text = ''
        for t in p_elem.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'):
            if t.text:
                full_text += t.text

        if not full_text.strip():
            return None

        return {
            'style': style or 'Normal',
            'text': text,
            'is_code': is_code
        }

    def _extract_textboxes_vml(self, doc_path: str) -> Dict[int, str]:
        """
        从 VML shape 中提取文本框内容（备用方法）。
        处理圆形矩阵等无法用标准方式提取的元素。
        """
        textboxes = {}

        with zipfile.ZipFile(doc_path, 'r') as zf:
            xml_data = zf.read('word/document.xml')

        tree = etree.fromstring(xml_data)
        body = tree.find('.//w:body', self.NS)
        if body is None:
            body = tree

        # 查找所有 AlternateContent
        for idx, elem in enumerate(body):
            xml_str = etree.tostring(elem, encoding='unicode')

            if 'AlternateContent' not in xml_str:
                continue

            # 提取 Primary 或 Choice 内容
            choice_match = re.search(r'<mc:Choice[^>]*>(.*?)</mc:Choice>', xml_str, re.DOTALL)
            fallback_match = re.search(r'<mc:Fallback[^>]*>(.*?)</mc:Fallback>', xml_str, re.DOTALL)

            content_match = choice_match or fallback_match
            if not content_match:
                continue

            content_str = content_match.group(1)

            # 提取 wps:txbx 或 w:txbxContent
            txbx_match = re.search(r'<wps:txbx>(.*?)</wps:txbx>', content_str, re.DOTALL)
            if not txbx_match:
                txbx_match = re.search(r'<w:txbxContent>(.*?)</w:txbxContent>', content_str, re.DOTALL)

            if not txbx_match:
                continue

            txbx_xml = txbx_match.group(1)
            texts = re.findall(r'<w:t[^>]*>([^<]*)</w:t>', txbx_xml)
            text = ''.join(texts).strip()

            if text:
                textboxes[idx] = text

        return textboxes

    def _split_by_heading1(self, paragraphs: List[dict], textboxes: Dict[int, str]) -> Dict:
        """按 Heading 1 将文档分成多个项目"""
        projects = {}
        current_project = None
        current_h2 = None
        current_section = None
        before_task_content = []
        task_contents = {}

        # 代码块状态追踪
        in_code_block = False

        for idx, para in enumerate(paragraphs):
            style_name = para.get('style', 'Normal')
            text = para.get('text', '').strip()
            is_code = para.get('is_code', False)

            # 标准化样式名
            # Word XML 中 style 可能存为 ID（如 "2"）或名称（如 "heading 1"）
            # python-docx 解析后可能得到 styleId 或本地化的 name
            style_lower = style_name.lower().strip()
            is_heading1 = style_lower in ('heading 1', '1', 'heading1') or 'heading 1' in style_lower
            is_heading2 = style_lower in ('heading 2', '2', 'heading2') or 'heading 2' in style_lower
            is_heading3 = style_lower in ('heading 3', '3', 'heading3') or 'heading 3' in style_lower
            is_heading4 = style_lower in ('heading 4', '4', 'heading4') or 'heading 4' in style_lower
            is_heading5 = style_lower in ('heading 5', '5', 'heading5') or 'heading 5' in style_lower

            # 处理代码块状态切换（仅在非代码段落时处理）
            if is_code and not in_code_block:
                # 进入代码块
                if current_h2 and task_contents:
                    task_num = self._get_last_task_num(task_contents)
                    if task_num and task_num in task_contents:
                        task_contents[task_num]["full_content"].append("```")
                        task_contents[task_num]["base_content"].append("```")
                        task_contents[task_num]["perception_content"].append("```")
                elif current_project and not current_h2:
                    before_task_content.append("```")
                in_code_block = True
            elif not is_code and in_code_block:
                # 退出代码块
                if current_h2 and task_contents:
                    task_num = self._get_last_task_num(task_contents)
                    if task_num and task_num in task_contents:
                        task_contents[task_num]["full_content"].append("```")
                        task_contents[task_num]["base_content"].append("```")
                        task_contents[task_num]["perception_content"].append("```")
                elif current_project and not current_h2:
                    before_task_content.append("```")
                in_code_block = False

            # 检查 textbox
            if idx in textboxes and current_project:
                tb_text = textboxes[idx]
                if current_h2 and task_contents:
                    task_num = self._get_last_task_num(task_contents)
                    if task_num and task_num in task_contents:
                        task_contents[task_num]["full_content"].append(tb_text)
                        task_contents[task_num]["base_content"].append(tb_text)

            if not text and not is_code:
                continue

            # Heading 1 - 新项目开始
            if is_heading1:
                # 退出任何代码块
                in_code_block = False
                if current_project is not None:
                    projects[current_project] = {
                        "before_task": list(before_task_content),
                        "tasks": dict(task_contents)
                    }

                current_project = text
                current_h2 = None
                before_task_content = []
                task_contents = {}
                current_section = None

            # Heading 2 - 新任务开始
            elif is_heading2 and current_project:
                in_code_block = False
                current_h2 = text
                task_num = self._extract_task_num(text)
                if task_num:
                    task_contents[task_num] = {
                        "title": text,
                        "full_content": [],
                        "base_content": [],
                        "perception_content": []
                    }
                current_section = None

            # 项目级别 Heading 3
            elif text in self.PROJECT_LEVEL_HEADING3 and current_project:
                in_code_block = False
                if current_h2 and task_contents:
                    task_num = self._get_last_task_num(task_contents)
                    if task_num and task_num in task_contents:
                        task_contents[task_num]["full_content"].append(f"### {text}")
                        task_contents[task_num]["base_content"].append(f"### {text}")
                elif not current_h2:
                    before_task_content.append(f"### {text}")

            # 特殊章节标题
            elif text in self.PERCEPTION_SECTION_MARKERS:
                in_code_block = False
                current_section = "perception"
                if current_project:
                    if current_h2 and task_contents:
                        task_num = self._get_last_task_num(task_contents)
                        if task_num and task_num in task_contents:
                            h3_text = f"### {text}"
                            task_contents[task_num]["full_content"].append(h3_text)
                            task_contents[task_num]["perception_content"].append(h3_text)
                    elif not current_h2:
                        before_task_content.append(f"### {text}")

            elif text in self.BASE_SECTION_MARKERS:
                in_code_block = False
                current_section = "base"
                if current_project:
                    if current_h2 and task_contents:
                        task_num = self._get_last_task_num(task_contents)
                        if task_num and task_num in task_contents:
                            h3_text = f"### {text}"
                            task_contents[task_num]["full_content"].append(h3_text)
                            task_contents[task_num]["base_content"].append(h3_text)
                    elif not current_h2:
                        before_task_content.append(f"### {text}")

            # Heading 3
            elif is_heading3 and current_h2:
                in_code_block = False
                if current_h2 and task_contents:
                    task_num = self._get_last_task_num(task_contents)
                    if task_num and task_num in task_contents:
                        h3_text = f"### {text}"
                        task_contents[task_num]["full_content"].append(h3_text)
                        if current_section == "base":
                            task_contents[task_num]["base_content"].append(h3_text)
                        elif current_section == "perception":
                            task_contents[task_num]["perception_content"].append(h3_text)

            # Heading 4
            elif is_heading4 and current_h2:
                in_code_block = False
                if current_h2 and task_contents:
                    task_num = self._get_last_task_num(task_contents)
                    if task_num and task_num in task_contents:
                        h4_text = f"#### {text}"
                        task_contents[task_num]["full_content"].append(h4_text)
                        if current_section == "base":
                            task_contents[task_num]["base_content"].append(h4_text)
                        elif current_section == "perception":
                            task_contents[task_num]["perception_content"].append(h4_text)

            # Heading 5
            elif is_heading5 and current_h2:
                in_code_block = False
                if current_h2 and task_contents:
                    task_num = self._get_last_task_num(task_contents)
                    if task_num and task_num in task_contents:
                        h5_text = f"##### {text}"
                        task_contents[task_num]["full_content"].append(h5_text)
                        if current_section == "base":
                            task_contents[task_num]["base_content"].append(h5_text)
                        elif current_section == "perception":
                            task_contents[task_num]["perception_content"].append(h5_text)

            # 代码段落 - 使用 ``` 包围（相邻代码段落合并为一个代码块）
            elif current_project and is_code:
                code_text = text
                if current_h2 and task_contents:
                    task_num = self._get_last_task_num(task_contents)
                    if task_num and task_num in task_contents:
                        # 代码块已在状态切换时打开，这里只添加代码文本
                        task_contents[task_num]["full_content"].append(code_text)
                        if current_section == "base":
                            task_contents[task_num]["base_content"].append(code_text)
                        elif current_section == "perception":
                            task_contents[task_num]["perception_content"].append(code_text)
                        else:
                            task_contents[task_num]["base_content"].append(code_text)
                elif current_project and not current_h2:
                    # 代码块已在状态切换时打开，这里只添加代码文本
                    before_task_content.append(code_text)

            # 普通文本
            elif current_project and text:
                # 非代码段落，退出代码块时添加结束标记
                if in_code_block:
                    if current_h2 and task_contents:
                        task_num = self._get_last_task_num(task_contents)
                        if task_num and task_num in task_contents:
                            task_contents[task_num]["full_content"].append("```")
                            task_contents[task_num]["base_content"].append("```")
                            task_contents[task_num]["perception_content"].append("```")
                    elif current_project and not current_h2:
                        before_task_content.append("```")
                    in_code_block = False
                if current_h2 and task_contents:
                    task_num = self._get_last_task_num(task_contents)
                    if task_num and task_num in task_contents:
                        task_contents[task_num]["full_content"].append(text)
                        if current_section == "base":
                            task_contents[task_num]["base_content"].append(text)
                        elif current_section == "perception":
                            task_contents[task_num]["perception_content"].append(text)
                        else:
                            task_contents[task_num]["base_content"].append(text)
                elif current_project and not current_h2:
                    before_task_content.append(text)

        # 项目结束前关闭代码块
        if in_code_block:
            in_code_block = False

        if current_project is not None:
            projects[current_project] = {
                "before_task": list(before_task_content),
                "tasks": dict(task_contents)
            }

        return projects

    def _extract_task_num(self, text: str) -> Optional[str]:
        match = re.search(r'任务([一二三四五六\d]+)', text)
        if match:
            return self._chinese_to_arabic(match.group(1))
        return None

    def _chinese_to_arabic(self, cn: str) -> str:
        mapping = {
            "一": "1", "二": "2", "三": "3",
            "四": "4", "五": "5", "六": "6"
        }
        if cn in mapping:
            return mapping[cn]
        if cn.isdigit():
            return cn
        return cn

    def _get_last_task_num(self, task_contents: Dict) -> Optional[str]:
        if not task_contents:
            return None
        return max(task_contents.keys(), key=lambda x: int(x) if x.isdigit() else 0)

    def _create_project_output(self, project_dir: Path, project_name: str, project_data: Dict) -> List[str]:
        """为一个项目创建输出目录结构：创建 base/, perception/ 空文件夹，输出完整项目md"""
        project_dir.mkdir(parents=True, exist_ok=True)
        base_dir = project_dir / "base"
        perception_dir = project_dir / "perception"
        base_dir.mkdir(exist_ok=True)
        perception_dir.mkdir(exist_ok=True)

        files = []
        project_md_name = f"{project_name}.md"
        project_md = project_dir / project_md_name

        before_task = project_data.get("before_task", [])
        tasks = project_data.get("tasks", {})

        content_parts = [f"# {project_name}\n"]
        if before_task:
            content_parts.append("# before task\n\n")
            content_parts.append("\n".join(before_task))
            content_parts.append("\n")

        for task_num, task_data in sorted(tasks.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0):
            task_title = task_data.get("title", f"Task {task_num}")
            full_content = task_data.get("full_content", [])

            if full_content:
                content_parts.append(f"\n# {task_title}\n")
                content_parts.append("\n".join(full_content))

        content = "\n".join(content_parts)
        project_md.write_text(content, encoding='utf-8')
        files.append(f"{project_name}/{project_md_name}")

        return files


def main():
    """测试入口"""
    from pathlib import Path

    input_dir = Path(__file__).parent.parent.parent / "input"
    # 过滤临时文件（Word 打开时产生的 ~$ 前缀）
    docx_files = [f for f in input_dir.glob("*.docx") if not f.name.startswith('~$')]

    if not docx_files:
        print(f"错误: {input_dir} 中未找到 .docx 文件")
        return

    doc_path = docx_files[0]
    print(f"输入: {doc_path}")

    splitter = WordToMarkdown()
    result = splitter.split(str(doc_path))

    print(f"切分完成！")
    print(f"输出目录: {result['output_dir']}")
    print(f"项目数: {result['project_count']}")
    print(f"生成文件数: {len(result['files'])}")
    for f in result['files']:
        print(f"  - {f}")


if __name__ == "__main__":
    main()