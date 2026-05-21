"""
fill_processor - 填充 temp PPTX 中的占位符

占位符规范：
- {{text:cate_num}}: subcatelog页，knowledge="03", task="04"
- {{text:replace}}: subcatelog页，knowledge="知识储备", task="任务实施"
- {{text:point_N}}: subcatelog页，N=1~heading_chunk_count，对应 heading 字段
- {{text:content}}: content页，对应 content_chunks[].content
"""
import json
import re
from pathlib import Path

import win32com.client
import pythoncom


class FillProcessor:
    """填充 temp PPTX 占位符"""

    def __init__(self, temp_dir: Path, mapping_dir: Path):
        self.temp_dir = Path(temp_dir)
        self.mapping_dir = Path(mapping_dir)

    def _get_ppt_app(self):
        """获取 PowerPoint COM 对象"""
        import pythoncom

        # 尝试获取已有实例
        try:
            return win32com.client.GetActiveObject("PowerPoint.Application")
        except Exception:
            pass

        # 尝试创建新实例
        try:
            return win32com.client.Dispatch("WPP.Application")
        except Exception:
            try:
                return win32com.client.Dispatch("PowerPoint.Application")
            except Exception:
                print("    [ERROR] Cannot start PowerPoint application")
                return None

    def process_all(self) -> dict:
        """
        一次打开 PowerPoint，处理所有 mapping JSON。

        Returns:
            dict: {task_num: {"knowledge": Path, "task": Path}} 填充后的文件路径
        """
        pythoncom.CoInitialize()
        try:
            ppt_app = self._get_ppt_app()
            if not ppt_app:
                return None

            try:
                ppt_app.Visible = -1
            except Exception:
                pass
            try:
                ppt_app.DisplayAlerts = 0
            except Exception:
                pass

            results = {}
            for mapping_json in sorted(self.mapping_dir.glob("task*_mapping.json")):
                print(f"\n[Fill] {mapping_json.name}")
                result = self._process_one_mapping(mapping_json, ppt_app)
                if result:
                    results[mapping_json.stem] = result

            ppt_app.Quit()
            return results
        finally:
            pythoncom.CoUninitialize()

    def process_from_mapping(self, mapping_json: Path) -> dict:
        """
        读取 mapping JSON，填充对应的 temp PPTX。
        每次调用都会打开关闭 PowerPoint（向后兼容）。

        Returns:
            dict: {"knowledge": Path, "task": Path} 填充后的文件路径
        """
        pythoncom.CoInitialize()
        try:
            ppt_app = self._get_ppt_app()
            if not ppt_app:
                return None

            try:
                ppt_app.Visible = -1
            except Exception:
                pass
            try:
                ppt_app.DisplayAlerts = 0
            except Exception:
                pass

            result = self._process_one_mapping(mapping_json, ppt_app)
            ppt_app.Quit()
            return result
        finally:
            pythoncom.CoUninitialize()

    def _process_one_mapping(self, mapping_json: Path, ppt_app) -> dict:
        """处理单个 mapping JSON 文件"""
        with open(mapping_json, "r", encoding="utf-8") as f:
            mapping_data = json.load(f)

        task_num = mapping_data.get("task_num", "")
        knowledge_data = mapping_data.get("knowledge", {})
        task_section_data = mapping_data.get("task", {})

        print(f"  [FillProcessor] task={task_num}")

        # 填充 knowledge PPTX
        knowledge_output = self._fill_pptx(
            ppt_app,
            knowledge_data,
            task_num,
            "knowledge",
            "03",
            "知识储备"
        )

        # 填充 task PPTX
        task_output = self._fill_pptx(
            ppt_app,
            task_section_data,
            task_num,
            "task",
            "04",
            "任务实施"
        )

        return {"knowledge": knowledge_output, "task": task_output}

    def _fill_pptx(
        self, ppt_app, section_data: dict, task_num: str,
        module_type: str, cate_num: str, replace_text: str
    ) -> Path:
        """填充单个 section (knowledge/task) 的 PPTX"""
        segments = section_data.get("segments", [])
        all_headings = [seg.get("heading", "") for seg in segments]

        pptx_file = self.temp_dir / module_type / f"task{task_num}_{module_type}.pptx"
        if not pptx_file.exists():
            print(f"    [WARN] file not found: {pptx_file}")
            return None

        presentation = ppt_app.Presentations.Open(
            str(pptx_file.absolute()), ReadOnly=0, Untitled=0, WithWindow=0
        )

        slide_index = 1  # 1-based index for PPT slides

        # 按顺序处理每个 segment：
        # 结构是：subcatelog -> content页(共chunk_count个) -> subcatelog -> ...
        for seg_idx, seg in enumerate(segments, start=1):
            if slide_index > presentation.Slides.Count:
                break

            # 填充 subcatelog 页
            slide = presentation.Slides(slide_index)
            self._fill_subcatelog_page(
                slide, cate_num, replace_text, all_headings
            )
            print(f"    [Fill] slide {slide_index} ({module_type}) subcatelog")
            slide_index += 1

            # 跳过 content 页（用 chunk_count 计算）
            content_chunks = seg.get("content_chunks", [])
            chunk_count = seg.get("heading_chunk_count", 0)

            for chunk_idx in range(chunk_count):
                if slide_index > presentation.Slides.Count:
                    break
                slide = presentation.Slides(slide_index)
                content = content_chunks[chunk_idx].get("content", "") if chunk_idx < len(content_chunks) else ""
                self._fill_content_page(slide, content)
                print(f"    [Fill] slide {slide_index} ({module_type}) content chunk {chunk_idx + 1}")
                slide_index += 1

        presentation.Save()
        presentation.Close()
        print(f"    → {pptx_file.name} filled")
        return pptx_file

    def _fill_subcatelog_page(
        self, slide, cate_num: str, replace_text: str,
        all_headings: list
    ):
        """填充 subcatelog 页的占位符"""
        # 英文单词到数字的映射
        english_nums = {
            "one": 1, "two": 2, "three": 3, "four": 4,
            "five": 5, "six": 6, "seven": 7, "eight": 8,
            "nine": 9, "ten": 10
        }

        for i in range(1, slide.Shapes.Count + 1):
            shape = slide.Shapes.Item(i)
            if not shape.HasTextFrame:
                continue

            text = shape.TextFrame.TextRange.Text
            if not text:
                continue

            new_text = text

            # 替换 {{text：cate_num}} (全角冒号)
            new_text = new_text.replace("{{text：cate_num}}", cate_num)
            new_text = new_text.replace("{{text:cate_num}}", cate_num)

            # 替换 {{text：replace}} (全角冒号)
            new_text = new_text.replace("{{text：replace}}", replace_text)
            new_text = new_text.replace("{{text:replace}}", replace_text)

            # 替换 {{text:point_one}} ~ {{text:point_ten}}
            for word, num in english_nums.items():
                placeholder = f"{{{{text:point_{word}}}}}"
                if placeholder in new_text and num <= len(all_headings):
                    new_text = new_text.replace(placeholder, all_headings[num - 1])

            if new_text != text:
                shape.TextFrame.TextRange.Text = new_text

    def _fill_content_page(self, slide, content: str):
        """填充 content 页的 {{text:content}} 占位符"""
        for i in range(1, slide.Shapes.Count + 1):
            shape = slide.Shapes.Item(i)
            if not shape.HasTextFrame:
                continue

            text = shape.TextFrame.TextRange.Text
            if "{{text:content}}" in text:
                new_text = text.replace("{{text:content}}", content)
                shape.TextFrame.TextRange.Text = new_text


if __name__ == "__main__":
    import sys
    from pathlib import Path as PathLib

    PROJECT_ROOT = PathLib(__file__).parent.parent.resolve()
    sys.path.insert(0, str(PROJECT_ROOT))

    TEMP_DIR = PROJECT_ROOT / "PPT_Perception" / "temp"
    MAPPING_DIR = PROJECT_ROOT / "PPT_Perception" / "mapping"

    processor = FillProcessor(TEMP_DIR, MAPPING_DIR)

    print("=" * 60)
    print("Fill Processor: 填充 temp PPTX 占位符")
    print("=" * 60)

    processor.process_all()

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)