
## 环境准备

### 启动部署容器

### 检查环境

## 安装Transformer以及可视化工具

## 搭建简化版Transformer模型

### self.embedding = nn.Embedding(vocab_size, embed_dim)

# 定义单层 Transformer Encoder Layer

encoder_layer = nn.TransformerEncoderLayer(

d_model=embed_dim,   # 输入特征维度

nhead=num_heads,     # 注意力头的数量

batch_first=True     # 输入形状为 [batch_size, seq_len, embed_dim]

)

# 使用 TransformerEncoder 将多个 encoder_layer 堆叠起来

### self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers)

# 最后的全连接层，用于输出每个位置对 vocab 中每个词的概率

### self.fc_out = nn.Linear(embed_dim, vocab_size)

def forward(self, src):

"""

前向传播函数

参数:

## src:输入张量，形状为 [batch_size, seq_len]，包含 token 的索引值

# output:输出张量，形状为 [batch_size, seq_len, vocab_size]

## 模型结构

### 输入嵌入层（Embedding）

#### 将离散的 token ID 转换为连续向量（维度为 embed_dim）。

##### Transformer 编码器

###### 使用多个标准的 TransformerEncoderLayer 堆叠而成（默认3层）。

####### 每个编码层包含多头自注意力机制和前馈网络。

######## 输出层（全连接层）

######### 将编码后的特征映射回词汇表大小，用于预测每个位置上的 token。

########## 前向传播流程

########### 输入形状：(batch_size, seq_len) 的 token 索引。

############ 经过嵌入层后变为：(batch_size, seq_len, embed_dim)。

############# 通过 Transformer 编码器提取上下文信息。

############## 最终输出形状：(batch_size, seq_len, vocab_size)，表示每个位置对所有词的概率分布。

############### 示例配置

################ 词汇表大小：10,000

################# 批次大小：32

################## 序列长度：20

################### 输出：32 个样本 × 20 个词位 × 10,000 个词的概率

## 使用可视化工具查看注意力机制

### model.to(device)

### model.eval()

# 准备输入数据

text = "The animal didn't cross the street because it was too tired"

inputs = tokenizer.encode_plus(text, return_tensors='pt')

input_ids = inputs['input_ids'].to(device)

attention = model(input_ids)[-1]  # 获取注意力权重

# 将输入ID转换回token

tokens = tokenizer.convert_ids_to_tokens(input_ids[0])

# 保存可视化结果

html = head_view(attention, tokens, html_action='return')

with open('/app/llm_structure_data/attention.html', 'w') as f:

## f.write(html.data)

# 1.指代消解(观察"it"的注意力)：推荐查看较高层(8-12层)，"it"会强烈关注"animal"而不是"street"，这展示了BERT如何解决代词指代问题，如图 1-1-12所示：

 2.否定词影响(观察"didn't"的注意力)：推荐查看中间层(4-7层)，"didn't"会关注"cross"，表示否定作用于这个动词，如图 1-1-13所示：

 3.特殊token观察：查看[CLS]和[SEP]token的注意力模式。[CLS] token 是用于表示分类任务中整个输入序列汇总信息的特殊标记，通常在BERT等模型中作为句子或文本对的起始标志。[SEP] token 是用于分隔不同句子或句子对的特殊标记，帮助模型区分输入中的不同语义单元。通常在低层（第0层）时，它们主要关注自己，如图 1-1-14所示。