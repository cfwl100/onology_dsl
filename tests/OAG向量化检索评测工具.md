# OAG向量化检索评测工具

`oag_vector_eval.py`使用`OAG_本体索引结构.xlsx`中的种子节点、元数据元素和实例元素，比较不同Embedding文本组合与查询拆分方式的检索效果。

固定实验条件：

- Embedding模型：`BAAI/bge-m3`
- 向量维度：1024
- 向量归一化：L2 normalize
- 距离：COSINE
- GaussVector类型：`floatvector(1024)`
- GaussVector余弦距离操作符：`<+>`

数据来源：

- https://github.com/cfwl100/onology_dsl/blob/main/tests/OAG_%E6%9C%AC%E4%BD%93%E7%B4%A2%E5%BC%95%E7%BB%93%E6%9E%84.xlsx
- https://support.huaweicloud.com/intl/zh-cn/centralized-vector-devg-v10-gaussdb/gaussdb-38-0109.html

## 1. 对比方案

|方案|索引文本/向量行|
|---|---|
|`all_fields_single`|当前基线：名称、显示名、描述、同义词拼成一个向量|
|`core_short_single`|核心短向量：名称/值、显示名、同义词|
|`term_description_multi`|术语向量与描述向量分开|
|`context_shadow_multi`|术语、描述之外增加ObjectType/Property上下文影子向量|
|`atomic_field_rows`|每个字段、每条同义词分别形成向量行，作为效果上限与成本对照|

多向量方案检索后先按`entity_key`归并，默认取同一实体的最大加权相似度，不会因一个实体拥有更多向量行而直接累加得分。

查询侧同时测试：

|策略|说明|
|---|---|
|`whole`|原始问题整句Embedding|
|`token`|对原始问题分词，每个词分别Embedding后合并结果|
|`semantic_phrase`|使用标注文件中的`semantic_units`完整语义短语|
|`hybrid`|原始问题与Semantic Units联合召回|

`token`是用户提出的总体流程，也是必要对照组；最终方案不应预设它一定优于整句或语义短语。

## 2. 安装

建议使用Python 3.10以上的独立虚拟环境：

```bash
python -m venv .venv-oag-eval
source .venv-oag-eval/bin/activate
pip install -r tests/oag_vector_eval_requirements.txt
```

BGE-M3可以使用Hugging Face模型名，也可以将`model_name_or_path`改成本地模型目录。生产评测不能使用`hash_test_only`，该Provider仅供单元测试。

## 3. 配置GaussVector

通过环境变量传递连接信息，避免把密码写入配置文件：

```bash
export GAUSSVECTOR_DSN='host=127.0.0.1 port=5432 dbname=oag user=oag password=***'
```

复制配置并按环境调整：

```bash
cp tests/oag_vector_eval.example.json tests/oag_vector_eval.local.json
```

工具会创建以下测试表：

```sql
CREATE TABLE IF NOT EXISTS public.oag_vector_eval (
  run_id VARCHAR(64) NOT NULL,
  variant VARCHAR(64) NOT NULL,
  entity_type VARCHAR(32) NOT NULL,
  entity_key VARCHAR(2048) NOT NULL,
  group_key VARCHAR(1024),
  vector_role VARCHAR(64) NOT NULL,
  segment_no INTEGER NOT NULL,
  input_text TEXT NOT NULL,
  embedding FLOATVECTOR(1024) NOT NULL
);
```

默认创建余弦IVF索引：

```sql
CREATE INDEX oag_vector_eval_cosine_idx
ON public.oag_vector_eval
USING gsivfflat (embedding cosine)
WITH (ivf_nlist=<4 * sqrt(N)>);
```

配置为`"ivf_nlist": "auto"`时，工具按照方案文档建议使用`ceil(4 * sqrt(N))`。不同GaussDB版本的索引DDL如果存在差异，可把`create_index`设为`false`，由DBA提前创建索引；检索仍使用官方余弦距离操作符`<+>`。

## 4. 标注测试问题

`oag_vector_eval_queries.csv`字段：

|字段|说明|
|---|---|
|`query_id`|问题唯一编号|
|`question`|原始问题|
|`expected_entity_keys`|正确实体Key；多答案用分号分隔|
|`semantic_units`|完整语义短语；多个短语用`|`分隔|
|`category`|查询类型，如seed_property、enum_value、hard_negative|
|`language`|zh、en、mixed等|

实体Key格式：

```text
种子节点：seed|{id}
元数据元素：metadata|{propertyId}|{objectTypeId}|{value}
实例元素：instance|{propertyid}|{objectTypeId}|{value}
```

自动生成的问题来自名称、同义词等已知字段，只适合验证管线和建立弱监督基线。最终方案评判应使用实际业务问题和专家标注答案。

## 5. 运行

GaussVector正式评测：

```bash
python tests/oag_vector_eval.py \
  --config tests/oag_vector_eval.local.json
```

无数据库管线自测：

```bash
python tests/oag_vector_eval.py \
  --config tests/oag_vector_eval.example.json \
  --backend memory \
  --embedding-provider hash_test_only \
  --output-dir tests/oag_vector_eval_output
```

运行单元测试：

```bash
pytest -q tests/test_oag_vector_eval_tool.py
```

## 6. 输出

|文件|内容|
|---|---|
|`summary.csv`|各向量方案×查询策略的核心指标|
|`query_results.csv`|逐问题排名、相似度、Margin和Top10结果|
|`index_manifest.csv`|向量行数、实体数、文本长度和索引成本|
|`data_quality.json`|空值、重复Key和跳过记录统计|
|`summary.md`|可直接评审的对比表|
|`run.json`|本次运行标识和输出目录|

核心指标包括：

```text
Hit@1/3/5/10
Recall@1/3/5/10
Precision@1/3/5/10
NDCG@1/3/5/10
MRR
正确实体平均相似度
最佳错误实体平均相似度
Similarity Margin
P50/P95检索延迟
向量行数及文本长度
```

首选方案应同时满足：召回与MRR提升、Similarity Margin为正、端到端标注问题准确率不下降，并且P95延迟和向量行数增长在可接受范围内。

## 7. 当前工作簿数据质量提示

当前文件中：

- 种子节点数据行1119条；
- 元数据元素数据行2927条；
- 实例元素定义行136条，但`value`全部为空，正式评测时会跳过并写入`data_quality.json`；
- 种子节点`display_*`全部为空；
- 元数据元素`objectTypeId`全部为空；
- 元数据元素存在1条重复组合Key，加载时保留第一条并记录质量指标。

因此当前对比结果主要反映种子节点与元数据元素。实例元素必须补充真实去重列值后再参与最终方案评判。
