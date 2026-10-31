
---

> 版本：xxx
> 日期：xxx
> 文档定位：xxx
> 设计范围：xxx

---

## 文档结构

1.xxx

---

# 1. 设计目标、术语与总体架构

---

## 1.0 核心设计

---

### 1.1 设计目标

xxx

### 1.2 术语统一

| 术语 | 定义 |
|---|---|


### 1.3 业务背景与目标

CBS 涉及面向运营商人员的问账、集团客户问账，以及面向经营、销售、运营、运维人员的问计、问因与辅助决策。例如：查询预付费账户数量、汇总可用优惠余额、分析套餐月活 TOP3 及原因、回答账单风险和运营建议等。问计智能体侧重 CXO 客户体验、CMO 套餐市场表现、CFO 应收账款风险等决策分析场景，业务IRB成效目标准确率90%，端到端时长5min。

**CBS 软件场景本体模型**：对象类型：144，属性总数：2896，关系总数：370，内部划分11个域，当前业务侧还在优化本体模型。
模型参考：[CBS 场景的本体模型](https://clouddragon.huawei.com/cloudmodeling/myspace/diagram?diagramId=f46394eae0ec49d8a4693ebd93f0665c)；

![CBS场景的本体模型](https://cloudmodelingapi.tools.huawei.com/cloudmodelingdrawiosvr/d/1aa8934bdd27478cb45c4f5b06237c77?t=1792382890116)

### 1.4 需求范围与需求清单

TODO：整理成表格

|模块|关键能力分类|功能说明|工作量|
|OMS|本体加密|本体模型加密，多实例，参数拆分|0.5|
|DFx|OMS分域查询接口和本体定义接口，建立接口规范，避免实时查询，需要业务agent缓存处理，同时OMS接口内部缓存加速|0.2|
|DFx|支持多实例水平扩展，负载分担；|0.1|
|DFx|补充故障快速恢复指导书|0.5|
|DFx|安装场景包参数分层分级|0.1|
|OAG|接口统一|本体检索能力模块，服务场景和软件场景合二为一，已经串讲；默认：枚举索引不入库，子图属性的枚举全量返回|0.1|
|接口统一|本体开放skill V1切换为V2，V1标记为deprecated；|0.3|
|DFx|本体模型App安装时OMS调用OAG接口自动建索引，刷新内存图|0.5|
|DFx|支持多实例水平扩展，内存图同步刷新，接口调用负载分担；|0.1|
|DFx|安装场景包参数分层分级：组网级别的参数放置在场景包，系统级别参数收编到配置中心，任务级别参数放置在接口参数中，和服务底座统一配置|0.5|
|DFx|补充故障快速恢复指导书|0.5|
|性能|多实例性能，首次全量同步性能优化单表1000W（100W用户）,增量10W，实例数据语义索引入库性能规格和资源评估，包括embedding和向量库资源评估；结合DataSync和Spark联调（如下3项）；|1|
|性能|多实例性能，实例数据语义索引检索性能规格和资源评估，单实例3s 10QPS，水平扩展|1|
|性能|本体定义索引入库，根据参数控制，向量表全量比对，增量embedding，提升创建索引效率|0.5|
|性能|实例数据语义索引向量库rebuildindex LVQ索引前置到建表阶段，copy完成无需重建索引；copy批次大小调优（DCC参数）|0.2|
|性能|【联调】语义索引删除接口，Delete操作联调|0.1|
|性能|增量incremental接口在向量库中进行增量比对，新来的记录在原表不存在时，再向量化插入|0.5|
|性能和准确率|【预研】只入opensearch，不入向量，支持建模时语义字段配置，只入倒排索引，配合OMS建模|0.5|
|本体加密|【安全】向量表和opensearch去除名称和描述，只保留id，入库和检索逻辑做适配修改；根据name查id逻辑，改为从内存图或者nebulaGraph查询；|0.5|
|本体加密|后台日志子图明文打印，前台页面子图明文屏蔽，通过堆栈参数控制|0.2|



# 2. 详细设计与实现

TODO：按照关键能力进行分章节进行设计，中间相似类别的章节可以适当合并




参数列表：
```

一、系统组网参数（场景包）
控制内存图，nebulaGraph图数据库依赖
onto_encrypt: "0"
oag:
  cache.type: ${CACHE_TYPE}

二、租户级别参数（DCC）
# 语义检索接入控制配置（subgraphSemanticSearchV2，信号量在 transport 线程就地限流）
semantic-search:
  # 最大并发数（同时在跑的请求数上限）
  max-pool-size: 25
  # 等待队列容量（排队请求数上限，满则立即拒绝返回503）
  queue-capacity: 50
  # 排队等待并发许可的超时时间（秒），超时按限流返回503
  timeout-seconds: 300
  
include-all-properties: true

include-keys: false

# 连通子图路径/子图查询方向与边类型过滤开关：
# true  = 不区分方向（正向反向混合，仅需连通），且只取 defines_relation / has_property 边
# false = 历史兼容逻辑（默认，任意/单方向，不计边类型）
subgraph:
  undirected-filter: false


# 相似度定义 0 - 1的小数
ontology-object-similarity-threshold: -1
instance-similarity-threshold: -1

# top K
instance-topk: -1
rrf-topk: -1

# 链接开关
# 是否做对象链接（object 召回），默认 false
enable-object-linking: false
# 是否做属性链接（property 召回），默认 true；软件场景下置为 false（属性已在外部对齐）
enable-property-linking: false
# 是否做属性值链接（enum/instance 值召回），默认 false；软件场景下置为 true
enable-property-value-linking: true

embedding并发数：embedding-thread-pool-size
```