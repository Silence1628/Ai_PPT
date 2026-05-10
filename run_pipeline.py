"""
Edu_Agent 工程入口脚本
串联 Word_Chunks 和 PPT_Framework，完成 Word → JSON → PPT 完整流程

用法：
    python run_pipeline.py                  # 完整流程（Word→JSON→PPT）
    python run_pipeline.py --render-only    # 仅渲染（JSON已有，跳过Word处理）
    按 Ctrl+C 可随时打断（会保存已有进度）
"""
import argparse
import json
import sys
import signal
from pathlib import Path

# 确保项目根目录在 sys.path 中（可导入 LLM, Word_Chunks, PPT_Framework）
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from LLM.client import MiniMaxClient
from Word_Chunks.chunker import WordChunker
from Word_Chunks.processor import WordChunkProcessor
from Word_Chunks.checker import check_and_correct
from PPT_Framework.renderer import PPTRenderer


# =============================================================================
# 路径配置
# =============================================================================
WORD_OUTPUT_DIR = PROJECT_ROOT / "Word_Chunks" / "json_output"
PPT_TEMPLATE = PROJECT_ROOT / "PPT_Framework" / "templates" / "template.pptx"
PPT_SCHEMA = PROJECT_ROOT / "PPT_Framework" / "templates" / "template_schema.json"
PPT_OUTPUT_DIR = PROJECT_ROOT / "PPT_Framework" / "ppt_output"


def find_word_document(example_dir: Path) -> Path:
    """自动识别 example 目录中的 Word 文档"""
    docx_files = list(example_dir.glob("*.docx")) + list(example_dir.glob("*.doc"))
    if not docx_files:
        raise FileNotFoundError(
            f"未找到 Word 文件，请将 .docx 或 .doc 文件放入 {example_dir}"
        )
    if len(docx_files) > 1:
        raise ValueError(
            f"找到多个 Word 文件，请只保留一个: {[f.name for f in docx_files]}"
        )
    return docx_files[0]


# =============================================================================
# Step 1: Word → JSON
# =============================================================================
def run_word_to_json():
    """运行 Word_Chunks 流程：切割 Word → 调用 LLM → 生成 JSON"""
    print("=" * 70)
    print("Step 1: Word → JSON")
    print("=" * 70)

    # 自动识别 Word 文件
    word_example_dir = PROJECT_ROOT / "Word_Chunks" / "example"
    WORD_DOC_PATH = find_word_document(word_example_dir)
    print(f"[INFO] 自动识别到 Word 文件: {WORD_DOC_PATH.name}")

    # 1.1 切割
    print(f"[1/4] 切割 Word 文档: {WORD_DOC_PATH.name}")
    chunker = WordChunker(str(WORD_DOC_PATH))
    chunks = chunker.chunk()
    # chunk1=素材, chunk2~4=任务，取 task 数
    task_count = len(chunks) - 1
    print(f"      识别到项目指导书: {WORD_DOC_PATH.name}")
    print(f"      分离出 {task_count} 个任务")

    # 1.2 调用 LLM 生成 JSON
    print(f"\n[2/4] 调用 LLM 生成 JSON（并行处理 {task_count} 个任务）...")
    client = MiniMaxClient()
    processor = WordChunkProcessor(client, output_dir=str(WORD_OUTPUT_DIR))
    output_files = processor.process(chunks, max_workers=3)
    print(f"      [OK] 生成 {len(output_files)} 个 JSON 文件")

    # 1.3 Checker 阶段：检查并修正字数
    print(f"\n[3/4] Checker 检查与修正（精确字段替换）...")
    for json_path in sorted(WORD_OUTPUT_DIR.glob("task*.json")):
        check_and_correct(json_path, client, max_retries=1)
    print("      [OK] Checker 检查完成")

    # 1.4 列出输出
    print(f"\n[4/4] 输出文件:")
    for f in sorted(WORD_OUTPUT_DIR.glob("task*.json")):
        print(f"      {f.name}")

    return output_files


# =============================================================================
# Step 2: JSON → PPT
# =============================================================================
def run_json_to_ppt():
    """运行 PPT_Framework 流程：读取 JSON → 渲染 PPT"""
    print("\n" + "=" * 70)
    print("Step 2: JSON → PPT")
    print("=" * 70)

    # 查找 JSON 文件
    task_jsons = sorted(WORD_OUTPUT_DIR.glob("task*.json"))
    if not task_jsons:
        print(f"错误：未找到 JSON 文件，请先运行 --word-to-json")
        sys.exit(1)

    # 确保输出目录存在
    PPT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Clean up stale PPT files so each run only has task count files
    for f in PPT_OUTPUT_DIR.glob("*.pptx"):
        f.unlink()

    print(f"找到 {len(task_jsons)} 个 task JSON，开始渲染...\n")

    # 依次渲染（顺序执行，不并发 — COM 单线程 apartment）
    for i, json_path in enumerate(task_jsons, 1):
        print(f"[{i}/{len(task_jsons)}] 正在渲染: {json_path.name}")

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        renderer = PPTRenderer(
            template_path=str(PPT_TEMPLATE),
            schema_path=str(PPT_SCHEMA)
        )

        output_path = PPT_OUTPUT_DIR / f"{json_path.stem}.pptx"
        renderer.render(data, str(output_path))
        print(f"      [OK] 完成: {output_path.name}\n")

    print(f"=" * 70)
    print(f"完成！共输出 {len(task_jsons)} 个 PPT")
    print(f"输出目录: {PPT_OUTPUT_DIR}")
    print("=" * 70)


# =============================================================================
# Ctrl+C 中断支持：直接清空退出
# =============================================================================
def _handle_interrupt(*args):
    print("\n\n已打断，程序退出")
    sys.exit(0)

signal.signal(signal.SIGINT, _handle_interrupt)


# =============================================================================
# Main
# =============================================================================
def main():
    parser = argparse.ArgumentParser(description="Edu_Agent: Word → JSON → PPT")
    parser.add_argument(
        "--render-only",
        action="store_true",
        help="跳过 Word→JSON，仅执行 JSON→PPT 渲染"
    )
    args = parser.parse_args()

    if args.render_only:
        run_json_to_ppt()
    else:
        run_word_to_json()
        run_json_to_ppt()
        print("\n" + "=" * 60)
        print("全部完成！")
        print("=" * 60)


if __name__ == "__main__":
    main()
