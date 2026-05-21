"""
assemble - 根据 mapping JSON 组装 temp PPTX

使用 InsertFromFile 从单页模板组装，供后续渲染：
- knowledge: 10 页模板循环
- task: 2 页模板循环
- subcatelog: heading4_count 页
"""
import json
import shutil
from pathlib import Path

import win32com.client
import pythoncom


class AssembleProcessor:
    """根据 mapping JSON 组装 temp PPTX"""

    KNOWLEDGE_SINGLE_DIR = "knowledge/knowledge_single"
    TASK_SINGLE_DIR = "task/implementation_single"
    SUBCATELOG_SINGLE_DIR = "subcatelog"

    def __init__(self, template_dir: Path, temp_output_dir: Path):
        self.template_dir = Path(template_dir)
        self.temp_output_dir = Path(temp_output_dir)
        self.task_num = ""

    def process_from_mapping(self, mapping_json: Path) -> dict:
        """
        读取 mapping JSON，组装 knowledge 和 task 的 temp PPTX。

        Returns:
            dict: {"knowledge": Path, "task": Path} 输出文件路径
        """
        with open(mapping_json, "r", encoding="utf-8") as f:
            mapping_data = json.load(f)

        self.task_num = mapping_data.get("task_num", "")
        heading4_count = mapping_data.get("heading4_count", 0)

        print(f"  [ContentProcessor] task={self.task_num}, heading4_count={heading4_count}")

        pythoncom.CoInitialize()
        try:
            ppt_app = win32com.client.Dispatch("WPP.Application")
        except Exception:
            ppt_app = win32com.client.Dispatch("PowerPoint.Application")
        try:
            try:
                ppt_app.Visible = -1  # msoTrue = -1
            except Exception:
                pass  # 已有 PowerPoint 实例可能无法设置 Visible
            try:
                ppt_app.DisplayAlerts = 0  # ppAlertsNone = 2
            except Exception:
                pass

            knowledge_dir = self.temp_output_dir / "knowledge"
            task_dir = self.temp_output_dir / "task"

            knowledge_output = self._build_temp_pptx(
                ppt_app,
                mapping_data.get("knowledge", {}),
                heading4_count,
                knowledge_dir,
                "knowledge"
            )
            task_output = self._build_temp_pptx(
                ppt_app,
                mapping_data.get("task", {}),
                heading4_count,
                task_dir,
                "task"
            )

            ppt_app.Quit()
            return {"knowledge": knowledge_output, "task": task_output}
        finally:
            pythoncom.CoUninitialize()

    def _build_temp_pptx(
        self, ppt_app, section_data: dict, heading4_count: int,
        output_dir: Path, module_type: str
    ) -> Path:
        """组装单个 section (knowledge/task) 的 temp PPTX"""
        segments = section_data.get("segments", [])
        subcatelog_dir_name = section_data.get("subcatelog_dir", "")

        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"task{self._get_task_num()}_{module_type}.pptx"

        # 清理可能存在的旧文件
        if output_file.exists():
            try:
                output_file.unlink()
            except PermissionError:
                pass

        # 用 subcatelog page_1 作为基础文件
        base_file = self.template_dir / self.SUBCATELOG_SINGLE_DIR / str(heading4_count) / "page_1.pptx"
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
                "heading4_count": heading4_count
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
                return self.template_dir / self.KNOWLEDGE_SINGLE_DIR / f"{page}.pptx"
            else:
                return self.template_dir / self.TASK_SINGLE_DIR / f"{page}.pptx"

        return None

    def _get_task_num(self) -> str:
        return self.task_num


if __name__ == "__main__":
    import sys
    from pathlib import Path as PathLib

    PROJECT_ROOT = PathLib(__file__).parent.parent.resolve()
    sys.path.insert(0, str(PROJECT_ROOT))

    TEMPLATE_DIR = PROJECT_ROOT / "PPT_Perception" / "content_process" / "template"
    TEMP_OUTPUT_DIR = PROJECT_ROOT / "PPT_Perception" / "temp"
    MAPPING_DIR = PROJECT_ROOT / "PPT_Perception" / "mapping"

    processor = ContentProcessor(TEMPLATE_DIR, TEMP_OUTPUT_DIR)

    print("=" * 60)
    print("Content Processing: mapping JSON → temp PPTX")
    print("=" * 60)

    for mapping_json in sorted(MAPPING_DIR.glob("task*_mapping.json")):
        print(f"\n[Processing] {mapping_json.name}")
        processor.process_from_mapping(mapping_json)

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)