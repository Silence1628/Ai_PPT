"""
Fill 生成脚本
生成 mapping JSON → 组装 temp PPTX → 填充占位符

用法：
    python scripts/fill.py
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from PPT_Perception.content_process import MappingProcessor, AssembleProcessor, FillProcessor

KNOWLEDGE_PADDING_DIR = PROJECT_ROOT / "PPT_Perception" / "data" / "knowledge" / "padding_content"
TASK_PADDING_DIR = PROJECT_ROOT / "PPT_Perception" / "data" / "task" / "padding_content"

MAPPING_OUTPUT_DIR = PROJECT_ROOT / "PPT_Perception" / "mapping"
TEMPLATE_DIR = PROJECT_ROOT / "PPT_Perception" / "content_process" / "template"
TEMP_OUTPUT_DIR = PROJECT_ROOT / "PPT_Perception" / "temp"


def main():
    print("=" * 60)
    print("Fill Content: mapping JSON → temp PPTX")
    print("=" * 60)

    if not KNOWLEDGE_PADDING_DIR.exists():
        print(f"[ERROR] KNOWLEDGE_PADDING_DIR not found: {KNOWLEDGE_PADDING_DIR}")
        return

    # Step 1: Generate mapping JSON
    print("\n[Step 1] Generate mapping JSON")
    print("-" * 40)

    mapping_processor = MappingProcessor(
        ppt_file=None,
        padding_content_dir=KNOWLEDGE_PADDING_DIR,
        template_pptx=None,
        output_dir=MAPPING_OUTPUT_DIR,
        module_type="mapping"
    )

    for knowledge_json in sorted(KNOWLEDGE_PADDING_DIR.glob("task*_knowledge.json")):
        print(f"\n[Mapping] {knowledge_json.name}")

        task_num = knowledge_json.stem.replace("task", "").replace("_knowledge", "")
        task_json = TASK_PADDING_DIR / f"task{task_num}_implementation.json"

        if not task_json.exists():
            print(f"  [WARN] {task_json} not found, skipping")
            continue

        import json
        with open(knowledge_json, "r", encoding="utf-8") as f:
            knowledge_data = json.load(f)
        with open(task_json, "r", encoding="utf-8") as f:
            task_data = json.load(f)

        mapping_processor.process_from_data(knowledge_data, task_data)

    # Step 2: Build temp PPTX from mapping (all tasks)
    print("\n[Step 2] Build temp PPTX from mapping (all tasks)")
    print("-" * 40)

    assemble_processor = AssembleProcessor(TEMPLATE_DIR, TEMP_OUTPUT_DIR)

    for mapping_json in sorted(MAPPING_OUTPUT_DIR.glob("task*_mapping.json")):
        print(f"\n[Assemble] {mapping_json.name}")
        assemble_processor.process_from_mapping(mapping_json)

    # Step 3: Fill placeholders in temp PPTX
    print("\n[Step 3] Fill placeholders in temp PPTX")
    print("-" * 40)

    fill_processor = FillProcessor(TEMP_OUTPUT_DIR, MAPPING_OUTPUT_DIR)
    fill_processor.process_all()

    print("\n" + "=" * 60)
    print("完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()