### 【任务实施】
#### 一、新能源汽车市场简报助手
在本任务中我们要用工作流实现一个数据分析的skill，实现从本地上传csv文件到工作流中，并对文件内容的格式进行处理，保证后续代码可以正常运行。这个流程将相关逻辑封装，可以独立维护并且允许智能体复用。
##### 步骤一 准备表格材料
本案例使用的原始数据来自Our World in Data 的电动汽车专题页面https://ourworldindata.org/electric-car-sales，为了适配RAGFlow上传操作，将原始数据处理为一份教学样本，包括2019-2024年的12个国家的数据，实现任务需要的表格材料采用存放在路径xxxx中。
字段名
含义
country
国家或地区名称
code
三位国家代码
region
区域
year
年份
ev_sales
新能源汽车销量
ev_sales_share
新能源汽车销量占新车销量百分比
ev_stock
新能源汽车保有量
source_name
数据来源名称
source_url
数据来源链接
license
许可说明
需要特别说明的是：ev_sales_share 在本案例样本中采用百分比数值表示。例如，字段值38 表示38%。
##### 步骤二 搭建文件上传工作流
我们需要在RAGFlow中搭建一个工作流，允许用户在工作流开始节点上传文件。首先打开RAGFlow，新建一个智能体工作流，在开始节点的“模式“中选择任务模式，如图xxx，在开始节点中下方可以看到“输入”，这是在流程开始前，需要用户给出的输入信息，点击箭头所指的加号添加变量。在“类型”中选择“文件”，键和名称设置为“csv_file”，点击确定后可以看到成功添加csv_file变量。
在回复节点添加csv_file变量直接回复，保存并运行后可以看到弹出文档上传的窗口，选择path/to/file/ev_market_sample.csv，当文档成功上传后会在窗口显示，选择下一步，如图xxx，可以看到文件内容以文本形式被打印出来了。选择对话流模式也是一样的情况，在用户发送任意提问后，文件内容也会以同样的方式返回。
##### 步骤三 处理上传的csv文件
我们看到返回的内容不止有字典格式给出的文本内容，也有这个文件的相关信息，因此我们还需要对这段文本进行清洗，才能给后续节点使用。
在智能体工作流中我们很容易想到直接让智能体帮我们处理文件并给出最终结果，但这会占用大量的Token和上下文资源，因此在这一步我们通过调用代码工具来实现。创建一个代码节点，传入参数设置为这个csv文件，把它从文本转换为json列表的格式，最后设置输出格式为object。
```
REQUIRED_FIELDS = [
"country", "code", "region", "year",
"ev_sales", "ev_sales_share", "ev_stock",
"source_name", "source_url", "license"
]
def main(uploaded_file_content):
text = uploaded_file_content[0]
text = text.split("Content as following:", 1)[1].strip()
rows = []
for line in text.splitlines():
line = line.strip()
if not line:
continue
row = {}
parts = [p.strip() for p in line.split(";") if p.strip()]
for part in parts:
if "：" in part:
key, value = part.split("：", 1)
elif ":" in part:
key, value = part.split(":", 1)
else:
continue
row[key.strip()] = value.strip()
if row:
rows.append(row)
return {
"row_count": len(rows),
"rows": rows
}
```
再次运行工作流上传文件，可以看到数据结果已经和我们设置的一样，形成了json格式的列表
##### 步骤四 分析表格数据
格式化后的表格数据对我们人类来说和原本的表格差别不大，所以为了更直观地看到表格中的数据，我们可以再用代码工具实现一个简单的数据分析功能，分析Europe区域中2024年ev_sales_share的前5名，并以简报的形式描述返回的结果。
要实现这一步，我们需要获取限定条件下ev_sales_share的前5名，这是一个排序功能，明白这一点后我们来添加第二个代码节点，实现该功能。为了和第一个区分开，我们分别给两个节点起名为“数据预处理”和“数据排序”。
添加如下的筛选及排序代码，并设置输入输出变量和类型。
```
def main(csv_file):
rows = csv_file.get("rows")
year = 2024
metric = "ev_sales_share"
top_n = 5
region = "Europe"
filtered = [r for r in rows if int(r["year"]) == year]
if region and region != "Global":
filtered = [r for r in filtered if r["region"] == region]
filtered.sort(key=lambda x: float(x[metric]), reverse=True)
return {
"analysis_type": "topn_ranking",
"year": year,
"metric": metric,
"items": filtered[:top_n]
}
```
执行到这里，我们获取到了分析需要的数据，接下来需要把数据整理成文稿，形成一篇简报，所以还需要添加一个智能体节点，配合系统提示词：
```
你是一名新能源汽车产业研究助理。
请根据输入的结构化分析结果`数据排序/content`分析，生成一份商务风格的 Markdown 简报。
要求：
1. 只基于输入数据写作；
2. 先给出 3 条关键发现；
3. 再给出明细列表；
4. 最后保留数据来源与许可说明；
5. 不得编造数据。
```
如图xxx，可以看到模型按照我们的要求生成简报。值得注意的是“数据排序”的返回结果有两个，一个是被我们设置为Object的result，另一个是string格式的content，如果要被代码处理，使用Object格式的变量传输可以方便我们调整格式，但如果被内置的条件节点、回复节点或智能体节点调用，要使用string格式变量更容易被节点接受。
##### 步骤五 验证文件
在工程项目中，文件不会像课程用例一样标准，可能会有缺失值、格式错误、文件失效等问题，所以我们可以在预处理数据的同时添加验证逻辑，如果文件有问题，将它引导其他路由中。这部分逻辑可以通过修改代码模块实现：
```
REQUIRED_FIELDS = [
"country", "code", "region", "year",
"ev_sales", "ev_sales_share", "ev_stock",
"source_name", "source_url", "license"
]
def main(uploaded_file_content):
if not uploaded_file_content:
return {"ok": False, "message": "上传内容为空", "rows": []}
text = uploaded_file_content[0]
if "Content as following:" in text:
text = text.split("Content as following:", 1)[1].strip()
rows = []
for line in text.splitlines():
line = line.strip()
if not line:
continue
row = {}
parts = [p.strip() for p in line.split(";") if p.strip()]
for part in parts:
if "：" in part:
key, value = part.split("：", 1)
elif ":" in part:
key, value = part.split(":", 1)
else:
continue
row[key.strip()] = value.strip()
if row:
rows.append(row)
if not rows:
return {"ok": False, "message": "未解析出有效数据", "rows": []}
fieldnames = list(rows[0].keys())
missing = [f for f in REQUIRED_FIELDS if f not in fieldnames]
if missing:
return {
"ok": False,
"message": f"缺少字段: {', '.join(missing)}",
"rows": rows
}
return {
"ok": True,
"message": "文件加载成功",
"row_count": len(rows),
"rows": rows
}
```
通过这套校验机制，配合图xxx的问题分类节点，可以把一些基础错误隔绝在工作流外。设置输入变量为string格式的`数据处理/content`，两个问题分类如红框所示，指代“ok”变量的结果，分别是True和False。错误结果的返回节点配置使用的输出变量同样是`数据处理/content`，因为在其中也有保存的信息。
这样在运行过程中给，就可以测试文件是否正常，能否以工作流需要的格式接收数据，将这些信息统一约定并校验有助于智能体工作流的搭建和扩展。学员可以将csv表格复制备份并删除其中一两行关键列，测试校验效果能否顺利执行。
#### 二、新能源汽车市场简报助手【太复杂，待评估】
