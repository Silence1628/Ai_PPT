"""
padding_processor - 将 original_content 转换为 padding_content

过滤代码内容，按 schema 容量切割，为第二阶段模板填充提供数据。
"""
import json
import re
from pathlib import Path
from typing import Optional


class PaddingProcessor:
    """
    处理 original_content → padding_content 转换。

    核心规则：
      - 代码必须去除（关键字/命令行/代码块）
      - 非代码内容完整填入，不遗漏
      - 按 schema 容量固定截断切割
    """

    CODE_BLOCK_PATTERN = re.compile(r"```[\s\S]*?```")
    CODE_LINE_PATTERNS = [
        re.compile(r"^(import |def |class |return |for |if |else:|while |try:|except:)\s*"),
        re.compile(r"^(pip |cd |ls |nohup |python |python3 |sudo |mkdir |touch |cat |echo |grep )\s*"),
        re.compile(r"^(>>> |\$ |> )\s*"),
        re.compile(r"^\s{4,}.*#.*$"),
        re.compile(r"^\s{4,}\"\"\".*\"\"\"$"),
        re.compile(r"^\s{4,}'''.*'''$"),
        re.compile(r"^(self|super|cls)\.[\w]+\("),
        re.compile(r"^[\w\.]+\([^\)]*\)\s*[=:]"),
        re.compile(r"^[\w\.\s]+=[\s]*[a-zA-Z][\w\(\)\.]+"),
        re.compile(r"^\s{4,}[\w]+=.*[a-zA-Z][\)\]]"),
        re.compile(r"^\s{4,}[\w\s\.\(\)]+[=\(]"),
    ]

    def __init__(self, schema_path: Path, original_dir: Path, output_dir: Path):
        self.schema_path = Path(schema_path)
        self.original_dir = Path(original_dir)
        self.output_dir = Path(output_dir)
        self.max_chars = 0

    def process_all(self):
        """扫描 original_content 处理所有 JSON"""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        for json_file in sorted(self.original_dir.glob("*.json")):
            if json_file.name.startswith("~"):
                continue
            print(f"[PADDING] 处理: {json_file.name}")
            self.process_one(json_file)

    def process_one(self, json_file: Path) -> Optional[Path]:
        """处理单个 original_content JSON"""
        with open(json_file, "r", encoding="utf-8") as f:
            original_data = json.load(f)

        self.max_chars = self._load_max_chars()

        segments = []
        for seg in original_data.get("segments", []):
            heading = seg.get("heading", "")
            content = seg.get("content", "")

            clean_content = self._remove_code(content)
            chunks = self._split_by_capacity(clean_content, self.max_chars)

            content_chunks = [
                {"chunk_index": i + 1, "content": chunk}
                for i, chunk in enumerate(chunks)
            ]

            segments.append({
                "heading": heading,
                "content_chunks": content_chunks
            })

        padding_data = {
            "task_num": original_data.get("task_num", ""),
            "task_title": original_data.get("task_title", ""),
            "template_type": original_data.get("template_type", ""),
            "heading4_count": original_data.get("heading4_count", 0),
            "schema_name": self.schema_path.stem,
            "segments": segments
        }

        output_file = self.output_dir / json_file.name
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(padding_data, f, ensure_ascii=False, indent=2)

        print(f"      → {output_file.name}")
        return output_file

    def _load_max_chars(self) -> int:
        """从 schema 读取第一页的 max_chars"""
        with open(self.schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)

        pages = schema.get("pages", [])
        if not pages:
            return 500

        first_page = pages[0]
        textbox = first_page.get("content_textbox", {})
        height = textbox.get("height", 0)
        width = textbox.get("width", 0)
        font_info = textbox.get("font", {})
        font_size = font_info.get("size", 18)
        line_spacing = font_info.get("line_spacing", 1.5)

        return self.calculate_max_chars(height, width, font_size, line_spacing)

    @staticmethod
    def calculate_max_chars(height_emu: int, width_emu: int,
                            font_size: int, line_spacing: float) -> int:
        """计算文本框最大字符数"""
        line_height_emu = font_size * line_spacing * 12700
        max_lines = int(height_emu / line_height_emu)
        max_chars_per_line = int(width_emu / (font_size * 0.5 * 12700))
        return max_lines * max_chars_per_line

    def _remove_code(self, text: str) -> str:
        """
        过滤代码内容，返回纯文本。
        严格按排除规则执行，不做二次判断。
        """
        text = self.CODE_BLOCK_PATTERN.sub("", text)

        lines = text.split("\n")
        clean_lines = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                clean_lines.append("")
                continue

            is_code = False
            for pattern in self.CODE_LINE_PATTERNS:
                if pattern.match(stripped):
                    is_code = True
                    break

            if not is_code:
                clean_lines.append(line)

        result = "\n".join(clean_lines)

        result = re.sub(r"\n{3,}", "\n\n", result)

        return result.strip()

    def _split_by_capacity(self, text: str, max_chars: int) -> list:
        """按容量固定截断切割文本"""
        if not text:
            return []

        chunks = []
        remaining = text

        while remaining:
            if len(remaining) <= max_chars:
                chunks.append(remaining)
                break

            chunk = remaining[:max_chars]
            remaining = remaining[max_chars:]
            chunks.append(chunk)

        return chunks
