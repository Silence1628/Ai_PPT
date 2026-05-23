"""
JSON → PPT 测试脚本
读取 base_json/*.json，渲染生成 base_ppt/output/*.pptx

用法：
    python scripts/test_json_to_ppt.py
"""
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from base_ppt.renderer.renderer import PPTRenderer

BASE_JSON_DIR = PROJECT_ROOT / "word_process" / "llm_output" / "base_json"
# Support project subdirectories: try */ if flat is empty
def _get_base_json_files():
    files = sorted(BASE_JSON_DIR.glob("*.json"))
    if not files:
        for proj in sorted(BASE_JSON_DIR.glob("*/")):
            files.extend(sorted(proj.glob("*.json")))
    return files
PPT_TEMPLATE = PROJECT_ROOT / "base_ppt" / "templates" / "template.pptx"
PPT_SCHEMA = PROJECT_ROOT / "base_ppt" / "templates" / "template_schema.json"
PPT_OUTPUT_DIR = PROJECT_ROOT / "base_ppt" / "base_output"


def run_test():
    print("=" * 70)
    print("JSON → PPT (Base PPT 测试)")
    print("=" * 70)

    task_jsons = _get_base_json_files()
    if not task_jsons:
        print(f"[ERROR] 未找到 JSON 文件: {BASE_JSON_DIR}")
        return

    PPT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"找到 {len(task_jsons)} 个 JSON 文件，开始渲染...\n")

    MAX_RETRIES = 3
    RETRY_DELAY = 5

    for i, json_path in enumerate(task_jsons, 1):
        print(f"[{i}/{len(task_jsons)}] 正在渲染: {json_path.name}")

        for attempt in range(MAX_RETRIES):
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
                if attempt < MAX_RETRIES - 1:
                    print(f"      [WARN] 渲染失败 ({attempt+1}/{MAX_RETRIES}): {e}")
                    print(f"      [INFO] {RETRY_DELAY}秒后重试...")
                    time.sleep(RETRY_DELAY)
                else:
                    print(f"      [ERROR] 渲染失败，已重试 {MAX_RETRIES} 次: {e}\n")

    print("=" * 70)
    print(f"完成！")
    print(f"输出目录: {PPT_OUTPUT_DIR}")
    print("=" * 70)


if __name__ == "__main__":
    run_test()