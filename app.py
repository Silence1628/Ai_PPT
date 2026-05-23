"""
Edu_Agent 统一入口

全流程：
  1. Word → Markdown → 数据清洗
  2. 两次切分（project → clean → task）
  3. Base PPT 线：base_json → base PPT（LLM 跳过，使用已有输出）
  4. Final PPT 线：perception → padding_json → temp PPT → fill
  5. 整合：temp PPT 插入 base PPT → output/

用法：
    python app.py
"""
import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))


# =============================================================================
# Step 0: Word → Markdown
# =============================================================================
def step0_word_to_markdown():
    """将 input/*.docx 转换为项目 .md 文件"""
    print("\n" + "=" * 70)
    print("[Step 0] Word → Markdown")
    print("=" * 70)

    input_dir = PROJECT_ROOT / "input"
    docx_files = list(input_dir.glob("*.docx")) if input_dir.exists() else []
    if not docx_files:
        print("  [SKIP] 未找到 .docx 文件，使用已有 .md")
        return

    from word_process.chunker.word_to_markdown import WordToMarkdown
    converter = WordToMarkdown()
    for docx in docx_files:
        converter.split(str(docx), str(PROJECT_ROOT / "word_process" / "original"))
    print("  完成")


# =============================================================================
# Step 1: 第一次数据清洗
# =============================================================================
def step1_clean_first():
    """Word → MD 后第一次清洗"""
    print("\n" + "=" * 70)
    print("[Step 1] 第一次数据清洗")
    print("=" * 70)

    target = PROJECT_ROOT / "word_process" / "original"
    from word_process.chunker.markdown_cleaner import MarkdownCleaner
    MarkdownCleaner(str(target)).process_all()


# =============================================================================
# Step 2: 第一次切分（项目 → before_task + taskN）
# =============================================================================
def step2_split_project():
    """按 # 标题拆分项目 .md → before_task.md / taskN.md"""
    print("\n" + "=" * 70)
    print("[Step 2] 第一次切分：项目 → task")
    print("=" * 70)

    from word_process.chunker.project_splitter import ProjectMdSplitter
    ProjectMdSplitter(str(PROJECT_ROOT / "word_process" / "original")).split_all()


# =============================================================================
# Step 3: 第二次数据清洗
# =============================================================================
def step3_clean_second():
    """第一次切分后清洗"""
    print("\n" + "=" * 70)
    print("[Step 3] 第二次数据清洗")
    print("=" * 70)

    from word_process.chunker.markdown_cleaner import MarkdownCleaner
    MarkdownCleaner(str(PROJECT_ROOT / "word_process" / "original")).process_all()


# =============================================================================
# Step 4: 第二次切分（task → base + perception）
# =============================================================================
def step4_split_task():
    """将 taskN.md 拆分为 base/taskN_base.md + perception/taskN_perception.md"""
    print("\n" + "=" * 70)
    print("[Step 4] 第二次切分：task → base + perception")
    print("=" * 70)

    from word_process.chunker.task_splitter import TaskMdSplitter
    TaskMdSplitter(str(PROJECT_ROOT / "word_process" / "original")).split_all()


# =============================================================================
# Step 5: Base JSON 生成（跳过 LLM，使用已有输出）
# =============================================================================
def step5_base_json():
    """base_json 生成 — 跳过 LLM，检查已有输出"""
    print("\n" + "=" * 70)
    print("[Step 5] Base JSON（跳过 LLM，使用已有 llm_output/base_json/）")
    print("=" * 70)

    base_json_dir = PROJECT_ROOT / "word_process" / "llm_output" / "base_json"
    files = []
    if base_json_dir.exists():
        # Support both flat and project subdirectory
        files = sorted(base_json_dir.glob("*.json"))
        if not files:
            for proj in sorted(base_json_dir.glob("*/")):
                files.extend(sorted(proj.glob("*.json")))
    if files:
        print(f"  已有 {len(files)} 个 base JSON")
    else:
        print("  [WARN] 未找到 base_json，需要运行 scripts/md_to_json.py")


# =============================================================================
# Step 6: 渲染 Base PPT（跳过如果已有输出）
# =============================================================================
def step6_render_base_ppt():
    """base_json → base PPTX（跳过如果已有）"""
    print("\n" + "=" * 70)
    print("[Step 6] 渲染 Base PPT")
    print("=" * 70)

    output_dir = PROJECT_ROOT / "base_ppt" / "base_output"
    existing = list(output_dir.glob("*.pptx")) if output_dir.exists() else []
    if existing:
        print(f"  [SKIP] 已有 {len(existing)} 个 base PPTX，跳过渲染")
        return

    from scripts.json_to_ppt import run_test
    run_test()


