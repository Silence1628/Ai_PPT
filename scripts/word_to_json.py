"""
Word → JSON
将 Word 文档切分为 chunks，调用 LLM 生成 JSON，Checker 检查修正

用法：
    python scripts/word_to_json.py
按 Ctrl+C 可随时打断（会保存已有进度）
"""
import json
import sys
import signal
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from LLM.client import MiniMaxClient
from Word_Chunks.chunker import WordChunker
from Word_Chunks.processor import WordChunkProcessor
from Word_Chunks.checker import check_and_correct

WORD_INPUT_DIR = PROJECT_ROOT / "input"
WORD_OUTPUT_DIR = PROJECT_ROOT / "Word_Chunks" / "json_output"
KNOWLEDGE_ORIGINAL_DIR = PROJECT_ROOT / "PPT_Perception" / "data" / "knowledge" / "original_content"
TASK_ORIGINAL_DIR = PROJECT_ROOT / "PPT_Perception" / "data" / "task" / "original_content"


def select_word_document(input_dir: Path) -> Path:
    """显示选择菜单，让用户选择要处理的 Word 文档"""
    docx_files = list(input_dir.glob("*.docx")) + list(input_dir.glob("*.doc"))
    if not docx_files:
        raise FileNotFoundError(
            f"未找到 Word 文件，请将 .docx 或 .doc 文件放入 {input_dir}"
        )
    if len(docx_files) == 1:
        return docx_files[0]

    print("\n" + "=" * 50)
    print("检测到多个 Word 文件，请选择要处理的文件：")
    print("=" * 50)
    for i, f in enumerate(docx_files, 1):
        print(f"  [{i}] {f.name}")
    print(f"  [0] 退出")
    print("=" * 50)

    while True:
        try:
            choice = input("请输入序号 (0-{}): ".format(len(docx_files)))
            idx = int(choice)
            if idx == 0:
                sys.exit(0)
            if 1 <= idx <= len(docx_files):
                return docx_files[idx - 1]
            print("无效选择，请重试")
        except ValueError:
            print("请输入数字")


def run_word_to_json():
    """运行 Word → JSON 流程"""
    print("=" * 70)
    print("Word → JSON")
    print("=" * 70)

    WORD_DOC_PATH = select_word_document(WORD_INPUT_DIR)
    print(f"[INFO] 自动识别到 Word 文件: {WORD_DOC_PATH.name}")

    print(f"[1/4] 切割 Word 文档: {WORD_DOC_PATH.name}")
    chunker = WordChunker()
    chunks = chunker.chunk(str(WORD_DOC_PATH))
    task_count = len(chunks) - 1
    print(f"      识别到项目指导书: {WORD_DOC_PATH.name}")
    print(f"      分离出 {task_count} 个任务")

    print(f"\n[1.5/4] 导出知识储备和任务实施原始内容...")
    chunker.export_original_content(chunks, str(KNOWLEDGE_ORIGINAL_DIR), section_filter="knowledge_reserve")
    print(f"      [OK] 知识储备已导出到: {KNOWLEDGE_ORIGINAL_DIR}")
    chunker.export_original_content(chunks, str(TASK_ORIGINAL_DIR), section_filter="task_implementation")
    print(f"      [OK] 任务实施已导出到: {TASK_ORIGINAL_DIR}")

    print(f"\n[2/4] 调用 LLM 生成 JSON（串行处理 {task_count} 个任务）...")
    client = MiniMaxClient()
    processor = WordChunkProcessor(client, output_dir=str(WORD_OUTPUT_DIR))
    output_files = processor.process(chunks)
    print(f"      [OK] 生成 {len(output_files)} 个 JSON 文件，共消耗 tokens: {processor.total_tokens}")

    print(f"\n[3/4] Checker 检查与修正（精确字段替换）...")
    checker_total_tokens = 0
    checker_total_time = 0.0
    for json_path in sorted(WORD_OUTPUT_DIR.glob("task*.json")):
        _, tokens, elapsed = check_and_correct(json_path, client, max_retries=1)
        checker_total_tokens += tokens
        checker_total_time += elapsed
    print(f"      [OK] Checker 检查完成，共消耗 tokens: {checker_total_tokens}，耗时: {checker_total_time:.1f}s")

    print(f"\n[4/4] 输出文件:")
    for f in sorted(WORD_OUTPUT_DIR.glob("task*.json")):
        print(f"      {f.name}")

    return output_files


def _handle_interrupt(*args):
    print("\n\n已打断，程序退出")
    sys.exit(0)

signal.signal(signal.SIGINT, _handle_interrupt)


def main():
    run_word_to_json()
    print("\n" + "=" * 60)
    print("Word → JSON 完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
