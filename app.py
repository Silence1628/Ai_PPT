"""
Edu_Agent 统一入口
编排 scripts/ 下的各步骤脚本，执行完整的 Word → PPT 工作流

用法：
    python app.py              # 全流程执行（Step 1 → 3 → 4）
    python app.py --step 1     # 仅执行 Step 1（Word → JSON，含 Checker）
    python app.py --step 3     # 仅执行 Step 3（JSON → PPT，半成品）
    python app.py --step 4     # 仅执行 Step 4（插入 subcatelog）
    python app.py --render-only # 仅 Step 1 + Step 3（跳过 subcatelog 插入）
"""
import sys
import signal
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))


def step1():
    """Step 1: Word → JSON（含 Checker 修正）"""
    from scripts.word_to_json import run_word_to_json
    run_word_to_json()


def step3():
    """Step 3: JSON → PPT 渲染"""
    from scripts.json_to_ppt import run_json_to_ppt
    run_json_to_ppt()


def step4():
    """Step 4: 插入 subcatelog"""
    from scripts.subcatelogs_insert import main as run_subcatelogs
    run_subcatelogs()


def _handle_interrupt(*args):
    print("\n\n已打断，程序退出")
    sys.exit(0)

signal.signal(signal.SIGINT, _handle_interrupt)


def main():
    args = sys.argv[1:]

    if "--step" in args:
        idx = args[args.index("--step") + 1]
        if idx == "1":
            step1()
        elif idx == "3":
            step3()
        elif idx == "4":
            step4()
        else:
            print(f"[ERROR] 不支持的 step: {idx}，可用值: 1, 3, 4")
            sys.exit(1)
        return

    if "--render-only" in args:
        print("=" * 70)
        print("Step 1: Word → JSON")
        print("=" * 70)
        step1()
        print("\n" + "=" * 70)
        print("Step 3: JSON → PPT")
        print("=" * 70)
        step3()
        return

    # 默认：全流程
    print("=" * 70)
    print("Edu_Agent 全流程")
    print("Step 1: Word → JSON（含 Checker 修正）")
    print("Step 3: JSON → PPT（半成品）")
    print("Step 4: 插入 subcatelog")
    print("=" * 70)

    step1()

    print("\n" + "=" * 70)
    print("Step 3: JSON → PPT")
    print("=" * 70)
    step3()

    print("\n" + "=" * 70)
    print("Step 4: 插入 subcatelog")
    print("=" * 70)
    step4()

    print("\n" + "=" * 70)
    print("全部完成！")
    print("=" * 70)


if __name__ == "__main__":
    main()