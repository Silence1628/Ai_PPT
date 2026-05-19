"""
JSON → PPT
读取 JSON 文件，渲染生成 PPT

用法：
    python scripts/json_to_ppt.py
按 Ctrl+C 可随时打断
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

from PPT_Framework.renderer import PPTRenderer

WORD_OUTPUT_DIR = PROJECT_ROOT / "Word_Chunks" / "json_output"
PPT_TEMPLATE = PROJECT_ROOT / "PPT_Framework" / "templates" / "template.pptx"
PPT_SCHEMA = PROJECT_ROOT / "PPT_Framework" / "templates" / "template_schema.json"
PPT_OUTPUT_DIR = PROJECT_ROOT / "ppt_output"


def run_json_to_ppt():
    """运行 JSON → PPT 流程"""
    print("\n" + "=" * 70)
    print("JSON → PPT")
    print("=" * 70)

    task_jsons = sorted(WORD_OUTPUT_DIR.glob("task*.json"))
    if not task_jsons:
        print(f"错误：未找到 JSON 文件，请先运行 word_to_json")
        sys.exit(1)

    PPT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"找到 {len(task_jsons)} 个 task JSON，开始渲染...\n")

    MAX_RENDER_RETRIES = 3
    RETRY_DELAY = 5

    for i, json_path in enumerate(task_jsons, 1):
        print(f"[{i}/{len(task_jsons)}] 正在渲染: {json_path.name}")

        for attempt in range(MAX_RENDER_RETRIES):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                renderer = PPTRenderer(
                    template_path=str(PPT_TEMPLATE),
                    schema_path=str(PPT_SCHEMA)
                )

                output_path = PPT_OUTPUT_DIR / f"{json_path.stem}.pptx"
                renderer.render(data, str(output_path))
                print(f"      [OK] 完成: {output_path.name}\n")
                break
            except Exception as e:
                if attempt < MAX_RENDER_RETRIES - 1:
                    print(f"      [WARN] 渲染失败 ({attempt+1}/{MAX_RENDER_RETRIES}): {e}")
                    print(f"      [INFO] {RETRY_DELAY}秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    print(f"      [ERROR] 渲染失败，已重试 {MAX_RENDER_RETRIES} 次: {e}")
                    break

    print(f"=" * 70)
    print(f"完成！共输出 {len(task_jsons)} 个 PPT")
    print(f"输出目录: {PPT_OUTPUT_DIR}")
    print("=" * 70)


def _handle_interrupt(*args):
    print("\n\n已打断，程序退出")
    sys.exit(0)

signal.signal(signal.SIGINT, _handle_interrupt)


def main():
    run_json_to_ppt()


if __name__ == "__main__":
    main()
