"""
Subcatelog 插入脚本
将 subcatelog 模板插入到 ppt_output 中的半成品 PPT

用法：
    python scripts/subcatelogs_insert.py
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from PPT_Perception.subcatelog_process import CatelogProcessor

PPT_OUTPUT_DIR = PROJECT_ROOT / "ppt_output"
KNOWLEDGE_JSON_DIR = PROJECT_ROOT / "PPT_Perception" / "data" / "knowledge" / "original_content"
TASK_JSON_DIR = PROJECT_ROOT / "PPT_Perception" / "data" / "task" / "original_content"
TEMPLATE_DIR = PROJECT_ROOT / "PPT_Perception" / "subcatelog_process" / "template"


def main():
    print("=" * 60)
    print("Subcatelog 插入")
    print("=" * 60)

    processor = CatelogProcessor(
        ppt_output_dir=str(PPT_OUTPUT_DIR),
        knowledge_json_dir=str(KNOWLEDGE_JSON_DIR),
        task_json_dir=str(TASK_JSON_DIR),
        template_dir=str(TEMPLATE_DIR),
    )

    processor.process_all()
    print("完成！")


if __name__ == "__main__":
    main()
