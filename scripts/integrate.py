"""
integrate - 将 temp PPT 整合到 base PPT

映射关系：
- task1_knowledge.pptx → 1.1 的知识储备占位符
- task1_task.pptx → 1.1 的任务实施占位符
- 依此类推：task2 → 1.2, task3 → 1.3

占位符页标记：{{定位页}}（在模板中手动添加）

用法：
    python scripts/integrate.py
"""
import sys
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

import win32com.client
import pythoncom


class IntegrateProcessor:
    """将 temp PPT 整合到 base PPT"""

    def __init__(self, base_ppt_dir: Path, temp_dir: Path, output_dir: Path):
        self.base_ppt_dir = Path(base_ppt_dir)
        self.temp_dir = Path(temp_dir)
        self.output_dir = Path(output_dir)

    def process_all(self):
        """遍历所有 base PPT，整合 temp 内容"""
        # 清理 output_dir
        if self.output_dir.exists():
            for f in self.output_dir.glob("*.pptx"):
                try:
                    f.unlink()
                except Exception:
                    pass
        self.output_dir.mkdir(parents=True, exist_ok=True)

        pythoncom.CoInitialize()
        try:
            ppt_app = win32com.client.Dispatch("WPP.Application")
        except Exception:
            ppt_app = win32com.client.Dispatch("PowerPoint.Application")

        try:
            ppt_app.Visible = -1
            ppt_app.DisplayAlerts = 0

            for base_ppt in sorted(self.base_ppt_dir.glob("*.pptx")):
                print(f"\n[INTEGRATE] {base_ppt.name}")
                self._process_one(base_ppt, ppt_app)

            ppt_app.Quit()
        finally:
            pythoncom.CoUninitialize()

    def _process_one(self, base_ppt: Path, ppt_app):
        """处理单个 base PPT"""
        # 从文件名提取 task_num: 1.1 → 1, 1.2 → 2, 1.3 → 3
        parts = base_ppt.stem.split("_")[0].split(".")
        task_num = parts[1] if len(parts) > 1 else parts[0]

        # 对应的 temp 文件
        knowledge_pptx = self.temp_dir / "knowledge" / f"task{task_num}_knowledge.pptx"
        task_pptx = self.temp_dir / "task" / f"task{task_num}_implementation.pptx"

        if not knowledge_pptx.exists():
            print(f"  [WARN] knowledge not found: {knowledge_pptx}")
        if not task_pptx.exists():
            print(f"  [WARN] task not found: {task_pptx}")

        # 输出文件
        output_file = self.output_dir / base_ppt.name
        if output_file.exists():
            try:
                output_file.unlink()
            except Exception:
                pass

        # 用 shutil.copy 创建副本
        shutil.copy(base_ppt.absolute(), output_file.absolute())

        # 打开副本进行操作
        presentation = ppt_app.Presentations.Open(
            str(output_file.absolute()), ReadOnly=0, Untitled=0, WithWindow=0
        )

        # 找到所有包含 {{定位页}} 的占位符页
        placeholder_slides = []
        for i in range(1, presentation.Slides.Count + 1):
            slide = presentation.Slides(i)
            text = self._get_slide_text(slide)
            if "{{定位页}}" in text:
                placeholder_slides.append((i, text))
                print(f"  [FIND] placeholder at slide {i}: {text[:50]}...")

        if len(placeholder_slides) < 2:
            print(f"  [WARN] expected 2 placeholders, found {len(placeholder_slides)}, skipping")
            presentation.Close()
            return

        # 占位符顺序：第一个是 knowledge（知识储备），第二个是 task（任务实施）
        knowledge_placeholder_idx = placeholder_slides[0][0]  # 10
        task_placeholder_idx = placeholder_slides[1][0]       # 12

        # 1. 先插 task 内容（在 task 占位符位置之后插入）
        #    InsertFromFile 在索引后插入，所以 slide 12 位置不变
        if task_pptx.exists():
            task_slide_count = self._count_slides(task_pptx)
            presentation.Slides.InsertFromFile(
                str(task_pptx.absolute()),
                task_placeholder_idx
            )
            print(f"  [INSERT] task content after slide {task_placeholder_idx}, {task_slide_count} slides")

        # 2. 删除 task 占位符（位置不变，仍在 task_placeholder_idx）
        presentation.Slides(task_placeholder_idx).Delete()
        print(f"  [DELETE] task placeholder at slide {task_placeholder_idx}")

        # 3. 再插 knowledge 内容（在 knowledge 占位符位置之后插入）
        #    slide 10 位置不变
        if knowledge_pptx.exists():
            knowledge_slide_count = self._count_slides(knowledge_pptx)
            presentation.Slides.InsertFromFile(
                str(knowledge_pptx.absolute()),
                knowledge_placeholder_idx
            )
            print(f"  [INSERT] knowledge content after slide {knowledge_placeholder_idx}, {knowledge_slide_count} slides")

        # 4. 删除 knowledge 占位符（位置不变，仍在 knowledge_placeholder_idx）
        presentation.Slides(knowledge_placeholder_idx).Delete()
        print(f"  [DELETE] knowledge placeholder at slide {knowledge_placeholder_idx}")

        # 保存并关闭
        presentation.Save()
        presentation.Close()
        print(f"  → {output_file.name}")

    def _get_slide_text(self, slide) -> str:
        """获取幻灯片所有文本内容"""
        text_parts = []
        for i in range(1, slide.Shapes.Count + 1):
            shape = slide.Shapes.Item(i)
            if shape.HasTextFrame:
                text_parts.append(shape.TextFrame.TextRange.Text)
        return "\n".join(text_parts)

    def _count_slides(self, pptx_path: Path) -> int:
        """统计 PPTX 的幻灯片数量"""
        if not pptx_path.exists():
            return 0
        try:
            temp_app = win32com.client.Dispatch("PowerPoint.Application")
            temp_app.Visible = -1
            temp_pres = temp_app.Presentations.Open(
                str(pptx_path.absolute()), ReadOnly=1, Untitled=0, WithWindow=0
            )
            count = temp_pres.Slides.Count
            temp_pres.Close()
            temp_app.Quit()
            return count
        except Exception:
            return 0


def main():
    print("=" * 60)
    print("Integrate: temp PPT → base PPT")
    print("=" * 60)

    PROJECT_ROOT = Path(__file__).parent.parent.resolve()

    BASE_PPT_DIR = PROJECT_ROOT / "base_ppt" / "base_output"
    TEMP_DIR = PROJECT_ROOT / "final_ppt" / "temp"
    OUTPUT_DIR = PROJECT_ROOT / "output"

    processor = IntegrateProcessor(BASE_PPT_DIR, TEMP_DIR, OUTPUT_DIR)
    processor.process_all()

    print("\n" + "=" * 60)
    print("完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()