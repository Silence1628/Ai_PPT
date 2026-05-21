"""
mapping_processor - 生成 mapping JSON 作为渲染蓝图

读取 padding_content JSON，生成完整的 mapping 数据，包含：
- 每个 segment 的 subcatelog_page 和 content_pages
"""
import json
from pathlib import Path
from typing import Optional


class MappingProcessor:
    """生成 mapping JSON"""

    # 模板目录（相对于 template 根目录）
    KNOWLEDGE_SINGLE_DIR = "knowledge/knowledge_single"
    TASK_SINGLE_DIR = "task/implementation_single"
    SUBCATELOG_SINGLE_DIR = "subcatelog"

    # content 模板页循环
    KNOWLEDGE_PAGES = [f"page_{i}" for i in range(1, 11)]  # page_1~page_10
    TASK_PAGES = ["page_1", "page_2"]  # 固定2页

    def __init__(self, ppt_file: Path, padding_content_dir: Path,
                 template_pptx: Path, output_dir: Path, module_type: str):
        """
        Args:
            ppt_file: 原始 PPT 文件路径（不再使用）
            padding_content_dir: padding_content JSON 所在目录
            template_pptx: content 页模板 PPTX 路径（不再使用）
            output_dir: mapping JSON 的输出目录
            module_type: "knowledge" 或 "task"
        """
        self.ppt_file = Path(ppt_file) if ppt_file else None
        self.padding_content_dir = Path(padding_content_dir)
        self.template_pptx = Path(template_pptx) if template_pptx else None
        self.output_dir = Path(output_dir)
        self.module_type = module_type

    def process_from_data(self, knowledge_data: dict, task_data: dict) -> Optional[Path]:
        """
        根据 knowledge 和 task 数据生成 mapping JSON。
        """
        return self._generate_mapping(knowledge_data, task_data)

    def _generate_mapping(self, knowledge_data: dict, task_data: dict = None) -> Optional[Path]:
        """生成 mapping JSON"""
        task_num = knowledge_data.get("task_num", "")
        task_title = knowledge_data.get("task_title", "")
        knowledge_heading4_count = knowledge_data.get("heading4_count", 0)
        knowledge_segments = knowledge_data.get("segments", [])

        task_heading4_count = task_data.get("heading4_count", 0) if task_data else 0

        print(f"  [Mapping] task={task_num}, knowledge_h4={knowledge_heading4_count}, task_h4={task_heading4_count}")

        if knowledge_heading4_count < 2:
            print(f"  [WARN] knowledge_heading4_count={knowledge_heading4_count} < 2，跳过")
            return None

        # 获取 task segments
        task_segments = []
        if task_data:
            task_segments = task_data.get("segments", [])

        # 构建每个 segment 的 mapping
        knowledge_segments_mapping = self._build_segments_mapping(
            knowledge_segments, self.KNOWLEDGE_PAGES
        )
        task_segments_mapping = self._build_segments_mapping(
            task_segments, self.TASK_PAGES
        )

        mapping_data = {
            "task_num": task_num,
            "task_title": task_title,
            "heading4_count": knowledge_heading4_count,
            "knowledge": {
                "subcatelog_dir": f"{self.SUBCATELOG_SINGLE_DIR}/{knowledge_heading4_count}/catelog_single",
                "segments": knowledge_segments_mapping
            },
            "task": {
                "subcatelog_dir": f"{self.SUBCATELOG_SINGLE_DIR}/{task_heading4_count}/catelog_single",
                "segments": task_segments_mapping
            }
        }

        # 输出 mapping JSON
        self.output_dir.mkdir(parents=True, exist_ok=True)
        output_file = self.output_dir / f"task{task_num}_mapping.json"

        if output_file.exists():
            output_file.unlink()
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(mapping_data, f, ensure_ascii=False, indent=2)

        print(f"    → {output_file.name}")
        return output_file

    def _build_segments_mapping(self, segments: list, template_pages: list) -> list:
        """
        为每个 segment 构建 mapping：
        - subcatelog_page: page_{i} (i 从 1 到 heading4_count)
        - content_pages: 根据 heading_chunk_count 循环使用 template_pages
        """
        result = []
        for i, seg in enumerate(segments, start=1):
            chunk_count = seg.get("heading_chunk_count", 0)
            heading = seg.get("heading", "")

            # subcatelog page (从 1 开始编号)
            subcatelog_page = f"page_{i}"

            # content pages 循环
            content_pages = []
            for j in range(chunk_count):
                page_idx = j % len(template_pages)
                content_pages.append(template_pages[page_idx])

            result.append({
                "heading": heading,
                "heading_chunk_count": chunk_count,
                "content_chunks": seg.get("content_chunks", []),
                "subcatelog_page": subcatelog_page,
                "content_pages": content_pages
            })

        return result