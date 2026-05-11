"""
PPT渲染器 - 基于 pywin32 和 template_schema.json
单位换算：1 cm = 360000 EMU
"""
import json
import re
from pathlib import Path
from typing import Dict, Any

import win32com.client


class PPTRenderer:
    """PPT渲染器"""

    def __init__(self, template_path: str, schema_path: str):
        self.template_path = Path(template_path)
        self.schema_path = Path(schema_path)
        self.schema = self._load_schema()
        self.ppt_app = None
        self.ppt_presentation = None

    def _load_schema(self) -> dict:
        with open(self.schema_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _start_ppt(self):
        """启动 WPS 或 MS Office COM 对象"""
        try:
            self.ppt_app = win32com.client.Dispatch("WPP.Application")
        except Exception:
            self.ppt_app = win32com.client.Dispatch("PowerPoint.Application")
        try:
            self.ppt_app.Visible = 1
        except Exception:
            pass
        try:
            self.ppt_app.DisplayAlerts = 0
        except Exception:
            pass

    def _open_presentation(self):
        self.ppt_presentation = self.ppt_app.Presentations.Open(
            str(self.template_path.absolute()),
            ReadOnly=0,
            Untitled=0,
            WithWindow=0
        )

    def render(self, data: Dict[str, Any], output_path: str):
        """根据data渲染PPT并保存"""
        try:
            self._start_ppt()
            self._open_presentation()

            for page_index, page in enumerate(self.schema.get('pages', [])):
                self._render_page(page, data, page_index)

            # 从data中获取task_num和task_name，用于构造输出文件名
            chinese_to_arabic = {'一': '1', '二': '2', '三': '3', '四': '4', '五': '5', '六': '6', '七': '7', '八': '8', '九': '9', '十': '10'}
            task_num = None
            task_name = None
            for page_data in data.values():
                if isinstance(page_data, dict):
                    if task_num is None and 'task_num' in page_data:
                        raw_num = str(page_data['task_num'])
                        task_num = chinese_to_arabic.get(raw_num, raw_num)
                    if task_name is None and 'task_name' in page_data:
                        task_name = page_data['task_name']
                    if task_num and task_name:
                        break

            # 构造输出文件名: 1.task_num_task_name.pptx
            if task_num and task_name:
                safe_task_name = re.sub(r'[<>:"/\\|?*]', '_', task_name)
                output_filename = f"1.{task_num}_{safe_task_name}.pptx"
                output_path = str(Path(output_path).parent / output_filename)

            output = Path(output_path)
            output.parent.mkdir(parents=True, exist_ok=True)
            self.ppt_presentation.SaveAs(str(output.absolute()))
        finally:
            self._close()

    def _render_page(self, page: dict, data: Dict[str, Any], page_index: int):
        if page_index >= self.ppt_presentation.Slides.Count:
            return
        slide = self.ppt_presentation.Slides(page_index + 1)
        for shape_config in page.get('shapes', []):
            self._render_shape(slide, shape_config, data)

    def _render_shape(self, slide, shape_config: dict, data: Dict[str, Any]):
        shape_name = shape_config.get('name', '')
        text_template = shape_config.get('text', '')

        # 跳过图片占位符
        if '{{image:' in text_template:
            return

        for i in range(1, slide.Shapes.Count + 1):
            shape = slide.Shapes.Item(i)
            if shape.Name == shape_name:
                new_text = self._set_shape_properties(shape, text_template, data, shape_config)

                # optional 且内容为空 → 删除该占位符文本框
                if shape_config.get('optional') and not new_text:
                    shape.Delete()
                break

    def _set_shape_properties(self, shape, text_template: str, data: Dict[str, Any], config: dict) -> str:
        if shape.HasTextFrame:
            text_frame = shape.TextFrame
            text_frame.WordWrap = config.get('word_wrap', True)

            # 处理 combine_fields：将多个字段合并
            processed_data = self._process_combine_fields(data, config)
            new_text = self._substitute_text(text_template, processed_data)

            # 保留模板格式，直接设置文本
            self._set_text_paragraph_preserved(text_frame, new_text)

            self._set_paragraph_alignment(text_frame, config)
            self._set_font_format(text_frame, config.get('font', {}))

            return new_text
        return ""

    def _process_combine_fields(self, data: Dict[str, Any], config: dict) -> Dict[str, Any]:
        """
        处理 combine_fields 配置，将多个字段合并为一个临时字段
        用于多段落内容（如任务要求分点罗列）
        """
        combine_fields = config.get('combine_fields')
        if not combine_fields:
            return data

        # 确保 combine_fields 是列表
        if isinstance(combine_fields, str):
            combine_fields = [combine_fields]

        if len(combine_fields) < 2:
            return data

        # 获取分隔符，默认换行
        separator = config.get('combine_separator', '\n')

        # 构建合并后的数据副本
        processed_data = {}
        for k, v in data.items():
            if isinstance(v, dict):
                processed_data[k] = v.copy()
            else:
                processed_data[k] = v

        # 对每个页面处理
        for page_key, page_data in processed_data.items():
            if isinstance(page_data, dict):
                # 检查是否有任何 combine_fields 在这个页面中
                values = []
                first_field = None
                for field in combine_fields:
                    if field in page_data:
                        values.append(str(page_data[field]))
                        if first_field is None:
                            first_field = field

                if values and first_field:
                    # 用分隔符合并
                    combined_value = separator.join(values)
                    # 替换第一个字段为合并后的值
                    processed_data[page_key][first_field] = combined_value

        return processed_data

    def _set_text_paragraph_preserved(self, text_frame, new_text: str):
        """
        直接设置文本，保留模板格式
        """
        try:
            text_frame.TextRange.Text = new_text
        except Exception:
            pass

    def _set_paragraph_alignment(self, text_frame, config: dict):
        try:
            alignment_map = {'left': 1, 'center': 2, 'right': 3, 'justify': 4}
            alignment = config.get('alignment', 'left')
            if alignment in alignment_map:
                text_frame.TextRange.ParagraphFormat.Alignment = alignment_map[alignment]
        except Exception:
            pass

    def _set_font_format(self, text_frame, font_config: dict):
        try:
            if not font_config:
                return
            font = text_frame.TextRange.Font
            if font_config.get('name'):
                font.Name = font_config['name']
            if font_config.get('size'):
                font.Size = font_config['size']
            if font_config.get('bold') is not None:
                font.Bold = font_config['bold']
        except Exception:
            pass

    def _substitute_text(self, text: str, data: Dict[str, Any]) -> str:
        def replace_field(match):
            field_name = match.group(1)
            for page_data in data.values():
                if isinstance(page_data, dict) and field_name in page_data:
                    return str(page_data[field_name])
            return match.group(0)
        return re.sub(r'\{\{text:(\w+)\}\}', replace_field, text)

    def _close(self):
        if self.ppt_presentation:
            self.ppt_presentation.Close()
            self.ppt_presentation = None
        if self.ppt_app:
            self.ppt_app.Quit()
            self.ppt_app = None


if __name__ == "__main__":
    import os

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    with open(os.path.join(project_root, 'examples', 'test_input.json'), 'r', encoding='utf-8') as f:
        test_data = json.load(f)

    renderer = PPTRenderer(
        template_path=os.path.join(project_root, 'templates', 'template.pptx'),
        schema_path=os.path.join(project_root, 'templates', 'template_schema.json')
    )

    renderer.render(test_data, os.path.join(project_root, 'output', 'test_output.pptx'))
    print("PPT渲染完成!")