# =============================================================================
# Step 7: Perception 流水线（split → AST → flatten）
# =============================================================================
def step7_perception_pipeline():
    """处理 perception 文件：split → AST parse → flatten chunks"""
    print("\n" + "=" * 70)
    print("[Step 7] Perception 流水线")
    print("=" * 70)

    from word_process.processor.perception_splitter import PerceptionSplitter
    from word_process.processor.perception_processor import PerceptionProcessor
    from word_process.processor.markdown_ast import MarkdownASTProcessor

    original_dir = PROJECT_ROOT / "word_process" / "original"
    markdown_cut_dir = PROJECT_ROOT / "word_process" / "llm_input" / "perception" / "markdown_cut"
    original_md_dir = PROJECT_ROOT / "word_process" / "llm_input" / "perception" / "original_markdown"
    preprocessed_dir = PROJECT_ROOT / "word_process" / "llm_input" / "perception" / "preprocessed"

    # Stage 0: 分割 perception.md → knowledge.md + implementation.md
    print("\n  --- Stage 0: 分割 perception ---")
    splitter = PerceptionSplitter(original_dir, markdown_cut_dir)
    for pf in sorted([d for d in original_dir.iterdir() if d.is_dir() and d.name.startswith('项目')]):
        try:
            splitter.process(pf)
            print(f"    {pf.name}: done")
        except Exception as e:
            print(f"    {pf.name}: {e}")

    # Stage 1: H3/H4 AST 解析
    print("\n  --- Stage 1: AST 解析 ---")
    ast_processor = PerceptionProcessor(markdown_cut_dir, original_md_dir, original_dir)
    for pf in sorted([d for d in markdown_cut_dir.iterdir() if d.is_dir() and d.name.startswith('项目')]):
        try:
            result = ast_processor.process(pf)
            print(f"    {pf.name}: {len(result['files'])} files")
        except Exception as e:
            print(f"    {pf.name}: {e}")

    # Stage 2: 扁平化 chunk
    print("\n  --- Stage 2: 扁平化 ---")
    flattener = MarkdownASTProcessor(original_md_dir, preprocessed_dir)
    for pf in sorted([d for d in original_md_dir.iterdir() if d.is_dir() and d.name.startswith('项目')]):
        try:
            result = flattener.process(pf)
            print(f"    {pf.name}: {len(result['files'])} files")
        except Exception as e:
            print(f"    {pf.name}: {e}")


# =============================================================================
# Step 8: Semantic Chunk（跳过 LLM，使用已有输出）
# =============================================================================
def step8_semantic_chunk():
    """LLM 语义切分 — 跳过，检查已有 perception_json"""
    print("\n" + "=" * 70)
    print("[Step 8] Semantic Chunk（跳过 LLM，使用已有 perception_json/）")
    print("=" * 70)

    output_dir = PROJECT_ROOT / "word_process" / "llm_output" / "perception_json"
    total = 0
    if output_dir.exists():
        for proj in output_dir.iterdir():
            if proj.is_dir():
                files = list(proj.rglob("*.json"))
                total += len(files)
                print(f"  {proj.name}: {len(files)} files")
    if total == 0:
        print("  [WARN] 未找到 perception_json，需要运行 perception_semantic_chunker")
    else:
        print(f"  共 {total} 个文件，跳过 LLM 切分")


# =============================================================================
# Step 9: Assemble（生成 temp PPTX）
# =============================================================================
def step9_assemble():
    """读取 perception_json → 生成 temp PPTX"""
    print("\n" + "=" * 70)
    print("[Step 9] Assemble: perception_json → temp PPTX")
    print("=" * 70)

    import win32com.client
    import pythoncom
    from collections import OrderedDict
    from perception_ppt.content_process.assemble import AssembleProcessor

    template_dir = PROJECT_ROOT / "perception_ppt" / "content_process" / "template"
    temp_dir = PROJECT_ROOT / "perception_ppt" / "perception_output"
    padding_base = PROJECT_ROOT / "word_process" / "llm_output" / "perception_json"

    processor = AssembleProcessor(template_dir, temp_dir)

    project_dirs = sorted([d for d in padding_base.iterdir() if d.is_dir() and d.name.startswith('项目')])
    for project_dir in project_dirs:
        knowledge_dir = project_dir / "knowledge"
        task_dir = project_dir / "task"
        if not knowledge_dir.exists():
            continue

        k_files = sorted(knowledge_dir.glob("task*_knowledge.json"))
        print(f"\n  [Project] {project_dir.name} ({len(k_files)} tasks)")

        # 单 PPT 实例处理本项目所有 task
        pythoncom.CoInitialize()
        try:
            ppt = win32com.client.Dispatch("PowerPoint.Application")
        except Exception:
            ppt = win32com.client.Dispatch("WPP.Application")
        ppt.Visible = -1
        try:
            ppt.DisplayAlerts = 0
        except Exception:
            pass

        try:
            for kf in k_files:
                tn = kf.stem.replace("_knowledge", "")
                tf = task_dir / f"{tn}_implementation.json"
                if not tf.exists():
                    print(f"    [SKIP] {tn}: no implementation")
                    continue

                kd = json.loads(kf.read_text(encoding='utf-8'))
                td = json.loads(tf.read_text(encoding='utf-8'))
                processor.task_num = kd.get("task_num", "")

                ks = AssembleProcessor.padding_to_section(kd.get("chunks", []), "knowledge")
                ts = AssembleProcessor.padding_to_section(td.get("chunks", []), "task")

                kr = processor._build_temp_pptx(ppt, ks, temp_dir / "knowledge", "knowledge")
                tr = processor._build_temp_pptx(ppt, ts, temp_dir / "task", "task")
                print(f"    [{tn}] k={kr.name if kr else 'SKIP'}  impl={tr.name if tr else 'SKIP'}")
        finally:
            try:
                ppt.Quit()
            except Exception:
                pass
            pythoncom.CoUninitialize()


