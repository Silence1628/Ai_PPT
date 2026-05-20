"""
Split multi-page content templates into single-page templates

正确方式：复制完整模板，然后删除不需要的页面，保留背景

用法：
    python scripts/split_templates.py
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

import win32com.client
import pythoncom
import tempfile
import shutil


def split_template(input_pptx: Path, output_dir: Path, prefix: str):
    """将多页PPT拆分为单页PPT（保留背景）"""
    output_dir.mkdir(parents=True, exist_ok=True)

    pythoncom.CoInitialize()
    try:
        ppt_app = win32com.client.Dispatch("PowerPoint.Application")
        ppt_app.Visible = 1
        ppt_app.DisplayAlerts = 0

        presentation = ppt_app.Presentations.Open(
            str(input_pptx.absolute()), ReadOnly=0, Untitled=0, WithWindow=0
        )

        print(f"  Splitting {input_pptx.name} ({presentation.Slides.Count} pages)...")

        total_slides = presentation.Slides.Count

        for slide_idx in range(1, total_slides + 1):
            tmp = Path(tempfile.mktemp(suffix=".pptx"))
            presentation.SaveCopyAs(str(tmp.absolute()))

            copy_pres = ppt_app.Presentations.Open(
                str(tmp.absolute()), ReadOnly=0, Untitled=0, WithWindow=0
            )

            slides_to_delete = []
            for i in range(1, copy_pres.Slides.Count + 1):
                if i != slide_idx:
                    slides_to_delete.append(i)

            for idx in sorted(slides_to_delete, reverse=True):
                copy_pres.Slides(idx).Delete()

            output_file = output_dir / f"{prefix}_{slide_idx}.pptx"
            if output_file.exists():
                output_file.unlink()

            copy_pres.SaveAs(str(output_file.absolute()))
            copy_pres.Close()
            tmp.unlink(missing_ok=True)

            print(f"    → {output_file.name}")

        presentation.Close()
        ppt_app.Quit()

    finally:
        pythoncom.CoUninitialize()


def main():
    print("=" * 60)
    print("Split Content Templates")
    print("=" * 60)

    # Knowledge template: 10 pages
    knowledge_template = PROJECT_ROOT / "PPT_Perception" / "content_process" / "template" / "knowledge" / "knowledge_content.pptx"
    knowledge_output = PROJECT_ROOT / "PPT_Perception" / "content_process" / "template" / "knowledge" / "knowledge_single"
    if knowledge_template.exists():
        print("\n[Knowledge Template]")
        split_template(knowledge_template, knowledge_output, "page")
    else:
        print(f"[WARN] {knowledge_template} not found")

    # Task template: 2 pages
    task_template = PROJECT_ROOT / "PPT_Perception" / "content_process" / "template" / "task" / "implementation_content.pptx"
    task_output = PROJECT_ROOT / "PPT_Perception" / "content_process" / "template" / "task" / "implementation_single"
    if task_template.exists():
        print("\n[Task Template]")
        split_template(task_template, task_output, "page")
    else:
        print(f"[WARN] {task_template} not found")

    # Subcatelog templates
    subcatelog_dir = PROJECT_ROOT / "PPT_Perception" / "content_process" / "template" / "subcatelog"
    subcatelog_names = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}

    print("\n[Subcatelog Templates]")
    for count in [2, 3, 4, 5, 6]:
        template_file = subcatelog_dir / str(count) / f"catelog_{subcatelog_names[count]}.pptx"
        if template_file.exists():
            output_dir = subcatelog_dir / str(count) / "catelog_single"
            print(f"\n  Splitting {template_file.name}...")
            split_template(template_file, output_dir, "page")
        else:
            print(f"  [WARN] {template_file} not found")

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()