"""
Markdown → JSON 流水线

复刻 Ai_PPT/scripts/word_to_json.py 的两阶段架构：
- Stage 1: MarkdownChunkProcessor 生成原始 JSON（无字数限制）
- Stage 2: check_and_correct() 修正超长字段（最多2轮）

用法：
    python scripts/md_to_json.py [-p 项目名称]
"""
import json
import sys
import signal
import time
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from LLM.client import MiniMaxClient
from word_process.processor import MarkdownChunkProcessor
from word_process.checker import check_and_correct


def run_md_to_json(project_name: str = None):
    """运行 Markdown → JSON 流程"""
    print("=" * 70)
    print("Markdown → JSON")
    print("=" * 70)

    # 项目文件夹路径
    original_dir = PROJECT_ROOT / "word_process" / "original"

    # 选择项目文件夹
    project_folders = [d for d in original_dir.iterdir() if d.is_dir() and d.name.startswith('项目')]
    if not project_folders:
        print(f"[ERROR] 未找到项目文件夹: {original_dir}")
        return

    # 按名称筛选
    if project_name:
        matched = [d for d in project_folders if project_name in d.name]
        if not matched:
            print(f"[ERROR] 未找到包含 '{project_name}' 的项目")
            return
        project_folder = matched[0]
        print(f"[INFO] 选定项目: {project_folder.name}")
    elif len(project_folders) == 1:
        project_folder = project_folders[0]
        print(f"[INFO] 自动选择项目: {project_folder.name}")
    else:
        print("\n检测到多个项目，请选择：")
        for i, d in enumerate(sorted(project_folders), 1):
            print(f"  [{i}] {d.name}")
        idx = int(input("请输入序号: ").strip()) - 1
        project_folder = sorted(project_folders)[idx]

    print(f"\n[1/3] 调用 LLM 生成 JSON...")
    client = MiniMaxClient()
    processor = MarkdownChunkProcessor(client)
    output_files = processor.process(project_folder)
    print(f"      [OK] 生成 {len(output_files)} 个 JSON 文件")

    print(f"\n[2/3] Checker 检查与修正（最多2轮）...")
    checker_total_tokens = 0
    checker_total_time = 0.0
    for json_path in sorted(output_files):
        _, tokens, elapsed = check_and_correct(json_path, client, max_retries=1)
        checker_total_tokens += tokens
        checker_total_time += elapsed
    print(f"      [OK] Checker 完成，消耗 tokens: {checker_total_tokens}，耗时: {checker_total_time:.1f}s")

    print(f"\n[3/3] 输出文件:")
    for f in sorted(output_files):
        print(f"      {f.name}")

    print("\n" + "=" * 60)
    print("Markdown → JSON 完成！")
    print("=" * 60)


def _handle_interrupt(*args):
    print("\n\n已打断，程序退出")
    sys.exit(0)

signal.signal(signal.SIGINT, _handle_interrupt)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Markdown → JSON 流水线")
    parser.add_argument("-p", "--project", type=str, default=None, help="项目名称（支持模糊匹配）")
    args = parser.parse_args()
    run_md_to_json(project_name=args.project)