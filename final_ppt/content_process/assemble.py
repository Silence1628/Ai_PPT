"""
assemble - 根据 padding JSON 组装 temp PPTX

使用 InsertFromFile 从单页模板组装，供后续渲染：
- knowledge: 10 页模板循环
- task: 2 页模板循环
- subcatelog: heading4_count 页

输入：word_process/llm_input/perception/padding_json/{project}/{section}/task*_*.json
"""
import json
import shutil
from collections import OrderedDict
from pathlib import Path

import win32com.client
import pythoncom


class AssembleProcessor:
    """根据 padding JSON 直接组装 temp PPTX"""

    KNOWLEDGE_SINGLE_DIR = "knowledge/knowledge_single"
    TASK_SINGLE_DIR = "task/implementation_single"
    SUBCATELOG_SINGLE_DIR = "subcatelog"

    def __init__(self, template_dir: Path, temp_output_dir: Path):
        self.template_dir = Path(template_dir)
        self.temp_output_dir = Path(temp_output_dir)
        self.task_num = ""

    def process(self, knowledge_json: Path, task_json: Path) -> dict:
        """
        读取 knowledge 和 task 的 padding JSON，组装 temp PPTX。

        Returns:
            dict: {"knowledge": Path, "task": Path} 输出文件路径
        """
        k_data = json.loads(knowledge_json.read_text(encoding='utf-8'))
        t_data = json.loads(task_json.read_text(encoding='utf-8'))

        self.task_num = k_data.get("task_num", "")
        print(f"  [Assemble] task={self.task_num}  title={k_data.get('task_title','')}")

        k_section = self.padding_to_section(k_data.get("chunks", []), "knowledge")
        t_section = self.padding_to_section(t_data.get("chunks", []), "task")

        pythoncom.CoInitialize()
        try:
            ppt_app = win32com.client.Dispatch("WPP.Application")
        except Exception:
            ppt_app = win32com.client.Dispatch("PowerPoint.Application")
        try:
            try:
                ppt_app.Visible = -1
            except Exception:
                pass
            try:
                ppt_app.DisplayAlerts = 0
            except Exception:
                pass

            knowledge_output = self._build_temp_pptx(
                ppt_app, k_section,
                self.temp_output_dir / "knowledge", "knowledge"
            )
            task_output = self._build_temp_pptx(
                ppt_app, t_section,
                self.temp_output_dir / "task", "task"
            )

            try:
                ppt_app.Quit()
            except Exception:
                pass
            return {"knowledge": knowledge_output, "task": task_output}
        finally:
            pythoncom.CoUninitialize()

    @staticmethod
    def padding_to_section(chunks: list, module_type: str) -> dict:
        """将 padding chunks 按 H3 分组，转为 _build_temp_pptx 需要的 section 格式

        content_pages 映射规则：
        - knowledge: 10页模板，page_1~10 循环使用
        - task: 2页模板，page_1/page_2 交替使用
        """
        MAX_PAGES = 10 if module_type == "knowledge" else 2

        # Group sub_chunks by parent_title (H3 heading)
        groups = OrderedDict()
        for chunk in chunks:
            parent = chunk.get("parent_title", "") or chunk.get("title", "")
            if parent not in groups:
                groups[parent] = []
            for sub in chunk.get("sub_chunks", []):
                groups[parent].append(sub.get("content", ""))

        segment_count = len(groups)
        segments = []
        page_idx = 0
        global_chunk_idx = 0  # across all segments for consistent page assignment
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

        return {
            "subcatelog_dir": f"subcatelog/{segment_count}/catelog_single",
            "segments": segments
        }

    def _build_temp_pptx(
        self, ppt_app, section_data: dict,
        output_dir: Path, module_type: str
    ) -> Path:
        """组装单个 section (knowledge/task) 的 temp PPTX"""
        segments = section_data.get("segments", [])
        subcatelog_dir_name = section_data.get("subcatelog_dir", "")

        output_dir.mkdir(parents=True, exist_ok=True)
        module_suffix = "knowledge" if module_type == "knowledge" else "implementation"
        output_file = output_dir / f"task{self._get_task_num()}_{module_suffix}.pptx"

        # 清理可能存在的旧文件
        if output_file.exists():
            try:
                output_file.unlink()
            except PermissionError:
                pass

        # 从 subcatelog_dir 中提取 heading4_count (e.g., "subcatelog/2/catelog_single" → 2)
        section_heading4_count = 4  # fallback default
        if subcatelog_dir_name:
            parts = subcatelog_dir_name.split("/")
            if len(parts) >= 2:
                try:
                    section_heading4_count = int(parts[1])
                except ValueError:
                    pass

        # 用 subcatelog page_1 作为基础文件
        base_file = self.template_dir / self.SUBCATELOG_SINGLE_DIR / str(section_heading4_count) / "page_1.pptx"
        if not base_file.exists():
            print(f"    [WARN] base file not found: {base_file}")
            return None
        shutil.copy(base_file, output_file)

        # 打开复制后的文件
        presentation = ppt_app.Presentations.Open(
            str(output_file.absolute()), ReadOnly=0, Untitled=0, WithWindow=0
        )

        # 收集所有需要插入的幻灯片
        all_slides = []
        for seg in segments:
            subcatelog_page = seg.get("subcatelog_page", "page_1")
            content_pages = seg.get("content_pages", [])

            # subcatelog 页
            all_slides.append({
                "type": "subcatelog",
                "page": subcatelog_page,
                "heading4_count": section_heading4_count
            })

            # content 页
            for cp in content_pages:
                all_slides.append({
                    "type": "content",
                    "page": cp,
                    "module_type": module_type
                })

        if not all_slides:
            print(f"    [WARN] no slides to insert")
            return None

        # base page_1 已存在（复制过来的），从 all_slides 中移除第一个（避免重复插入）
        slides_to_insert = all_slides[1:]

        # 倒序插入剩余幻灯片（每次插入到位置1，最终顺序正确）
        for slide_info in reversed(slides_to_insert):
            template_pptx = self._get_template_path(slide_info, subcatelog_dir_name)
            if not template_pptx or not template_pptx.exists():
                print(f"    [WARN] template not found: {template_pptx}")
                continue

            presentation.Slides.InsertFromFile(
                str(template_pptx.absolute()),
                1  # 插入到位置1
            )
            print(f"    + {slide_info['type']}: {template_pptx.name}")

        # 保存
        presentation.SaveAs(str(output_file.absolute()))
        presentation.Close()

        print(f"    → {output_file.name}")
        return output_file

    def _get_template_path(self, slide_info: dict, subcatelog_dir_name: str) -> Path:
        """获取模板文件路径"""
        slide_type = slide_info["type"]
        page = slide_info["page"]

        if slide_type == "subcatelog":
            # subcatelog/4/catelog_single/page_1.pptx (from mapping)
            # actual: subcatelog/4/page_1.pptx
            # 先尝试 mapping 中的路径
            mapped_path = self.template_dir / subcatelog_dir_name / f"{page}.pptx"
            if mapped_path.exists():
                return mapped_path
            # 回退到 subcatelog/4/page_N.pptx
            parts = subcatelog_dir_name.split("/")
            if len(parts) >= 2:
                return self.template_dir / parts[0] / parts[1] / f"{page}.pptx"
            return mapped_path
        elif slide_type == "content":
            module_type = slide_info["module_type"]
            if module_type == "knowledge":
                template = self.template_dir / self.KNOWLEDGE_SINGLE_DIR / f"{page}.pptx"
                if template.exists():
                    return template
                return self.template_dir / self.KNOWLEDGE_SINGLE_DIR / "page_1.pptx"
            else:
                template = self.template_dir / self.TASK_SINGLE_DIR / f"{page}.pptx"
                if template.exists():
                    return template
                return self.template_dir / self.TASK_SINGLE_DIR / "page_1.pptx"

        return None

    def _get_task_num(self) -> str:
        return self.task_num