# =============================================================================
# Step 10: Fill（填充占位符）
# =============================================================================
def step10_fill():
    """填充 temp PPTX 占位符"""
    print("\n" + "=" * 70)
    print("[Step 10] Fill: 填充占位符")
    print("=" * 70)

    import win32com.client
    import pythoncom
    from perception_ppt.content_process.fill import FillProcessor

    temp_dir = PROJECT_ROOT / "perception_ppt" / "perception_output"
    padding_base = PROJECT_ROOT / "word_process" / "llm_output" / "perception_json"

    filler = FillProcessor(temp_dir)

    project_dirs = sorted([d for d in padding_base.iterdir() if d.is_dir() and d.name.startswith('项目')])
    for project_dir in project_dirs:
        knowledge_dir = project_dir / "knowledge"
        task_dir = project_dir / "task"
        if not knowledge_dir.exists():
            continue

        k_files = sorted(knowledge_dir.glob("task*_knowledge.json"))
        print(f"\n  [Project] {project_dir.name} ({len(k_files)} tasks)")

        pythoncom.CoInitialize()
        try:
            ppt = win32com.client.Dispatch("PowerPoint.Application")
        except Exception:
            ppt = win32com.client.Dispatch("WPP.Application")
        ppt.Visible = -1
        try:
            ppt.DisplayAlerts = 0
        except Exception:
            pass

        try:
            for kf in k_files:
                tn = kf.stem.replace("_knowledge", "")
                tf = task_dir / f"{tn}_implementation.json"
                if not tf.exists():
                    continue

                kd = json.loads(kf.read_text(encoding='utf-8'))
                td = json.loads(tf.read_text(encoding='utf-8'))
                task_num = kd.get("task_num", "")

                ks = FillProcessor.padding_to_section(kd.get("chunks", []), "knowledge")
                ts = FillProcessor.padding_to_section(td.get("chunks", []), "task")

                filler._fill_pptx(ppt, ks, task_num, "knowledge", "03", "知识储备")
                filler._fill_pptx(ppt, ts, task_num, "task", "04", "任务实施")
                print(f"    [{tn}] filled")
        finally:
            try:
                ppt.Quit()
            except Exception:
                pass
            pythoncom.CoUninitialize()


# =============================================================================
# Step 11: Integrate（temp PPT 插入 base PPT）
# =============================================================================
def step11_integrate():
    """将 temp PPT 插入 base PPT，输出最终文件"""
    print("\n" + "=" * 70)
    print("[Step 11] Integrate: temp PPT → base PPT → output/")
    print("=" * 70)

    from scripts.integrate import IntegrateProcessor

    base_ppt_dir = PROJECT_ROOT / "base_ppt" / "base_output"
    temp_dir = PROJECT_ROOT / "perception_ppt" / "perception_output"
    output_dir = PROJECT_ROOT / "output"

    processor = IntegrateProcessor(base_ppt_dir, temp_dir, output_dir)
    processor.process_all()


# =============================================================================
# main
# =============================================================================
def main():
    print("=" * 70)
    print("Edu_Agent — 全流程执行")
    print("=" * 70)

    steps = [
        ("Word → Markdown",           step0_word_to_markdown),
        ("第一次数据清洗",              step1_clean_first),
        ("第一次切分：项目 → task",      step2_split_project),
        ("第二次数据清洗",              step3_clean_second),
        ("第二次切分：task → base+perception", step4_split_task),
        ("Base JSON（跳过LLM）",       step5_base_json),
        ("渲染 Base PPT",             step6_render_base_ppt),
        ("Perception 流水线",          step7_perception_pipeline),
        ("Semantic Chunk（跳过LLM）",  step8_semantic_chunk),
        ("Assemble：temp PPTX",       step9_assemble),
        ("Fill：填充占位符",           step10_fill),
        ("Integrate：输出最终 PPT",    step11_integrate),
    ]

    for name, func in steps:
        try:
            func()
        except Exception as e:
            print(f"\n  [ERROR] {name}: {e}")
            import traceback
            traceback.print_exc()
            ans = input("\n继续执行后续步骤？[Y/n] ").strip().lower()
            if ans == 'n':
                break

    print("\n" + "=" * 70)
    print("完成！最终输出: output/")
    print("=" * 70)


if __name__ == "__main__":
    main()
