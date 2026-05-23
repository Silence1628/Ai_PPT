"""
Edu_Agent 统一入口

用法：
    python app.py
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))


def step1_word_to_json_and_export():
    """Word → JSON + original_content"""
    print("\n" + "=" * 70)
    print("[Step 1] Word → JSON + original_content")
    print("=" * 70)

    from scripts.word_to_json import run_word_to_json
    run_word_to_json()

    from scripts.original_export import main as original_export_main
    original_export_main()


def step2_llm_chunk():
    """LLM 语义切分: markdown_content + LLM_refactor → LLM_refactor"""
    print("\n" + "=" * 70)
    print("[Step 2] LLM 语义切分: markdown_content + LLM_refactor → LLM_refactor")
    print("=" * 70)

    from scripts.llm_chunk import main as llm_chunk_main
    llm_chunk_main()


def step3_render_and_mapping():
    """渲染基础 PPT + 生成 mapping"""
    print("\n" + "=" * 70)
    print("[Step 3] 渲染基础 PPT + 生成 mapping")
    print("=" * 70)

    # 渲染基础 PPT
    from scripts.json_to_ppt import run_json_to_ppt
    run_json_to_ppt()

    # 生成 mapping
    from final_ppt.content_process import MappingProcessor

    KNOWLEDGE_PADDING_DIR = PROJECT_ROOT / "word_process" / "llm_input"
    TASK_PADDING_DIR = PROJECT_ROOT / "word_process" / "llm_input"
    MAPPING_OUTPUT_DIR = PROJECT_ROOT / "final_ppt" / "mapping"

    mapping_processor = MappingProcessor(
        ppt_file=None,
        padding_content_dir=KNOWLEDGE_PADDING_DIR,
        template_pptx=None,
        output_dir=MAPPING_OUTPUT_DIR,
        module_type="mapping"
    )

    import json
    for knowledge_json in sorted(KNOWLEDGE_PADDING_DIR.glob("task*_knowledge.json")):
        task_num = knowledge_json.stem.replace("task", "").replace("_knowledge", "")
        task_json = TASK_PADDING_DIR / f"task{task_num}_implementation.json"

        if not task_json.exists():
            print(f"  [WARN] {task_json} not found, skipping")
            continue

        with open(knowledge_json, "r", encoding="utf-8") as f:
            knowledge_data = json.load(f)
        with open(task_json, "r", encoding="utf-8") as f:
            task_data = json.load(f)

        mapping_processor.process_from_data(knowledge_data, task_data)


def step4_assemble_and_fill():
    """Assemble 生成 temp PPT → Fill 填充"""
    print("\n" + "=" * 70)
    print("[Step 4] Assemble → temp PPT → Fill 填充")
    print("=" * 70)

    from final_ppt.content_process import AssembleProcessor, FillProcessor

    TEMPLATE_DIR = PROJECT_ROOT / "final_ppt" / "content_process" / "template"
    TEMP_OUTPUT_DIR = PROJECT_ROOT / "final_ppt" / "temp"
    MAPPING_DIR = PROJECT_ROOT / "final_ppt" / "mapping"

    # Assemble: 生成 temp PPTX
    assemble_processor = AssembleProcessor(TEMPLATE_DIR, TEMP_OUTPUT_DIR)
    for mapping_json in sorted(MAPPING_DIR.glob("task*_mapping.json")):
        print(f"\n[Assemble] {mapping_json.name}")
        assemble_processor.process_from_mapping(mapping_json)

    # Fill: 填充占位符
    fill_processor = FillProcessor(TEMP_OUTPUT_DIR, MAPPING_DIR)
    fill_processor.process_all()


def step5_integrate_ppt():
    """整合 temp PPT 到 base PPT"""
    print("\n" + "=" * 70)
    print("[Step 5] Integrate: temp PPT → base PPT")
    print("=" * 70)

    from scripts.integrate import IntegrateProcessor

    BASE_PPT_DIR = PROJECT_ROOT / "base_ppt" / "base_ppt"
    TEMP_DIR = PROJECT_ROOT / "final_ppt" / "temp"
    OUTPUT_DIR = PROJECT_ROOT / "output"

    processor = IntegrateProcessor(BASE_PPT_DIR, TEMP_DIR, OUTPUT_DIR)
    processor.process_all()


def main():
    print("=" * 70)
    print("Edu_Agent 执行流程")
    print("=" * 70)

    try:
        step1_word_to_json_and_export()
        step2_llm_chunk()
        step3_render_and_mapping()
        step4_assemble_and_fill()
        step5_integrate_ppt()
    except Exception as e:
        print(f"\n[ERROR] {e}")

    print("\n" + "=" * 70)
    print("完成")
    print("=" * 70)


if __name__ == "__main__":
    main()