"""
catelog_process.processor - 将 subcatelog 模板插入到半成品 PPT

技术栈: win32com (WPS/MS Office COM)
"""
import json
import re
import tempfile
from pathlib import Path
from typing import Optional

import win32com.client


class CatelogProcessor:
    """
    将 subcatelog 模板插入到半成品 PPT 中。

    插入规则:
      - knowledge subcatelog: 插入到 "03 知识储备" 标记页之后
      - task subcatelog:     插入到 "04 任务实施" 标记页之后

    heading4_count 决定选择哪个模板:
      - count=4 → catelog_four.pptx（该模板已包含4页，整本插入）
    """

    FILENAME_TASK_PATTERN = re.compile(r"^(\d+)\.(\d+)_(.+)\.pptx$")
    PLACEHOLDER_PATTERN = re.compile(r"\{\{text[：:](\w+)\}\}")

    MARKER_KNOWLEDGE = "知识储备"
    MARKER_TASK      = "任务实施"

    def __init__(self, ppt_output_dir: str, knowledge_json_dir: str,
                 task_json_dir: str, template_dir: str):
        self.ppt_output_dir = Path(ppt_output_dir)
        self.knowledge_json_dir = Path(knowledge_json_dir)
        self.task_json_dir = Path(task_json_dir)
        self.template_dir = Path(template_dir)
        self.ppt_app = None

    def process_all(self):
        """扫描 ppt_output 目录，处理所有半成品 PPT（跳过已处理的文件）"""
        for ppt_file in sorted(self.ppt_output_dir.glob("*.pptx")):
            if ppt_file.name.startswith("~$") or "_with_cat" in ppt_file.name:
                continue
            print(f"[CATALOG] 处理: {ppt_file.name}")
            self.process_one(ppt_file)

    def process_one(self, ppt_file: Path) -> Optional[Path]:
        """
        处理单个 PPT 文件。

        1. 从文件名解析 task 编号 (1.1 → task1)
        2. 加载对应的 knowledge 和 implementation JSON
        3. 定位插入点
        4. 插入 subcatelog 模板（带占位符填充）
        5. 保存
        """
        task_num = self._parse_task_num(ppt_file.name)
        if not task_num:
            print(f"[WARN] 无法解析文件名: {ppt_file.name}")
            return None

        knowledge_json = self.knowledge_json_dir / f"task{task_num}_knowledge.json"
        task_json = self.task_json_dir / f"task{task_num}_implementation.json"

        if not knowledge_json.exists():
            print(f"[WARN] {knowledge_json} not found, skip")
            return None
        if not task_json.exists():
            print(f"[WARN] {task_json} not found, skip")
            return None

        with open(knowledge_json, "r", encoding="utf-8") as f:
            knowledge_data = json.load(f)
        with open(task_json, "r", encoding="utf-8") as f:
            task_data = json.load(f)

        return self._insert_subcatelogs(ppt_file, knowledge_data, task_data)

    def _insert_subcatelogs(self, ppt_file: Path,
                            knowledge_data: dict,
                            task_data: dict) -> Optional[Path]:
        """实际执行 subcatelog 插入（含占位符填充）"""
        self._start_ppt()
        try:
            presentation = self.ppt_app.Presentations.Open(
                str(ppt_file.absolute()), ReadOnly=0, Untitled=0, WithWindow=0
            )

            # 获取 marker 幻灯片上的文本（用于填充 cate_num 和 replace）
            knowledge_idx = self._find_marker_index(presentation, self.MARKER_KNOWLEDGE)
            task_idx = self._find_marker_index(presentation, self.MARKER_TASK)

            marker_texts = self._get_marker_texts(presentation, knowledge_idx, task_idx)

            print(f"      knowledge marker @ slide {knowledge_idx}, task marker @ slide {task_idx}")

            knowledge_count = knowledge_data.get("heading4_count", 0)
            task_count = task_data.get("heading4_count", 0)

            # 先插入 knowledge subcatelog
            if knowledge_idx > 0 and knowledge_count >= 2:
                knowledge_template = self._get_template_path(knowledge_count)
                if knowledge_template and knowledge_template.exists():
                    heading4_list = [seg["heading"] for seg in knowledge_data.get("segments", [])]
                    filled = self._fill_subcatelog_placeholders(
                        knowledge_template, heading4_list, "knowledge",
                        marker_texts["knowledge"]
                    )
                    self._insert_template_slides(presentation, filled, knowledge_idx)
                    Path(filled).unlink(missing_ok=True)

            # 再插入 task subcatelog
            if task_idx > 0 and task_count >= 2:
                task_template = self._get_template_path(task_count)
                if task_template and task_template.exists():
                    task_idx_new = self._find_marker_index(presentation, self.MARKER_TASK)
                    if task_idx_new > 0:
                        heading4_list = [seg["heading"] for seg in task_data.get("segments", [])]
                        filled = self._fill_subcatelog_placeholders(
                            task_template, heading4_list, "task",
                            marker_texts["task"]
                        )
                        self._insert_template_slides(presentation, filled, task_idx_new)
                        Path(filled).unlink(missing_ok=True)

            tmp = Path(tempfile.mktemp(suffix=".pptx"))
            presentation.SaveAs(str(tmp.absolute()))
            presentation.Close()
            if ppt_file.exists():
                ppt_file.unlink()
            import shutil
            shutil.copy2(str(tmp), str(ppt_file))
            tmp.unlink(missing_ok=True)
            return ppt_file
        finally:
            self._close_ppt()

    def _get_marker_texts(self, presentation, knowledge_idx: int, task_idx: int) -> dict:
        """
        从 marker 幻灯片中提取 cate_num 和 replace 的值。
        返回 {"knowledge": {"cate_num": "03", "replace": "知识储备"},
              "task": {"cate_num": "04", "replace": "任务实施"}}
        """
        texts = {"knowledge": {"cate_num": "03", "replace": "知识储备"},
                 "task": {"cate_num": "04", "replace": "任务实施"}}

        def read_shapes(idx):
            if idx < 0:
                return {}
            slide = presentation.Slides(idx)
            result = {}
            for j in range(1, slide.Shapes.Count + 1):
                shape = slide.Shapes(j)
                if shape.HasTextFrame:
                    txt = shape.TextFrame.TextRange.Text.strip()
                    if txt:
                        result[shape.Name] = txt
            return result

        # knowledge marker 读取
        k_shapes = read_shapes(knowledge_idx)
        for v in k_shapes.values():
            if v in ("03", "知识储备"):
                texts["knowledge"]["replace"] = "知识储备"
                texts["knowledge"]["cate_num"] = "03"
                break

        # task marker 读取
        t_shapes = read_shapes(task_idx)
        for v in t_shapes.values():
            if v in ("04", "任务实施"):
                texts["task"]["replace"] = "任务实施"
                texts["task"]["cate_num"] = "04"
                break

        return texts

    def _fill_subcatelog_placeholders(self, template_path: Path,
                                       heading4_list: list,
                                       module_type: str,
                                       marker_info: dict) -> Path:
        """
        在模板中填充占位符，返回填充后的临时文件路径。

        填充内容：
          - {{text:cate_num}} → marker_info["cate_num"]
          - {{text:replace}} → marker_info["replace"]
          - {{text:point_one}} ~ point_N → heading4_list[0] ~ heading4_list[N-1]
        """
        tmp_pptx = Path(tempfile.mktemp(suffix=".pptx"))

        self.ppt_app.DisplayAlerts = 0
        template_pres = self.ppt_app.Presentations.Open(
            str(template_path.absolute()), ReadOnly=0, Untitled=0, WithWindow=0
        )

        # 构建 point 映射
        point_map = self._build_point_mapping(heading4_list)

        # 收集所有占位符 → 值 的映射
        cate_num = marker_info.get("cate_num", "03" if module_type == "knowledge" else "04")
        replace = marker_info.get("replace", "知识储备" if module_type == "knowledge" else "任务实施")

        for slide_idx in range(1, template_pres.Slides.Count + 1):
            slide = template_pres.Slides(slide_idx)
            for shape_idx in range(1, slide.Shapes.Count + 1):
                shape = slide.Shapes(shape_idx)
                if not shape.HasTextFrame:
                    continue
                tf = shape.TextFrame
                if not tf.TextRange:
                    continue
                text = tf.TextRange.Text
                if not text:
                    continue

                def replace_field(match):
                    field = match.group(1)
                    if field == "cate_num":
                        return cate_num
                    if field == "replace":
                        return replace
                    if field.startswith("point_"):
                        return point_map.get(field, "")
                    return match.group(0)

                new_text = re.sub(self.PLACEHOLDER_PATTERN, replace_field, text)
                if new_text != text:
                    tf.TextRange.Text = new_text

        template_pres.SaveAs(str(tmp_pptx.absolute()))
        template_pres.Close()
        return tmp_pptx

    def _build_point_mapping(self, heading4_list: list) -> dict:
        """
        将 heading4_list 映射为 {point_one: heading1, point_two: heading2, ...}
        """
        point_map = {}
        for i, heading in enumerate(heading4_list, start=1):
            point_map[f"point_{self._int_to_word(i)}"] = heading
        return point_map

    def _int_to_word(self, n: int) -> str:
        """1 → one, 2 → two, ..., 6 → six"""
        words = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}
        return words.get(n, str(n))

    def _insert_template_slides(self, presentation, template_path: Path, insert_after_idx: int):
        """
        将模板的所有幻灯片插入到 insert_after_idx 之后。

        使用 Slides.InsertFromFile 方法从模板文件插入。
        insert_after_idx 是 marker 幻灯片的索引（1-based），
        直接在其后插入，InsertFromFile 会把新幻灯片放在 marker 和后续幻灯片之间。
        """
        try:
            # 直接在 marker 幻灯片之后插入，不跳过任何页
            insert_pos = insert_after_idx
            presentation.Slides.InsertFromFile(
                str(template_path.absolute()), insert_pos
            )
        except Exception as e:
            print(f"      [ERROR] InsertFromFile failed: {e}")

    def _get_template_path(self, heading4_count: int) -> Optional[Path]:
        """根据 heading4_count 返回对应的 subcatelog 模板路径"""
        count = max(2, min(6, heading4_count))
        template_name = {
            2: "catelog_two.pptx",
            3: "catelog_three.pptx",
            4: "catelog_four.pptx",
            5: "catelog_five.pptx",
            6: "catelog_six.pptx",
        }.get(count)
        if not template_name:
            return None
        return self.template_dir / str(count) / template_name

    def _find_marker_index(self, presentation, marker_name: str) -> int:
        """
        在 presentation 中查找包含 marker_name 文本的幻灯片索引（1-based）。
        先尝试 slide.Name 精确匹配，未找到则遍历所有 shape 的文本内容搜索。
        返回 -1 表示未找到。
        """
        # 先尝试 slide.Name 精确匹配
        for i in range(1, presentation.Slides.Count + 1):
            slide = presentation.Slides(i)
            if slide.Name == marker_name:
                return i

        # 再搜索 shape 文本内容
        for i in range(1, presentation.Slides.Count + 1):
            slide = presentation.Slides(i)
            for j in range(1, slide.Shapes.Count + 1):
                shape = slide.Shapes(j)
                if shape.HasTextFrame:
                    text = shape.TextFrame.TextRange.Text
                    if marker_name in text:
                        return i
        return -1

    def _parse_task_num(self, filename: str) -> Optional[str]:
        """
        从文件名解析 task 编号。
        '1.1_大模型基石——Transformer.pptx' → '1'
        """
        m = self.FILENAME_TASK_PATTERN.match(filename)
        if m:
            return m.group(2)
        return None

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

    def _close_ppt(self):
        if self.ppt_app:
            self.ppt_app.Quit()
            self.ppt_app = None