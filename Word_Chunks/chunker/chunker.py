from docx import Document
from pathlib import Path
from typing import List


class WordChunker:
    """
    Word document chunker - 按【标题2】粗切分为4个大chunk。

    输出结构化数据：
        chunk1: 项目介绍+引导案例（任务一之前的所有内容）
        chunk2-4: 每个任务包含
            - title: 标题
            - level: 级别
            - main_content: 主内容（不含知识储备/任务实施）
            - knowledge_reserve: 知识储备模块内容列表
            - task_implementation: 任务实施模块内容列表
    """

    # 样式类型映射
    STYLE_TYPES = {
        'Normal': 'text',
        'List Paragraph': 'text',
        'Heading 3': 'section_title',
        'Heading 4': 'sub_heading',
        'Heading 5': 'sub_heading',
        'Heading 6': 'sub_heading',
        'HTML Preformatted': 'skip',  # 代码块 - 跳过
    }

    # 特殊章节标题
    SECTION_TITLES = ('知识储备', '任务实施')

    def chunk(self, doc_path: str) -> List[dict]:
        """
        粗切分：按【标题2】将Word文档切分为4个大chunk
        """
        doc = Document(doc_path)
        chunks = []
        current_chunk = None
        current_section = 'main'  # 'main' | 'knowledge_reserve' | 'task_implementation'

        for para in doc.paragraphs:
            style_name = para.style.name
            text = para.text.strip()
            if not text:
                continue

            # 遇到【标题2】→ 开始新 chunk
            if style_name.startswith('Heading 2'):
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = {
                    'title': para.text,
                    'level': 2,
                    'main_content': '',
                    'knowledge_reserve': [],
                    'task_implementation': []
                }
                current_section = 'main'
            # 任务一之前的内容 → 作为chunk1（项目介绍+引导案例）
            elif current_chunk is None:
                if not chunks:
                    chunks.append({
                        'title': '项目介绍+引导案例',
                        'level': 2,
                        'main_content': '',
                        'knowledge_reserve': [],
                        'task_implementation': []
                    })
                chunks[0]['main_content'] += text + '\n'
            # 检测章节标题（仅识别【知识储备】和【任务实施】精确标题）
            elif text == '【知识储备】':
                current_section = '知识储备'
            elif text == '【任务实施】':
                current_section = '任务实施'
            elif text in ('【任务小结】', '【任务拓展】'):
                current_section = 'main'
            # 在子section中遇到 Heading 2 → 退出子section（Heading 2 是 chunk 边界）
            elif current_section != 'main' and style_name.startswith('Heading'):
                level = int(style_name.split()[-1]) if style_name.split()[-1].isdigit() else 0
                if level <= 2:
                    current_section = 'main'
            if current_chunk:
                para_type = self.STYLE_TYPES.get(style_name, 'skip')
                level = int(style_name.split()[-1]) if style_name.split()[-1].isdigit() else 0
                para_data = {'type': para_type, 'level': level, 'text': text}

                if para_type == 'skip':
                    pass  # 代码块跳过
                elif current_section == '知识储备':
                    current_chunk['knowledge_reserve'].append(para_data)
                elif current_section == '任务实施':
                    current_chunk['task_implementation'].append(para_data)
                else:
                    current_chunk['main_content'] += text + '\n'

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def export_original_content(self, chunks: list[dict], output_dir: str, section_filter: str = None):
        """
        按任务切分导出知识储备或任务实施原始内容，以 Heading 4 分段。

        Args:
            chunks: WordChunker.chunk() 返回的切分结果
            output_dir: 输出目录路径（直接是 knowledge/ 或 task/ 目录）
            section_filter: None 表示导出所有，指定 "knowledge_reserve" 或 "task_implementation" 只导出对应内容
        """
        from pathlib import Path
        import json, re

        base = Path(output_dir)
        base.mkdir(parents=True, exist_ok=True)

        # 跳过 chunk1（项目介绍+引导案例），从 chunk2 开始是任务
        task_chunks = chunks[1:]

        # 中文数字 → 阿拉伯数字映射
        CN_TO_ARABIC = {
            "一": "1", "二": "2", "三": "3",
            "四": "4", "五": "5", "六": "6",
        }

        for idx, chunk in enumerate(task_chunks, 1):
            # 从标题提取任务序号，如 "任务一" → "1"
            m = re.search(r"任务([一二三四五六]+)", chunk.get("title", ""))
            task_num = CN_TO_ARABIC.get(m.group(1), str(idx)) if m else str(idx)

            # 确定要导出的 section
            if section_filter:
                sections = [(section_filter, "knowledge" if section_filter == "knowledge_reserve" else "implementation")]
            else:
                sections = [
                    ("knowledge_reserve", "knowledge"),
                    ("task_implementation", "implementation"),
                ]

            for section_key, filename_prefix in sections:
                all_segments = []
                current_segment = None

                for para in chunk.get(section_key, []):
                    # Heading 4 → 开始新段落
                    if para["type"] == "sub_heading" and para["level"] == 4:
                        if current_segment:
                            all_segments.append(current_segment)
                        clean_heading = re.sub(r'^[一-龥]+[.、]\s*', '', para["text"])
                        current_segment = {
                            "heading": clean_heading,
                            "content": "",
                        }
                    elif current_segment is not None:
                        current_segment["content"] += para["text"] + "\n"

                if current_segment:
                    all_segments.append(current_segment)

                # 统计 heading 4（sub_heading level=4）数量
                heading4_count = sum(
                    1 for para in chunk.get(section_key, [])
                    if para["type"] == "sub_heading" and para["level"] == 4
                )

                filename = f"task{task_num}_{filename_prefix}.json"
                # 保留最新版本：先删除同名旧文件
                existing = (base / filename)
                if existing.exists():
                    existing.unlink()
                with open(base / filename, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "task_num": task_num,
                            "task_title": chunk.get("title", ""),
                            "template_type": section_key,
                            "heading4_count": heading4_count,
                            "segments": all_segments,
                        },
                        f,
                        ensure_ascii=False,
                        indent=2,
                    )
