"""
Edu_Agent 统一入口
仅执行 JSON → PPT 渲染

用法：
    python app.py
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))


def step3():
    """JSON → PPT 渲染"""
    from scripts.json_to_ppt import run_json_to_ppt
    run_json_to_ppt()


def main():
    print("=" * 70)
    print("JSON → PPT")
    print("=" * 70)
    step3()
    print("\n" + "=" * 70)
    print("完成")
    print("=" * 70)


if __name__ == "__main__":
    main()