if __name__ == "__main__":
    import sys
    from pathlib import Path as PathLib

    PROJECT_ROOT = PathLib(__file__).parent.parent.parent.resolve()
    sys.path.insert(0, str(PROJECT_ROOT))

    TEMPLATE_DIR = PROJECT_ROOT / "final_ppt" / "content_process" / "template"
    TEMP_OUTPUT_DIR = PROJECT_ROOT / "final_ppt" / "temp"
    PADDING_BASE = PROJECT_ROOT / "word_process" / "llm_output" / "perception_json"

    processor = AssembleProcessor(TEMPLATE_DIR, TEMP_OUTPUT_DIR)

    print("=" * 60)
    print("Assemble: padding JSON → temp PPTX")
    print("=" * 60)

    project_dirs = sorted([d for d in PADDING_BASE.iterdir() if d.is_dir() and d.name.startswith('项目')])
    for project_dir in project_dirs:
        print(f"\n[Project] {project_dir.name}")
        knowledge_dir = project_dir / "knowledge"
        task_dir = project_dir / "task"
        if not knowledge_dir.exists() or not task_dir.exists():
            continue
        for k_file in sorted(knowledge_dir.glob("task*_knowledge.json")):
            task_num = k_file.stem.replace("_knowledge", "")
            t_file = task_dir / f"{task_num}_implementation.json"
            if not t_file.exists():
                print(f"  [SKIP] task{task_num}: no implementation file")
                continue
            print(f"  [Processing] {k_file.stem.replace('_knowledge','')}")
            processor.process(k_file, t_file)

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)