
## 使用不同的分词器实现分词

### 首先，我们需要认识到：计算机无法直接处理我们书写的文字，它们只能识别01数字。同样地，模型也不能直接理解我们的自然语言输入，第一步是将每一个词语转化为一个唯一的编号，这个过程叫做分词与编码（Tokenization and Encoding） 。例如，“我喜欢自然语言处理”这句话会被分词器拆解为：["我", "喜欢", "自然", "语言", "处理"]。接着，每个词都会被映射成一个整数编号，比如：[100, 3456, 7890, 2345, 6789]。这个编号来自一个庞大的词汇表，也就是所谓的“词典”，它是模型训练时就确定好的。每一种语言模型都对应着一个特定的词典。

### （一）使用jieba进行分词

### jieba 是一个用于中文文本处理的 Python 库，主要用于中文分词。它可以帮助我们将一段连续的中文文本切分成一个个有意义的词语，便于后续的自然语言处理任务，比如文本分析、关键词提取、词频统计等。

### jieba 的使用非常简单，支持多种分词模式，包括精确模式、全模式和搜索引擎模式。精确模式适合对准确度要求较高的场景，全模式会把句子尽可能多地切分成词语，适合快速扫描，而搜索引擎模式则会在精确模式的基础上进一步细分长词，提升召回率。

### 除了基本的分词功能，jieba 还支持用户自定义词典，这样可以将一些专业术语或者特定领域的词汇加入到分词器中，提高分词的准确性。此外，它还提供了关键词提取、词性标注等功能，方便进行更深入的文本分析。

### 总的来说，jieba 是一个功能强大且易于使用的中文分词工具，广泛应用于数据挖掘、信息检索和自然语言处理等领域。

### 安装jieba库

### 使用 jieba 对一段进行分词，比较不同分词模式的输出差异：

### 添加自定义词典提升效果，创建一个 custom_dict.txt 文件，内容如下：

### （二）使用BERT tokenizer进行分词

### （三）使用Qwen tokenizer进行分词

## Transformer 中的词嵌入与位置编码

### 安装依赖库

### 运行词嵌入与位置编码的代码脚本：

### python bert_embeddings_similarity.py

### （一）词嵌入—— 将编号映射为向量

### Goal:Understand how word embeddings encode semantics and positional encodings add structural information.

"""

import os

import torch

import numpy as np

from transformers import BertModel, BertTokenizer

from sklearn.metrics.pairwise import cosine_similarity

from sklearn.decomposition import PCA

import matplotlib.pyplot as plt

import seaborn as sns

# 设置 Matplotlib 字体为英文字体，避免中文字体缺失问题

## plt.rcParams['font.sans-serif'] = ['DejaVu Sans']

## plt.rcParams['axes.unicode_minus'] = False  # 避免负号显示异常

# os.makedirs('embeddings_analysis', exist_ok=True)

 embeddings.extend([emb1, emb2])

 labels.extend([w1, w2])

 plt.figure(figsize=(10, 8))

 plt.scatter(emb_2d[i, 0], emb_2d[i, 1], label=label)

 plt.annotate(label, (emb_2d[i, 0], emb_2d[i, 1]))

 plt.title("Word Embedding Semantic Space (PCA Reduced)")

 plt.xlabel("PCA Component 1")

 plt.ylabel("PCA Component 2")

 plt.legend()

 plt.grid(True)

 plt.savefig('embeddings_analysis/word_embeddings.png', dpi=300, bbox_inches='tight')

 plt.show()

 （二）位置编码——告诉模型词语的顺序

 plt.figure(figsize=(12, 10))

 sns.heatmap(pos_sim_matrix, cmap="YlGnBu")

 plt.title(f"Position Embedding Similarity Matrix (First {max_pos} Positions)")

 plt.xlabel("Position Index")

 plt.ylabel("Position Index")

 plt.savefig('embeddings_analysis/position_similarity.png', dpi=300, bbox_inches='tight')

 plt.show()

 plt.figure(figsize=(12, 6))

 plt.plot(pos_range, pos_emb[:max_pos, dim], label=f"Dim {dim}")

 plt.title("Position Embedding Values Across Positions")

 plt.xlabel("Position Index")

 plt.ylabel("Embedding Value")

 plt.legend()

 plt.grid()

 plt.savefig('embeddings_analysis/position_values.png', dpi=300, bbox_inches='tight')

 plt.show()

 观察不同位置词汇的位置编码之间的相关性

 观察不同位置词汇的位置编码的数值变化

 （三）最终输入的构造：词嵌入 + 位置编码

 plt.figure(figsize=(15, 5))

 plt.subplot(1, 3, 1)

 plt.scatter(components[i, 0], components[i, 1], label=label)

 plt.annotate(label.split(":")[1], (components[i, 0], components[i, 1]))

 plt.title("Pure Word Embedding Space")

 plt.grid()

 plt.subplot(1, 3, 2)

 plt.scatter(components[i+len(tokens), 0], components[i+len(tokens), 1], label=f"Pos{i}")

 plt.annotate(f"Pos{i}", (components[i+len(tokens), 0], components[i+len(tokens), 1]))

 plt.title("Pure Position Embedding Space")

 plt.grid()

 plt.subplot(1, 3, 3)

 plt.scatter(components[i+2*len(tokens), 0], components[i+2*len(tokens), 1], label=label)

 plt.annotate(label.split(":")[1], (components[i+2*len(tokens), 0], components[i+2*len(tokens), 1]))

 plt.title("Combined Embedding Space")

 plt.grid()

 plt.tight_layout()

 plt.savefig('embeddings_analysis/joint_embeddings.png', dpi=300, bbox_inches='tight')

 plt.show()