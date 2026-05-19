"""
导出原始内容脚本
将 Word 文档切分后的 knowledge_reserve 和 task_implementation 原始内容导出为 JSON

用法：
    python scripts/original_export.py
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from Word_Chunks.chunker import WordChunker

WORD_INPUT_DIR = PROJECT_ROOT / "word_input"
KNOWLEDGE_ORIGINAL_DIR = PROJECT_ROOT / "PPT_Perception" / "data" / "knowledge" / "original_content"
TASK_ORIGINAL_DIR = PROJECT_ROOT / "PPT_Perception" / "data" / "task" / "original_content"


def main():
    docx_files = [f for f in WORD_INPUT_DIR.glob("*.docx") if not f.name.startswith('~$')]
    if not docx_files:
        print(f"[ERROR] 未找到 Word 文件: {WORD_INPUT_DIR}")
        return

    word_doc = docx_files[0].resolve()
    print(f"[INFO] 使用文档: {word_doc.name}")

    print("\n[1/2] 切分 Word 文档...")
    chunker = WordChunker()
    chunks = chunker.chunk(str(word_doc))
    task_count = len(chunks) - 1
    print(f"      识别到 {task_count} 个任务")

    print("\n[2/2] 导出原始内容...")
    KNOWLEDGE_ORIGINAL_DIR.mkdir(parents=True, exist_ok=True)
    chunker.export_original_content(chunks, str(KNOWLEDGE_ORIGINAL_DIR), section_filter="knowledge_reserve")
    print(f"      [OK] 知识储备 → {KNOWLEDGE_ORIGINAL_DIR}")
    for f in KNOWLEDGE_ORIGINAL_DIR.glob("task*_knowledge.json"):
        print(f"         {f.name}")

    TASK_ORIGINAL_DIR.mkdir(parents=True, exist_ok=True)
    chunker.export_original_content(chunks, str(TASK_ORIGINAL_DIR), section_filter="task_implementation")
    print(f"      [OK] 任务实施 → {TASK_ORIGINAL_DIR}")
    for f in TASK_ORIGINAL_DIR.glob("task*_implementation.json"):
        print(f"         {f.name}")

    print("\n" + "=" * 50)
    print("完成！")
    print("=" * 50)


if __name__ == "__main__":
    main()
