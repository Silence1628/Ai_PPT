"""
文本框容量测试脚本
读取 schema 并计算每个模板页面的容量参数

输出到: PPT_Perception/data/{knowledge,task}/
"""
import json
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
TEMPLATE_CONTENT_DIR = PROJECT_ROOT / "PPT_Perception" / "template" / "content"
OUTPUT_DIR = PROJECT_ROOT / "PPT_Perception" / "data"


def calculate_max_lines(height_emu: int, font_size: int, line_spacing: float) -> int:
    """计算文本框最大行数"""
    line_height_emu = font_size * line_spacing * 12700
    return int(height_emu / line_height_emu)


def calculate_max_chars_per_line(width_emu: int, font_size: int, char_width_ratio: float = 0.5) -> int:
    """计算每行最大字符数（字宽系统数默认0.5，即字宽≈font_size×0.5）"""
    char_width_emu = font_size * char_width_ratio * 12700
    return int(width_emu / char_width_emu)


def process_schema(schema_path: Path, output_path: Path):
    """处理单个 schema 文件并输出容量计算结果"""
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema = json.load(f)

    template_name = schema_path.stem

    results = {
        "template_name": template_name,
        "pages": []
    }

    for page in schema.get('pages', []):
        content_textbox = page.get('content_textbox', {})

        height_emu = content_textbox.get('height', 0)
        font_info = content_textbox.get('font', {})
        font_size = font_info.get('size', 18)
        line_spacing = font_info.get('line_spacing', 1.5)

        max_lines = calculate_max_lines(height_emu, font_size, line_spacing)
        max_chars_per_line = calculate_max_chars_per_line(content_textbox.get('width', 0), font_size)
        max_total_chars = max_lines * max_chars_per_line

        page_result = {
            "index": page.get('index'),
            "name": page.get('name'),
            "content_textbox": {
                "name": content_textbox.get('name'),
                "height_emu": height_emu,
                "width_emu": content_textbox.get('width', 0),
                "font_size": font_size,
                "line_spacing": line_spacing,
                "max_lines": max_lines,
                "max_chars_per_line": max_chars_per_line,
                "max_total_chars": max_total_chars
            }
        }
        results["pages"].append(page_result)

    if output_path.exists():
        output_path.unlink()
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"[OK] {output_path.name}")
    return results


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("文本框容量计算")
    print("=" * 60)

    schema_files = list(TEMPLATE_CONTENT_DIR.glob("*/**/*_schema.json"))

    if not schema_files:
        print(f"[WARN] 未找到 schema 文件: {TEMPLATE_CONTENT_DIR}")
        return

    for schema_path in schema_files:
        template_folder = schema_path.parent.name
        output_subdir = OUTPUT_DIR / template_folder
        output_subdir.mkdir(parents=True, exist_ok=True)
        output_name = f"{template_folder}_capacity.json"
        output_path = output_subdir / output_name

        print(f"\n处理: {schema_path.relative_to(PROJECT_ROOT)}")
        process_schema(schema_path, output_path)

    print("\n" + "=" * 60)
    print("完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
