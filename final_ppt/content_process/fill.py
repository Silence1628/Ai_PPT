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
from collections import OrderedDict
from pathlib import Path

import win32com.client
import pythoncom


class FillProcessor:
    """填充 temp PPTX 占位符"""

    def __init__(self, temp_dir: Path):
        self.temp_dir = Path(temp_dir)

    def _get_ppt_app(self):
        """获取 PowerPoint COM 对象"""
        import pythoncom

        try:
            return win32com.client.GetActiveObject("PowerPoint.Application")
        except Exception:
            pass

        try:
            return win32com.client.Dispatch("WPP.Application")
        except Exception:
            try:
                return win32com.client.Dispatch("PowerPoint.Application")
            except Exception:
                print("    [ERROR] Cannot start PowerPoint application")
                return None

    def process_all(self, padding_dir: Path) -> dict:
        """
        一次打开 PowerPoint，处理 padding 下的所有 task。

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
            k_dir = padding_dir / "knowledge"
            t_dir = padding_dir / "task"
            for k_file in sorted(k_dir.glob("task*_knowledge.json")):
                task_num = k_file.stem.replace("_knowledge", "")
                t_file = t_dir / f"{task_num}_implementation.json"
                if not t_file.exists():
                    continue
                print(f"\n[Fill] {k_file.stem.replace('_knowledge','')}")
                result = self._process_padding(k_file, t_file, ppt_app)
                if result:
                    results[f"task{task_num}"] = result

            ppt_app.Quit()
            return results
        finally:
            pythoncom.CoUninitialize()

    def process(self, knowledge_json: Path, task_json: Path) -> dict:
        """
        读取 knowledge 和 task 的 padding JSON，填充对应的 temp PPTX。
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

            result = self._process_padding(knowledge_json, task_json, ppt_app)
            ppt_app.Quit()
            return result
        finally:
            pythoncom.CoUninitialize()

    @staticmethod
    def padding_to_section(chunks: list, module_type: str) -> dict:
        """将 padding chunks 按 H3 分组，转为 _fill_pptx 需要的 section 格式

        content_pages 映射规则：
        - knowledge: 10页模板，page_1~10 循环使用
        - task: 2页模板，page_1/page_2 交替使用
        """
        MAX_PAGES = 10 if module_type == "knowledge" else 2

        groups = OrderedDict()
        for chunk in chunks:
            parent = chunk.get("parent_title", "") or chunk.get("title", "")
            if parent not in groups:
                groups[parent] = []
            for sub in chunk.get("sub_chunks", []):
                groups[parent].append(sub.get("content", ""))

        segments = []
        page_idx = 0
        global_chunk_idx = 0
        for heading, contents in groups.items():
            page_idx += 1
            content_chunks = [{"chunk_index": i + 1, "content": ct}
                              for i, ct in enumerate(contents) if ct]
            pages = []
            for _ in range(len(content_chunks)):
                pages.append(f"page_{global_chunk_idx % MAX_PAGES + 1}")
                global_chunk_idx += 1
            segments.append({
                "heading": heading,
                "heading_chunk_count": len(content_chunks),
                "content_chunks": content_chunks,
                "subcatelog_page": f"page_{page_idx}",
                "content_pages": pages
            })

        return {"segments": segments, "subcatelog_dir": ""}

    def _process_padding(self, knowledge_json: Path, task_json: Path, ppt_app) -> dict:
        """处理单个 task 的 knowledge + task padding 文件"""
        k_data = json.loads(knowledge_json.read_text(encoding='utf-8'))
        t_data = json.loads(task_json.read_text(encoding='utf-8'))

        task_num = k_data.get("task_num", "")
        k_section = self.padding_to_section(k_data.get("chunks", []), "knowledge")
        t_section = self.padding_to_section(t_data.get("chunks", []), "task")

        print(f"  [Fill] task={task_num}")

        knowledge_output = self._fill_pptx(
            ppt_app, k_section, task_num, "knowledge", "03", "知识储备"
        )
        task_output = self._fill_pptx(
            ppt_app, t_section, task_num, "task", "04", "任务实施"
        )

        return {"knowledge": knowledge_output, "task": task_output}

    def _fill_pptx(
        self, ppt_app, section_data: dict, task_num: str,
        module_type: str, cate_num: str, replace_text: str
    ) -> Path:
        """填充单个 section (knowledge/task) 的 PPTX"""
        segments = section_data.get("segments", [])
        all_headings = [seg.get("heading", "") for seg in segments]

        module_suffix = "knowledge" if module_type == "knowledge" else "implementation"
        pptx_file = self.temp_dir / module_type / f"task{task_num}_{module_suffix}.pptx"
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

    PROJECT_ROOT = PathLib(__file__).parent.parent.parent.resolve()
    sys.path.insert(0, str(PROJECT_ROOT))

    TEMP_DIR = PROJECT_ROOT / "final_ppt" / "temp"
    PADDING_BASE = PROJECT_ROOT / "word_process" / "llm_output" / "perception_json"

    processor = FillProcessor(TEMP_DIR)

    print("=" * 60)
    print("Fill Processor: 填充 temp PPTX 占位符")
    print("=" * 60)

    project_dirs = sorted([d for d in PADDING_BASE.iterdir() if d.is_dir() and d.name.startswith('项目')])
    for project_dir in project_dirs:
        print(f"\n[Project] {project_dir.name}")
        processor.process_all(project_dir)

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)