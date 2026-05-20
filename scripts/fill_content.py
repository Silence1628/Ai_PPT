"""
Fill Content 生成脚本
生成 mapping JSON 作为渲染蓝图

用法：
    python scripts/fill_content.py
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from PPT_Perception.content_process import MappingProcessor

KNOWLEDGE_PADDING_DIR = PROJECT_ROOT / "PPT_Perception" / "data" / "knowledge" / "padding_content"
TASK_PADDING_DIR = PROJECT_ROOT / "PPT_Perception" / "data" / "task" / "padding_content"

MAPPING_OUTPUT_DIR = PROJECT_ROOT / "PPT_Perception" / "mapping"


def main():
    print("=" * 60)
    print("Mapping JSON 生成")
    print("=" * 60)

    if not KNOWLEDGE_PADDING_DIR.exists():
        print(f"[ERROR] KNOWLEDGE_PADDING_DIR not found: {KNOWLEDGE_PADDING_DIR}")
        return

    # 遍历 knowledge padding JSON 文件
    for knowledge_json in sorted(KNOWLEDGE_PADDING_DIR.glob("task*_knowledge.json")):
        print(f"\n[Mapping] {knowledge_json.name}")

        # 解析 task_num
        task_num = knowledge_json.stem.replace("task", "").replace("_knowledge", "")
        task_json = TASK_PADDING_DIR / f"task{task_num}_implementation.json"

        if not task_json.exists():
            print(f"  [WARN] {task_json} not found, skipping")
            continue

        # 读取 knowledge 数据
        import json
        with open(knowledge_json, "r", encoding="utf-8") as f:
            knowledge_data = json.load(f)

        # 读取 task 数据
        with open(task_json, "r", encoding="utf-8") as f:
            task_data = json.load(f)

        # 创建 processor
        processor = MappingProcessor(
            ppt_file=None,
            padding_content_dir=KNOWLEDGE_PADDING_DIR,
            template_pptx=None,
            output_dir=MAPPING_OUTPUT_DIR,
            module_type="mapping"
        )

        # 生成 mapping
        processor.process_from_data(knowledge_data, task_data)

    print("\n" + "=" * 60)
    print("完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()