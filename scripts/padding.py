"""
Padding 生成脚本
将 original_content 转换为 padding_content JSON

用法：
    python scripts/padding.py
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from PPT_Perception.content_process import PaddingProcessor

KNOWLEDGE_SCHEMA = PROJECT_ROOT / "PPT_Perception" / "data" / "knowledge" / "input_schema" / "knowledge_capacity.json"
TASK_SCHEMA = PROJECT_ROOT / "PPT_Perception" / "data" / "task" / "input_schema" / "task_capacity.json"

KNOWLEDGE_ORIGINAL_DIR = PROJECT_ROOT / "PPT_Perception" / "data" / "knowledge" / "original_content"
TASK_ORIGINAL_DIR = PROJECT_ROOT / "PPT_Perception" / "data" / "task" / "original_content"

KNOWLEDGE_OUTPUT_DIR = PROJECT_ROOT / "PPT_Perception" / "data" / "knowledge" / "padding_content"
TASK_OUTPUT_DIR = PROJECT_ROOT / "PPT_Perception" / "data" / "task" / "padding_content"


def main():
    print("=" * 60)
    print("Padding Content 生成")
    print("=" * 60)

    print("\n[Knowledge]")
    knowledge_processor = PaddingProcessor(
        schema_path=KNOWLEDGE_SCHEMA,
        original_dir=KNOWLEDGE_ORIGINAL_DIR,
        output_dir=KNOWLEDGE_OUTPUT_DIR,
    )
    knowledge_processor.process_all()

    print("\n[Task]")
    task_processor = PaddingProcessor(
        schema_path=TASK_SCHEMA,
        original_dir=TASK_ORIGINAL_DIR,
        output_dir=TASK_OUTPUT_DIR,
    )
    task_processor.process_all()

    print("\n" + "=" * 60)
    print("完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
