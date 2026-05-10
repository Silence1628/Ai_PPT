from docx import Document
from pathlib import Path
from typing import List


class WordChunker:
    """
    Word document chunker - 按【标题2】粗切分为4个大chunk。

    输出：
        chunk1: 项目介绍+引导案例（任务一之前的所有内容）
        chunk2: 任务一 AIGC与大模型概述与环境准备
        chunk3: 任务二 基于ollama部署本地大模型
        chunk4: 任务三 可视化操作界面open-webui部署与应用
    """

    def __init__(self, doc_path: str):
        self.doc = Document(doc_path)
        self._validate_doc()

    def _validate_doc(self):
        """Check if the document has valid content."""
        if not self.doc.paragraphs:
            raise ValueError("Document appears to be empty")

    def chunk(self) -> List[dict]:
        """
        粗切分：按【标题2】将Word文档切分为4个大chunk

        chunk1: 任务一之前的所有内容（项目介绍 + 引导案例）
        chunk2: 任务一 AIGC与大模型概述与环境准备
        chunk3: 任务二 基于ollama部署本地大模型
        chunk4: 任务三 可视化操作界面open-webui部署与应用
        """
        chunks = []
        current_chunk = None

        for para in self.doc.paragraphs:
            style_name = para.style.name

            # 遇到【标题2】→ 开始新 chunk
            if style_name.startswith("Heading 2"):
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = {"title": para.text, "content": "", "level": 2}
            elif current_chunk:
                if para.text.strip():
                    current_chunk["content"] += para.text + "\n"
            else:
                # 任务一之前的内容 → chunk1
                if para.text.strip():
                    if not chunks:
                        chunks.append({"title": "项目介绍+引导案例", "content": "", "level": 2})
                    chunks[0]["content"] += para.text + "\n"

        if current_chunk:
            chunks.append(current_chunk)

        return chunks
