
## 访问与下载公开数据集（ModelScope平台）

### 安装modelscope与datasets库

### 打开 ModelScope 网站数据集页面搜索相关数据集

### 使用modelscope命令行下载数据集

### --dataset指定下载数据集的具体名称

### --local_dir 指定数据集下载的目标目录

## 对公开数据集进行预处理

### json.dump(ner_data, outfile, ensure_ascii=False, indent=2)

# 最后打印完成信息

print(f"成功提取 {len(ner_data)} 条 NER 数据并写入 {output_file}")

执行该数据预处理脚本：

cd /app/llm_structure_data

python firefly_process.py

显示如图 1-2-7所示的输出，则表示处理与格式转换完成：

图 1-2-7 数据处理结果

查看处理后的数据，如图 1-2-8所示：

head firefly/firefly_ner_1k.json

图 1-2-8 部分NER数据

## 构造指令数据集

### （一）利用现有大模型生成

### （二）使用指令模板生成

### str:替换后的文本

"""

return output_text.replace("{{name}}", name).replace("{{author}}", author)

# 3. 处理每条数据

processed_identity = []

for item in identity_data:

new_item = {

"instruction": item["instruction"],

"input": item.get("input", ""),  # 如果没有 input 字段，默认为空字符串

"output": replace_template(item["output"])

}

processed_identity.append(new_item)

# 4. 保存处理后的数据到新文件

with open(output_file, "w", encoding="utf-8") as f:

## json.dump(processed_identity, f, ensure_ascii=False, indent=2)

### （三）整合多个指令数据集

为了方便后续任务的训练，我们这里将之前处理与构造的firefly_ner_1k、self_data、 self_identity数据集进行合并处理：

# 加载三份数据

with open("/app/llm_structure_data/firefly/firefly_ner_1k.json", "r", encoding="utf-8") as f:

data1 = json.load(f)

with open("/app/llm_structure_data/self_data.json", "r", encoding="utf-8") as f:

data2 = json.load(f)

with open("/app/llm_structure_data/self_identity.json", "r", encoding="utf-8") as f:

data3 = json.load(f)

# 合并数据

combined_data = data1 + data2 + data3

# 保存为最终训练数据文件

with open("/app/llm_structure_data/final_train_data.json", "w", encoding="utf-8") as f:

### json.dump(combined_data, f, ensure_ascii=False, indent=2)

执行数据合并脚本：

python merge_data.py

查看合并后的数据：

head final_train_data.json && tail final_train_data.json

输出如图 1-2-19所示的信息则说明合并成功：

图 1-2-19 合并多个指令数据集

## 指令数据集清洗检查

### json.dump(cleaned_data, f, ensure_ascii=False, indent=2)

print(f"数据清洗完成，共保留 {len(cleaned_data)} 条有效数据")

print(f"已保存至：{OUTPUT_FILE}")

执行该脚本，得到输出如图 1-2-20所示：

python data_verify.py

图 1-2-20 指令数据集清洗结果

查看清洗后的数据，可以看到字段名称，修改为instruction，并且中英文混杂时，英文前后多余的空格消失，如图 1-2-21所示：

head final_cleaned_data.json && tail final_cleaned_data.json

图 1-2-21 清洗后的指令数据集