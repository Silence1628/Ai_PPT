"""
Stage 2: Markdown AST → H4 切块

将 original_markdown JSON（H3/H4 嵌套）扁平化为独立的 H4 chunk 列表。
每个 H4 是一个独立 chunk；H3 无 H4 子节点时，该 H3 本身作为 chunk。

输入：word_process/llm_input/perception/original_markdown/{project}/{section}/task{N}_{section}.json
输出：word_process/llm_input/perception/preprocessed/{project}/task{N}_{section}.json
"""
from pathlib import Path
from typing import List, Dict
import json


class MarkdownASTProcessor:
    """将 H3/H4 嵌套 AST 扁平化为独立 chunk"""

    def __init__(self, input_dir: Path, output_dir: Path):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)

    def process(self, project_folder: Path) -> dict:
        project_name = project_folder.name
        results = {"project": project_name, "files": []}

        for section in ["knowledge", "task"]:
            section_dir = self.input_dir / project_name / section
            if not section_dir.exists():
                continue

            json_files = sorted(section_dir.glob("task*_*.json"))
            for json_file in json_files:
                out_path = self.output_dir / project_name / section / json_file.name
                out_path.parent.mkdir(parents=True, exist_ok=True)

                data = json.loads(json_file.read_text(encoding='utf-8'))
                processed = self._flatten_chunks(data)
                out_path.write_text(json.dumps(processed, ensure_ascii=False, indent=2), encoding='utf-8')
                results["files"].append(str(out_path))

        return results

    def _flatten_chunks(self, data: dict) -> dict:
        """将嵌套 H3/H4 结构扁平化为独立 chunk 列表"""
        chunks = []
        chunk_id = 0

        for h3 in data.get("chunks", []):
            h3_title = h3.get("title", "")

            # H3 with H4 children: each H4 is a chunk
            if h3.get("children"):
                for h4 in h3["children"]:
                    chunk_id += 1
                    chunks.append({
                        "id": f"chunk_{chunk_id}",
                        "level": 4,
                        "title": h4.get("title", ""),
                        "parent_title": h3_title,
                        "content": h4.get("content", ""),
                        "code_blocks": h4.get("code_blocks", []),
                        "chart_refs": h4.get("chart_refs", [])
                    })
            # H3 without children: H3 itself is a chunk
            elif h3.get("content"):
                chunk_id += 1
                chunks.append({
                    "id": f"chunk_{chunk_id}",
                    "level": 3,
                    "title": h3_title,
                    "parent_title": "",
                    "content": h3.get("content", ""),
                    "code_blocks": h3.get("code_blocks", []),
                    "chart_refs": h3.get("chart_refs", [])
                })

        return {
            "task_num": data.get("task_num", ""),
            "task_title": data.get("task_title", ""),
            "section": data.get("section", ""),
            "chunks": chunks
        }


def main():
    from pathlib import Path

    PROJECT_ROOT = Path(__file__).parent.parent.parent
    input_dir = PROJECT_ROOT / "word_process" / "llm_input" / "perception" / "original_markdown"
    output_dir = PROJECT_ROOT / "word_process" / "llm_input" / "perception" / "preprocessed"

    processor = MarkdownASTProcessor(input_dir, output_dir)

    project_folders = [d for d in input_dir.iterdir() if d.is_dir() and d.name.startswith('项目')]
    for project_folder in sorted(project_folders):
        print(f"\n处理项目: {project_folder.name}")
        try:
            result = processor.process(project_folder)
            total_chunks = sum(
                len(json.loads((Path(f)).read_text(encoding='utf-8'))['chunks'])
                for f in result['files']
            )
            print(f"  生成文件: {len(result['files'])}, 总 chunk 数: {total_chunks}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"  错误: {e}")


if __name__ == "__main__":
    main()