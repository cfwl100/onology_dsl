# 《OAC 功能设计说明书》

## 1. 文档概述

### 1.1 编写目的

说明本文档用于定义 OAC（Ontology Access Center / Service）的功能边界、系统模块、核心流程和关键数据结构，为研发、测试、架构评审和后续迭代提供依据。

### 1.2 适用范围

说明本文档覆盖：

- OQL DSL 请求接入
- 查询编译
- 执行调度
- 多源适配
- 结果装配
- MCP Tool 集成
- Python OSDK
- 扩展能力机制

不覆盖：

- 具体数据库建模细节
- 具体业务 schema 定义
- 底层数据库部署方案

### 1.3 术语与缩略语

建议统一定义：

- OQL
- OAC
- schemaRef
- identity source
- primary source
- logical plan
- physical DAG
- pushdown
- degraded
- sourceQuery
- MCP Tool
- OSDK

### 1.4 参考文档

- 《本体对象操作语言（OQL）DSL 规范》
- 本体 schema 与映射规范
- MCP Tool 接入规范
- yacht / graph proxy 接口文档
- 统一错误码规范

------

## 2. 系统建设目标与设计原则

### 2.1 建设目标

描述 OAC 的总体目标：

- 面向本体对象模型的统一访问入口
- 支持多数据源透明访问
- 支持对象查询、聚合、关系查询和写操作
- 支持逻辑计划与物理计划解耦
- 支持 AI / Agent / MCP 调用
- 支持扩展能力注入

### 2.2 设计原则

建议写入：

- 逻辑与物理解耦
- 单一 canonical OQL 输入
- 对象驱动而非表驱动
- 优先单源下推
- 跨源谨慎编排
- 安全优先
- 扩展可控
- 可观测、可审计

### 2.3 支持边界

明确：

- 支持单对象跨源拼装
- 支持同库 JOIN
- 支持图关系遍历
- 支持 sourceQuery 中间结果集
- 限制超大跨源全量 JOIN
- 限制未治理的原生 SQL 注入
- 限制跨源强一致分布式事务

------

下面我直接按**正式功能设计说明书正文**的风格，先写：

- **第 3 章：总体架构设计**
- **第 4 章：功能模块设计**
- **第 6 章：关键流程设计**
- **第 5 章：核心数据结构设计**
- **第 11 章：时序图建议**

------

# 3. 总体架构设计

## 3.1 设计目标

OAC（Ontology Access Center / Service）是面向本体对象模型的统一访问与执行中枢，负责接收符合 OQL DSL 规范的对象操作请求，并完成从逻辑对象操作到物理访问语句的编译、调度、执行与结果装配。

OAC 的总体设计目标如下：

1. **统一对象操作入口**
   对外提供统一的对象操作服务接口，以 `operation` 字段区分具体语义，屏蔽底层数据源、执行方言和物理路由差异。
2. **逻辑与物理解耦**
   OQL 仅表达逻辑对象、属性、关系和条件，不直接暴露物理表、物理字段或数据库方言；物理绑定、查询优化和执行由 OAC 统一处理。
3. **多数据源透明访问**
   支持对象属性跨数据源映射、多对象同库 / 跨库访问、关系型与图数据库联合访问，以及外部服务型数据源访问。
4. **可编译、可优化、可编排**
   采用“解析 → 绑定 → 逻辑计划 → 优化 → 物理 DAG → 调度执行”的模式，支持条件下推、聚合下推、sourceQuery 中间结果集、同源合并和跨源拆分。
5. **面向 AI / Agent 可直接调用**
   兼容 canonical OQL JSON 输入，可作为 MCP Tool、OSDK 和 Agent 执行后端，支持 validate / explain / execute 等能力。
6. **支持企业级治理与扩展**
   支持统一错误码、trace、审计、权限校验和扩展能力注入，以满足中台级服务的治理要求。

------

## 3.2 架构定位

OAC 在整体系统中的定位如下：

- **上游调用方**：业务服务、工作流引擎、LLM / Agent、MCP Tool、Python OSDK
- **中间职责**：OQL 接入、语义校验、查询编译、执行调度、结果装配、治理
- **下游执行依赖**：
    - yacht（SQL 执行代理）
    - graph proxy（nGQL 执行代理）
    - 第三方 REST / RPC 服务
    - schema / mapping registry
    - 配置中心、日志与 trace 平台、权限系统

OAC 不直接承担底层数据库的连接治理与执行驱动实现，而是通过统一适配器调用外部执行代理服务完成物理访问。

------

## 3.3 总体分层架构

OAC 采用分层架构设计，整体分为五层：

1. **接入层（Access Layer）**
2. **语义与元数据层（Semantic & Metadata Layer）**
3. **编译与优化层（Compiler & Optimizer Layer）**
4. **执行与调度层（Execution & Scheduling Layer）**
5. **结果与治理层（Result & Governance Layer）**

整体分层关系如下：

```text
上游调用方（应用 / Agent / MCP / OSDK）
                │
                ▼
          [接入层 Access Layer]
                │
                ▼
   [语义与元数据层 Semantic & Metadata]
                │
                ▼
 [编译与优化层 Compiler & Optimizer Layer]
                │
                ▼
 [执行与调度层 Execution & Scheduling Layer]
                │
                ▼
 [结果与治理层 Result / Trace / Audit Layer]
                │
                ▼
 下游执行后端（yacht / graph proxy / REST / RPC）
```

------

## 3.4 分层职责说明

### 3.4.1 接入层

接入层负责承接所有对象操作请求，并构造统一的请求上下文。
其核心职责是统一入口管理，而不是业务语义解释。

主要职责包括：

- 接收 OQL 请求
- 识别 `operation`
- 构造 requestId、traceId、调用上下文
- 进行请求模式分发（validate / explain / execute）
- 调用后续模块并返回统一响应

------

### 3.4.2 语义与元数据层

语义与元数据层负责为 OQL 解析、校验与编译提供 schema、映射和能力元数据支持。

主要职责包括：

- schemaRef 解析与加载
- 对象、字段、关系定义查询
- identity source / primary source 解析
- 字段到物理源、表、列的映射查询
- 数据源执行能力矩阵查询
- 扩展能力元数据查询

该层是 OAC 的语义基础层，不直接参与请求执行。

------

### 3.4.3 编译与优化层

编译与优化层负责将已通过校验的 OQL 请求编译为可执行的逻辑计划与物理执行 DAG。

主要职责包括：

- OQL AST 绑定
- 逻辑算子图生成
- 条件下推与聚合下推
- source 分组与物理拆分
- sourceQuery 子计划规划
- Join / Traverse / Mutation 规划
- 物理执行 DAG 生成

该层是 OAC 的核心计算层。

------

### 3.4.4 执行与调度层

执行与调度层负责基于物理 DAG 编排和执行各物理子计划。

主要职责包括：

- DAG 拓扑调度
- 节点依赖管理
- 节点并发执行
- 外部执行代理调用
- 重试、超时、限流与降级
- BATCH 原子性控制
- 写操作失败补偿控制

------

### 3.4.5 结果与治理层

结果与治理层负责将底层物理执行结果恢复为 OQL 逻辑结果，并输出统一治理信息。

主要职责包括：

- 多源结果 merge
- 对象级结果装配
- 聚合结果装配
- alias 结果恢复
- metadata / trace 构建
- 错误对象构建
- 审计日志与执行归因记录

------

## 3.5 核心架构原则

### 3.5.1 统一入口，内部按 operation 分发

OAC 对外仅提供统一对象操作入口，不按 operation 拆分为多个对外服务接口。
operation 的区分仅在服务内部进行。

### 3.5.2 先编译后执行

OAC 必须采用“先校验、后编译、再执行”的模式，不允许将 OQL 直接字符串转换为 SQL / nGQL 后立即执行。

### 3.5.3 `sourceQuery` 视为逻辑中间结果集

`sourceQuery` 的语义不局限于 SQL 子查询，而应视为 OAC 内部可执行的中间结果集节点。

### 3.5.4 多源访问采用编排模式

对于跨源查询，OAC 采用逻辑计划拆分与物理 DAG 编排模式，不强制要求所有场景都映射为单条物理语句。

### 3.5.5 扩展能力必须受治理控制

标准 OQL 无法覆盖的场景，允许通过扩展能力或插件机制实现，但必须受白名单、审计和权限策略约束。

------

## 3.6 外部依赖与接口边界

### 3.6.1 外部元数据依赖

- schema registry
- mapping registry
- source capability registry
- extension registry

### 3.6.2 外部执行依赖

- yacht
- graph proxy
- 第三方 REST / RPC 服务

### 3.6.3 平台治理依赖

- 认证与鉴权系统
- 配置中心
- 日志与 trace 平台
- 审计平台
- MCP Tool Center

------

## 3.7 总体数据流

一个标准 OQL 请求在 OAC 中的处理过程如下：

1. 接入层接收请求并构造上下文
2. 校验模块完成结构、引用、语义校验
3. 加载 schemaRef 对应元数据
4. 编译器绑定对象、字段、关系
5. 生成逻辑计划并进行优化
6. 生成物理执行 DAG
7. 调度器执行 DAG 节点
8. 适配器调用实际执行服务
9. 汇总各节点结果
10. 装配逻辑响应并返回

------

## 3.8 模块边界

### 3.8.1 OAC 负责的内容

- OQL 接入
- 校验
- schema 绑定
- 编译
- 优化
- 调度
- 结果装配
- 治理信息输出

### 3.8.2 OAC 不负责的内容

- 底层数据库连接池与驱动管理
- 物理表建模
- 本体 schema 建模工具本身
- yacht / graph proxy 的底层执行实现
- 业务系统侧的复杂事务编排

### 3.8.3 OAC 与外部组件的边界

- OAC 面向逻辑对象
- 外部执行代理面向物理语句
- schema / mapping 中心负责元数据，不负责编译执行

------

## 3.9 风险点

1. **跨源编排复杂度高**
   多源 Join、图关系 + 关系属性、sourceQuery 嵌套都可能导致执行计划急剧复杂化。
2. **元数据治理成本高**
   schema、字段映射、关系映射不准确会直接影响编译正确性。
3. **执行代理能力差异大**
   各 source 的 filter / aggregate / sort / graph traversal 能力不一致，需要严格能力建模。
4. **扩展能力可能破坏统一语义**
   若扩展机制失控，可能导致 OQL 规范被绕过，损害系统稳定性。
5. **多源写一致性难以保证**
   UPDATE / UPSERT / BATCH 在多源场景下存在主写、补偿和幂等等复杂问题。

------

## 3.10 实现建议

1. **优先落地“单源查询 + 同库 Join + 图关系回查”主链路**
   跨源复杂编排能力建议分阶段演进。
2. **将 schema / mapping registry 设计为独立能力**
   不建议在 OAC 内部硬编码对象与字段映射。
3. **逻辑计划与物理 DAG 必须分离**
   便于 explain、优化、调试和未来 cost-based 优化器扩展。
4. **统一构建 explain 能力**
   从一开始支持 logical explain 和 physical explain，便于排障和运维。
5. **优先保证 canonical OQL 的严格输入**
   不建议在 OAC 中做过多输入容错，以免破坏上游规范。

------

# 4. 功能模块设计

## 4.1 概述

本章定义 OAC 的核心功能模块。
模块划分遵循“高内聚、低耦合、职责单一”的原则，确保各模块边界清晰、可独立开发、可独立测试、可独立替换。

OAC 共划分为以下核心模块：

1. 对象操作统一接入模块
2. Schema 与映射管理模块
3. OQL 解析与校验模块
4. 查询编译与优化模块
5. 执行计划调度模块
6. 外部执行适配器模块
7. 结果装配与统一响应模块
8. MCP Tool Center 集成模块
9. OSDK（Python SDK）模块
10. 扩展能力与插件模块

------

## 4.2 对象操作统一接入模块

### 4.2.1 模块职责

对象操作统一接入模块是 OAC 的统一入口模块，负责接收所有对象操作请求，并向后续模块传递标准化的请求上下文。

### 4.2.2 功能范围

- 接收 OQL JSON 请求
- 构造 requestId、traceId、authContext
- 支持 validate / explain / execute 三类请求模式
- 根据 `operation` 进行内部流程分发
- 输出统一响应结构

### 4.2.3 输入输出

**输入**：

- OQL 请求体
- 调用方身份信息
- 可选执行参数（timeout、dryRun 等）

**输出**：

- 校验结果
- explain 结果
- 执行结果
- 统一错误对象

### 4.2.4 设计约束

- 统一接入层不承担业务语义编排职责
- 不直接执行 SQL / nGQL
- 不直接访问 schema 配置细节
- 不负责多源结果装配

### 4.2.5 关键接口建议

建议提供以下接口：

- `executeOql`
- `validateOql`
- `explainOql`
- `compileOql`

### 4.2.6 模块边界

**负责**：

- 接入与响应
- 请求上下文构建
- 模式分发

**不负责**：

- schema 绑定
- 计划生成
- 物理执行
- 结果装配

### 4.2.7 风险点

- 接入层若承担过多逻辑，会导致后续模块边界模糊
- validate / explain / execute 混合实现不清晰，容易造成接口膨胀

### 4.2.8 实现建议

- 接入层尽量薄
- 使用统一 RequestContext
- 将 validate / explain / execute 视为同一流程链路上的不同终止点

------

## 4.3 Schema 与映射管理模块

### 4.3.1 模块职责

Schema 与映射管理模块负责维护 OAC 编译和执行所依赖的对象、字段、关系和物理映射元数据。

### 4.3.2 功能范围

- 加载 schemaRef
- 查询对象类型定义
- 查询字段定义
- 查询关系定义
- 查询字段物理映射
- 查询关系物理映射
- 查询 source capability
- 查询扩展能力注册信息

### 4.3.3 输入输出

**输入**：

- schemaRef
- objectType
- field
- relationshipType

**输出**：

- schema snapshot
- field mapping
- relationship mapping
- source capability metadata

### 4.3.4 设计约束

- 映射元数据应与 OAC 编译器解耦
- schema 应支持版本化
- 支持缓存与动态刷新

### 4.3.5 模块边界

**负责**：

- 提供只读元数据能力
- 提供 schema 与 mapping 绑定依据

**不负责**：

- 直接校验 OQL
- 直接生成计划
- 直接执行物理访问

### 4.3.6 风险点

- schema 变更与缓存不一致
- 字段映射缺失或错误导致编译结果不稳定
- source capability 元数据不准确会直接影响优化正确性

### 4.3.7 实现建议

- 使用独立 registry 服务或本地缓存 + 配置订阅模式
- 对关键元数据建立版本号和生效时间
- capability 建议显式枚举，不要依赖隐式推断

------

## 4.4 OQL 解析与校验模块

### 4.4.1 模块职责

负责将 OQL JSON 解析为 AST，并完成结构校验、引用校验、语义校验和治理校验。

### 4.4.2 功能范围

- JSON → AST
- 顶层字段校验
- alias 唯一性校验
- operation 与专用块匹配校验
- sourceQuery 绑定校验
- mutation 结构校验
- schema 权限校验

### 4.4.3 输入输出

**输入**：

- OQL JSON
- schema metadata
- auth context

**输出**：

- ValidatedAst
- ValidationError 列表

### 4.4.4 模块边界

**负责**：

- OQL 合法性确认
- 引用一致性确认
- 规范约束检查

**不负责**：

- 逻辑计划优化
- source capability 决策
- 物理语句生成

### 4.4.5 风险点

- 校验规则与 OQL 规范不同步
- alias / returns / orders 规则实现分散
- 严格模式和未来兼容模式边界不清晰

### 4.4.6 实现建议

- 校验规则应尽量与 OQL 规范一一对应
- 建议分阶段校验：结构 → 引用 → 语义 → 治理
- 建议错误码与 path 定位统一输出

------

## 4.5 查询编译与优化模块

### 4.5.1 模块职责

负责将 `ValidatedAst` 编译为逻辑执行计划，并生成优化后的物理执行 DAG。

### 4.5.2 功能范围

- schema 绑定
- 逻辑算子生成
- source 分组
- pushdown 优化
- same-table collapse 判定
- join 规划
- graph traversal 规划
- sourceQuery 规划
- mutation 规划
- 物理 DAG 输出

### 4.5.3 输入输出

**输入**：

- ValidatedAst
- schema metadata
- mapping metadata
- source capability metadata

**输出**：

- LogicalPlan
- OptimizedPlan
- PhysicalDag

### 4.5.4 模块边界

**负责**：

- 逻辑计划建模
- 物理拆分
- 执行顺序规划
- explain 计划输出

**不负责**：

- 实际执行节点调度
- 底层 SQL/nGQL 发起
- 最终结果装配

### 4.5.5 风险点

- 编译器职责过重，容易膨胀成“万能模块”
- 规则优化器缺乏边界，可能引入难以诊断的隐式行为
- same-table collapse / cross-source join 逻辑容易出现语义错误

### 4.5.6 实现建议

- 明确分层：Binder / Logical Planner / Optimizer / Physical Planner
- 所有优化规则可 explain、可关闭、可灰度
- 对关键规划结果建议输出 explain trace

------

## 4.6 执行计划调度模块

### 4.6.1 模块职责

负责执行物理 DAG，控制节点依赖、并发、重试、超时和失败处理。

### 4.6.2 功能范围

- DAG 拓扑排序
- 节点状态管理
- 节点依赖解析
- 并发提交
- 超时与重试
- degraded 执行
- BATCH 原子性控制
- 写操作失败补偿协调

### 4.6.3 输入输出

**输入**：

- PhysicalDag
- runtime policy
- RequestContext

**输出**：

- 节点执行结果集
- DAG 执行状态
- 节点级 trace 信息

### 4.6.4 模块边界

**负责**：

- DAG 级调度与生命周期管理
- 执行失败控制
- 中间结果集管理

**不负责**：

- 语句翻译
- schema 绑定
- 对象结果装配

### 4.6.5 风险点

- 调度器若和适配器耦合过深，会导致扩展困难
- 跨源重试策略处理不当，可能破坏幂等性
- BATCH 的 atomic 语义若无清晰实现边界，容易与底层能力不匹配

### 4.6.6 实现建议

- 调度器应只面向统一 ExecutionNode / ExecutionResult 模型
- 节点状态建议显式维护
- 对长耗时和复杂 DAG，预留异步执行扩展点

------

## 4.7 外部执行适配器模块

### 4.7.1 模块职责

负责将物理执行节点转换为具体外部执行请求，并标准化返回结果。

### 4.7.2 功能范围

- SQL Adapter 对接 yacht
- Graph Adapter 对接 graph proxy
- Service Adapter 对接 REST / RPC
- 参数绑定
- 错误标准化
- source trace 记录

### 4.7.3 输入输出

**输入**：

- ExecutionNode
- 执行参数
- source metadata

**输出**：

- ExecutionResult
- 标准化错误对象
- source trace

### 4.7.4 模块边界

**负责**：

- 物理请求翻译
- 外部服务调用
- 结果标准化

**不负责**：

- 逻辑计划生成
- DAG 调度
- 逻辑结果装配

### 4.7.5 风险点

- 不同后端错误语义差异大
- graph / SQL / service 执行能力模型不一致
- 大批量 id 回查时可能产生性能瓶颈

### 4.7.6 实现建议

- 统一适配器接口
- 使用统一 SourceError / SourceTrace 模型
- 对批量回查场景做批大小控制与分页策略

------

## 4.8 结果装配与统一响应模块

### 4.8.1 模块职责

负责将各物理节点结果恢复为 OQL 逻辑响应。

### 4.8.2 功能范围

- 多源结果 merge
- alias 结果映射
- 对象字段装配
- 聚合结果装配
- metadata 构建
- trace 构建
- 错误响应构建

### 4.8.3 输入输出

**输入**：

- ExecutionResult 列表
- LogicalPlan / alias 绑定信息
- RequestContext

**输出**：

- OqlResponse

### 4.8.4 模块边界

**负责**：

- 逻辑结果恢复
- 统一响应输出

**不负责**：

- 物理执行
- schema 绑定
- 编译优化

### 4.8.5 风险点

- 多源 merge 规则复杂，容易出现主键对齐错误
- 聚合结果和对象结果共用装配逻辑时容易混淆
- degraded 场景下的结果完整性需要明确定义

### 4.8.6 实现建议

- 对象结果、聚合结果、关系结果建议分装配器实现
- 响应 metadata 必须统一生成，不要分散在各模块拼装
- 明确 degraded 和 partial result 的输出语义

------

## 4.9 MCP Tool Center 集成模块

### 4.9.1 模块职责

负责将 OAC 能力注册为 MCP Tool，并向 LLM / Agent 暴露统一工具接口。

### 4.9.2 功能范围

- Tool 元数据注册
- Tool 参数 schema 定义
- Tool 调用桥接
- Tool 权限控制
- Tool 版本管理

### 4.9.3 模块边界

**负责**：

- OAC 与 MCP Tool Center 对接
- OQL 校验 / explain / execute 能力暴露

**不负责**：

- OQL 编译执行本身
- LLM prompt 管理
- agent 路由策略

### 4.9.4 风险点

- Tool schema 与 OQL 规范不同步
- tool 级权限与 OAC 权限体系不一致
- LLM 调用工具时输入质量不稳定

### 4.9.5 实现建议

- 优先暴露 `validate / explain / execute`
- 工具说明尽量简洁且结构化
- 可与 OQL router skill 配合使用

------

## 4.10 OSDK（Python SDK）模块

### 4.10.1 模块职责

为开发者提供 Python 形式的 OQL 构造与 OAC 调用封装。

### 4.10.2 功能范围

- DSL 链式 Builder
- DTO / model 定义
- validate / explain / execute client
- schema helper
- 异常封装与重试封装

### 4.10.3 模块边界

**负责**：

- Python 本地 DSL 拼装
- OAC API 调用封装
- Python 侧结果模型封装

**不负责**：

- OAC 服务内部编译执行
- schema 元数据治理
- 物理查询语句生成

### 4.10.4 风险点

- Builder 若不能严格输出 canonical OQL，会引入双重规范
- SDK 与服务端版本不一致时容易产生兼容问题

### 4.10.5 实现建议

- SDK 输出必须严格对齐 canonical OQL
- 建议为各 operation 提供显式 builder
- 建议内置 schema 感知能力和静态校验辅助

------

## 4.11 扩展能力与插件模块

### 4.11.1 模块职责

用于支持标准 OQL 语法之外的可控扩展能力。

### 4.11.2 功能范围

- `extensions` 解析
- 扩展能力注册
- 自定义逻辑算子注入
- 自定义执行节点注入
- 特殊查询能力接入

### 4.11.3 模块边界

**负责**：

- 扩展能力解析与治理
- 插件能力接入

**不负责**：

- 无治理的原生语句注入
- 绕过 OQL 规范的执行路径

### 4.11.4 风险点

- 扩展机制滥用后会破坏规范边界
- 插件能力与标准能力混用后，调试和 explain 复杂度上升

### 4.11.5 实现建议

- 所有扩展能力必须白名单化
- 扩展能力必须支持 explain 和审计
- 建议区分 declarative extension 与 operator plugin 两种类型

------

## 4.12 模块边界

### 4.12.1 明确模块拆分原则

- 接入层负责接入，不负责语义
- 校验层负责合法性，不负责优化
- 编译层负责计划生成，不负责执行
- 调度层负责执行，不负责对象装配
- 装配层负责逻辑结果恢复，不负责物理访问

### 4.12.2 明确禁止的职责穿透

不建议出现以下情况：

- 接入层直接访问 schema registry 并做业务解释
- 适配器自行决定查询优化策略
- 调度器直接拼装最终响应
- 扩展模块绕过统一校验链路

------

## 4.13 风险点

1. 模块间边界如果不严格，容易演变为“巨石式编译器”
2. 编译与调度耦合过深，会导致 explain 和可测试性下降
3. 多源结果装配逻辑不集中，容易造成响应结构不一致
4. 扩展能力若缺乏治理，会侵蚀标准 OQL 语义边界
5. OSDK 与服务端规范不同步，会造成双重语法源

------

## 4.14 实现建议

1. 优先保证模块边界清晰，再追求功能覆盖广度
2. 统一使用核心模型：`ValidatedAst`、`LogicalPlan`、`PhysicalDag`、`ExecutionNode`、`OqlResponse`
3. 对每个模块建立独立的单元测试和契约测试
4. 关键路径全部支持 explain 和 trace
5. 先实现主链路，再灰度扩展复杂跨源与扩展能力

------



下面给出 **第 6 章《关键流程设计》** 的**正式成稿版**。
风格与前面的第 3、4 章保持一致，并按你要求补齐：

- 前置条件
- 处理步骤
- 异常分支
- 输出结果
- 风险点
- 实现建议

你可以直接纳入《OAC 功能设计说明书》。

------

# 6. 关键流程设计

## 6.1 概述

本章描述 OAC 的关键业务处理流程。
关键流程设计遵循以下原则：

1. **统一入口、分层处理**
   所有流程均从统一接入层进入，依次经过校验、编译、调度、执行和结果装配。
2. **先校验、后执行**
   未通过结构校验、引用校验或语义校验的请求不得进入执行阶段。
3. **逻辑计划先于物理执行**
   所有请求在执行前必须完成逻辑计划构建和物理 DAG 生成。
4. **异常分层处理**
   结构错误、引用错误、语义错误、执行错误和内部错误应在对应阶段就地返回，不应跨阶段混淆。
5. **治理信息全链路保留**
   关键流程中的 requestId、traceId、logical plan、physical DAG、source trace 和 degraded 状态应全程保留。

本章重点说明以下流程：

- 查询执行主流程
- `sourceQuery` 执行流程
- 多源查询执行流程
- 图关系查询执行流程
- 写操作执行流程
- BATCH 执行流程

------

## 6.2 查询执行主流程

### 6.2.1 流程目标

查询执行主流程用于处理标准查询类请求，包括：

- `QUERY`
- `AGGREGATE`
- `ASSOCIATION_QUERY`
- `LINK_QUERY`

该流程覆盖从请求接入到结果返回的完整链路，是 OAC 的基础主流程。

------

### 6.2.2 前置条件

1. 调用方已获得 OAC 服务访问权限。
2. 请求体为合法 JSON。
3. 请求中已包含 `version`、`schemaRef`、`operation` 等基础字段。
4. `schemaRef` 可在 schema / mapping registry 中正确解析。
5. OAC 的外部依赖（如 registry、执行代理）处于可用状态。

------

### 6.2.3 处理步骤

#### 步骤 1：请求接入

接入层接收查询请求，生成本次请求的：

- `requestId`
- `traceId`
- 调用方上下文
- 超时、dryRun、returnMetadata 等执行上下文

#### 步骤 2：结构解析与校验

解析模块将请求 JSON 转换为 AST，并完成：

- 顶层字段校验
- 字段类型校验
- 枚举值校验
- 空对象 / 空数组 / null 校验

#### 步骤 3：引用与语义校验

继续完成：

- alias 唯一性校验
- `ref` / `from` / `to` / `sourceRef` / `targetRef` 合法性校验
- `operation` 与专用块匹配校验
- `returns` / `orders` / `sourceQuery` 语义校验

#### 步骤 4：加载 schema 与映射元数据

根据 `schemaRef` 加载：

- 对象定义
- 字段定义
- 关系定义
- 字段映射
- 关系映射
- source capability

#### 步骤 5：生成逻辑计划

编译器将 `ValidatedAst` 转换为 `LogicalPlan`，并表达以下语义：

- 对象扫描
- 过滤条件
- 返回投影
- 排序与限制
- 聚合
- 关系遍历
- 中间结果集引用

#### 步骤 6：计划优化

优化器根据元数据和 source capability 进行规则优化，包括：

- filter pushdown
- aggregate pushdown
- projection pruning
- same-table collapse analysis
- source 分组与合并

#### 步骤 7：生成物理执行 DAG

将优化后的逻辑计划转换为 `PhysicalDag`，形成：

- 节点列表
- 节点依赖
- 各节点目标 source
- 各节点 payload

#### 步骤 8：DAG 调度执行

调度器按照依赖关系执行 DAG：

- 提交可执行节点
- 调用各执行适配器
- 收集中间结果
- 逐步完成全部节点执行

#### 步骤 9：结果装配

结果装配模块基于执行结果与逻辑别名信息：

- 合并多源结果
- 恢复 alias 结构
- 生成 `data`
- 生成 `metadata`
- 生成 `trace`

#### 步骤 10：响应返回

接入层输出标准响应结构：

- `success`
- `operation`
- `data`
- `metadata`
- `trace`
- `errors`

------

### 6.2.4 异常分支

#### 分支 A：结构校验失败

如出现缺失字段、类型错误、非法枚举值等，直接返回 `VALIDATION_ERROR`，不进入编译阶段。

#### 分支 B：引用校验失败

如 alias 未声明、`sourceQuery` 绑定非法等，直接返回 `REFERENCE_ERROR`。

#### 分支 C：语义校验失败

如 `QUERY` 使用了非法的 `returns.kind`，或 `LINK_QUERY` 缺少 `linkQuery`，直接返回 `SEMANTIC_ERROR`。

#### 分支 D：元数据加载失败

如 `schemaRef` 不存在或映射元数据不可用，返回 `INTERNAL_ERROR` 或 `SEMANTIC_ERROR`（依实现定义）。

#### 分支 E：执行阶段失败

如 yacht / graph proxy / 第三方服务调用失败，则返回 `EXECUTION_ERROR`。
若支持部分降级执行，则应在 `metadata.degraded = true` 中体现。

------

### 6.2.5 输出结果

成功时输出：

- `success = true`
- `operation`
- `data`
- `metadata`
- `trace`

失败时输出：

- `success = false`
- `operation`
- `errors`
- `trace`

------

### 6.2.6 风险点

1. 校验规则与规范不一致会导致错误请求进入执行链路。
2. 编译器逻辑复杂时，explain 能力不足会增加排障成本。
3. 多源结果装配过程中，主键对齐错误会导致结果错配。
4. source capability 不准确会导致错误下推。

------

### 6.2.7 实现建议

1. 主流程必须支持 `validate / explain / execute` 三种模式。
2. 建议在响应中保留 `logicalPlanId` 和 `physicalPlanId`，便于 trace。
3. 所有失败分支都应尽量输出准确 path 和错误类别。
4. explain 输出建议与执行链路共用同一套计划生成逻辑。

------

## 6.3 `sourceQuery` 执行流程

### 6.3.1 流程目标

`sourceQuery` 执行流程用于处理“先生成中间结果集，再由外层消费”的查询场景。
它适用于：

- 子集裁剪
- 聚合前过滤
- 聚合后再筛选
- 图查询前输入集缩小
- 跨源查询前主键集合预筛选

------

### 6.3.2 前置条件

1. 当前 `operation` 为查询类操作。
2. `sourceQuery[].outputAs` 在同层唯一。
3. 外层 `objects[].fromSource` 正确引用子查询输出。
4. `sourceQuery` 不引用外层 alias。
5. 嵌套深度符合规范约束。

------

### 6.3.3 处理步骤

#### 步骤 1：识别 sourceQuery 结构

编译器扫描当前 AST，识别所有 `sourceQuery` 节点。

#### 步骤 2：对子查询进行独立校验

每个 `sourceQuery` 子句作为独立查询单元完成：

- 结构校验
- 引用校验
- 语义校验

#### 步骤 3：构建子查询逻辑计划

每个 `sourceQuery` 生成独立 `LogicalPlan`，并与 `outputAs` 绑定。

#### 步骤 4：生成子查询物理 DAG

对子查询单独进行优化和物理计划生成。

#### 步骤 5：先执行子查询

调度器优先执行所有前置 `sourceQuery` 子计划，并将结果缓存为中间结果集。

#### 步骤 6：绑定外层对象

外层 `objects[].fromSource` 消费中间结果集，并在后续逻辑计划中将其视为输入数据源。

#### 步骤 7：执行外层查询

外层逻辑计划基于中间结果集继续编译与执行。

------

### 6.3.4 异常分支

#### 分支 A：`outputAs` 重复

返回 `REFERENCE_ERROR`，错误码建议为 `INVALID_SOURCE_REFERENCE` 或 `DUPLICATE_ALIAS`。

#### 分支 B：`fromSource` 引用不存在

返回 `REFERENCE_ERROR`。

#### 分支 C：子查询执行失败

外层查询不再执行，直接返回子查询失败结果。

#### 分支 D：中间结果集过大

若超出系统预设阈值，可触发降级、拒绝执行或落盘中间结果集（依实现策略）。

------

### 6.3.5 输出结果

- 成功：返回外层查询结果
- 失败：返回子查询或绑定阶段错误
- metadata 中建议补充 `usedSourceQuery = true`

------

### 6.3.6 风险点

1. `sourceQuery` 嵌套层数增加会显著提升计划复杂度。
2. 中间结果集过大可能导致内存压力或跨阶段数据传输开销过高。
3. 子查询和外层字段投影不一致时，容易产生外层字段引用错误。

------

### 6.3.7 实现建议

1. `sourceQuery` 结果建议统一抽象为中间结果集节点，而不是内联为语法级子查询。
2. 建议限制默认嵌套深度，并对中间结果集大小设置阈值。
3. 若支持 explain，应明确输出子查询计划与外层计划的依赖关系。

------

## 6.4 多源查询执行流程

### 6.4.1 流程目标

多源查询执行流程用于处理以下场景：

- 单对象跨源属性拼装
- 多对象跨源查询
- 关系查询后回查属性
- 同一逻辑对象字段位于不同 source

------

### 6.4.2 前置条件

1. schema / mapping registry 能正确给出字段到 source 的映射。
2. 已定义 identity source 或 primary source。
3. source capability 信息完整。
4. 需要跨源处理的字段与条件已通过编译器识别。

------

### 6.4.3 处理步骤

#### 步骤 1：字段与条件按 source 分组

编译器将：

- 过滤条件
- 返回字段
- 聚合字段
- 排序字段
  按可下推 source 进行分组。

#### 步骤 2：确定主执行源

根据 identity source / primary source / filter selectivity 等规则，选择一个主执行源用于优先缩小数据集。

#### 步骤 3：在主源下推过滤

优先在主源执行可下推条件，获取对象主键集合或较小结果集。

#### 步骤 4：构造其他源回查计划

对于其他 source 中的字段，按主键集合进行批量回查。

#### 步骤 5：中间层合并

在 OAC 中间层对不同 source 的结果按逻辑主键进行 merge 或 join。

#### 步骤 6：执行必要的补偿逻辑

如果排序、聚合或过滤无法完全下推，则在 OAC 中间层执行补偿处理。

#### 步骤 7：结果装配并返回

将合并后的结果还原为逻辑对象结果。

------

### 6.4.4 异常分支

#### 分支 A：主键集合缺失

如果对象缺少 identity key 或无法对齐跨源结果，则应返回语义错误或执行错误。

#### 分支 B：某个 source 回查失败

根据策略可选择：

- 全局失败
- 部分降级返回
- 标记 `degraded = true`

#### 分支 C：跨源结果集过大

当主源过滤后返回集合过大时，可触发限制、分页或拒绝执行。

------

### 6.4.5 输出结果

- 标准 OQL 响应
- 建议在 metadata 中增加：
    - `crossSource = true`
    - `degraded = true/false`
    - `sourceCount`

------

### 6.4.6 风险点

1. identity key 定义不清会导致 merge 错乱。
2. 主源选择不当会造成不必要的大结果集回查。
3. 跨源排序 / 聚合补偿可能带来性能问题。

------

### 6.4.7 实现建议

1. 明确对象的 identity source 和主键规则。
2. 优先“主源过滤 + 其他源回查”的模式。
3. 对高成本跨源场景设置结果集阈值和降级策略。
4. 对 explain 输出中明确展示每个字段来自哪个 source。

------

## 6.5 图关系查询执行流程

### 6.5.1 流程目标

图关系查询执行流程用于处理：

- `ASSOCIATION_QUERY`
- `LINK_QUERY`
- 图关系 + 关系库属性回查场景

------

### 6.5.2 前置条件

1. 关系类型已绑定到图库边或关系表。
2. 图执行代理可用。
3. 若属性不在图库中，则存在可回查的关系库映射。
4. 对象 id / vertex id 的绑定规则可用。

------

### 6.5.3 处理步骤

#### 步骤 1：识别关系查询类型

区分当前请求为：

- 多跳路径查询（`ASSOCIATION_QUERY`）
- 一跳关系查询（`LINK_QUERY`）

#### 步骤 2：生成图查询节点

根据 `relationships` 或 `linkQuery` 生成 nGQL 物理节点。

#### 步骤 3：执行图查询

通过 graph adapter 调用 graph proxy，获取：

- 路径上的对象 id
- 边结果
- 或最终目标对象 id 集合

#### 步骤 4：按需回查对象属性

若对象属性不在图库中，则按返回 id 到关系型数据源回查属性。

#### 步骤 5：组装路径 / 对象结果

根据逻辑 alias 和关系路径顺序，装配最终结果。

------

### 6.5.4 异常分支

#### 分支 A：关系映射不存在

返回 `SEMANTIC_ERROR` 或 `REFERENCE_ERROR`。

#### 分支 B：图查询成功但属性回查失败

根据策略可部分降级，或整体失败。

#### 分支 C：`mode = ONE` 结果不唯一

返回 `EXECUTION_ERROR`，错误码建议为 `NON_UNIQUE_RESULT` 或 `NO_RESULT`。

------

### 6.5.5 输出结果

- 标准 OQL 响应
- 关系路径查询建议在 trace 中记录：
    - graph query trace
    - 回查 source trace
    - path length

------

### 6.5.6 风险点

1. 图 ID 与关系库主键映射不一致会导致回查失败。
2. 图遍历结果过大时，属性回查会产生放大效应。
3. 路径装配逻辑复杂，易出现 alias 对应错误。

------

### 6.5.7 实现建议

1. 图查询只负责取 path / id，属性优先在关系库回查。
2. `LINK_QUERY` 应尽量保持为单跳简单场景。
3. 对高 fan-out 图查询设置限制或分页策略。

------

## 6.6 写操作执行流程

### 6.6.1 流程目标

写操作执行流程用于支持：

- `CREATE`
- `UPDATE`
- `DELETE`
- `UPSERT`

------

### 6.6.2 前置条件

1. 请求已通过结构、引用和语义校验。
2. 调用方具备对应写权限。
3. 已能确定主写源。
4. 对于 `UPSERT`，`matchBy` 对应的字段具备存在性判断能力。

------

### 6.6.3 处理步骤

### A. CREATE

1. 校验 `mutation.data.properties`
2. 绑定对象字段映射
3. 选择主写源
4. 生成写入节点
5. 执行写入
6. 如有扩展写源，则进行同步写入或异步补偿
7. 返回 `affectedCount`

------

### B. UPDATE

1. 解析 `conditions`
2. 执行目标对象定位
3. 根据 `scope` 校验匹配数量
4. 生成更新节点
5. 执行更新
6. 返回 `affectedCount`

------

### C. DELETE

1. 解析 `conditions`
2. 定位目标对象
3. 根据 `scope` 校验匹配数量
4. 检查删除策略
5. 执行删除
6. 返回 `affectedCount`

------

### D. UPSERT

1. 解析 `matchBy`
2. 在 identity source 进行存在性判断
3. 若存在则进入 UPDATE 分支
4. 若不存在则进入 CREATE 分支
5. 执行后返回结果

------

### 6.6.4 异常分支

#### 分支 A：`scope = ONE` 但匹配多条

返回 `NON_UNIQUE_RESULT`。

#### 分支 B：UPDATE / DELETE 无匹配对象

根据策略可返回 `NO_RESULT` 或 `affectedCount = 0`。

#### 分支 C：UPSERT 无法判断存在性

返回 `SEMANTIC_ERROR` 或 `EXECUTION_ERROR`。

#### 分支 D：主写源成功、扩展写源失败

根据写策略：

- 回滚主写源
- 标记补偿任务
- 返回失败并记录审计

------

### 6.6.5 输出结果

成功时建议输出：

- `success = true`
- `operation`
- `metadata.affectedCount`

失败时输出：

- `success = false`
- `errors`
- `trace`

------

### 6.6.6 风险点

1. 多源写一致性复杂。
2. `scope = MANY` 存在高风险误更新 / 误删除。
3. UPSERT 的存在性判断与主写策略不一致时，容易造成重复或覆盖问题。

------

### 6.6.7 实现建议

1. 主写源必须明确。
2. UPDATE / DELETE 建议默认加强保护，尤其对 `scope = MANY`。
3. UPSERT 建议严格基于 identity source 或唯一索引源实现。
4. 多源写场景建议从同步弱一致或补偿模型起步。

------

## 6.7 BATCH 执行流程

### 6.7.1 流程目标

BATCH 执行流程用于在一个请求中批量执行多个子操作，并根据 `atomic` 控制整体原子性。

------

### 6.7.2 前置条件

1. 顶层 `operation = BATCH`。
2. `mutation.atomic` 已显式声明。
3. `mutation.items` 非空。
4. 子项均为合法的非 `BATCH` 子请求。

------

### 6.7.3 处理步骤

#### 步骤 1：校验 BATCH 结构

- 校验 `atomic`
- 校验 `items[]`
- 校验子项 operation 合法性

#### 步骤 2：逐子项编译

每个子项单独经历：

- AST 构建
- 校验
- 逻辑计划生成
- 物理计划生成

#### 步骤 3：确定执行顺序

默认按 `items[]` 顺序执行；若未来支持依赖，则可扩展依赖执行。

#### 步骤 4：执行子项

调度器逐项执行或按依赖并行执行。

#### 步骤 5：处理失败

- 若 `atomic = true`：任一子项失败则停止后续执行，并触发回滚 / 补偿
- 若 `atomic = false`：记录失败子项并继续执行后续项

#### 步骤 6：汇总整体结果

输出整体执行结果、子项状态和 trace。

------

### 6.7.4 异常分支

#### 分支 A：某子项校验失败

若 `atomic = true`，整体失败；若 `atomic = false`，可跳过该子项并继续执行。

#### 分支 B：某子项执行失败

按 atomic 策略处理：

- 原子模式：整体失败
- 非原子模式：局部失败

#### 分支 C：回滚 / 补偿失败

记录审计并返回失败状态；必要时生成后续补偿任务。

------

### 6.7.5 输出结果

建议输出：

- 整体 success / failure
- 子项执行状态数组
- metadata（成功数 / 失败数）
- trace

------

### 6.7.6 风险点

1. BATCH 若允许读写混合，语义与执行顺序会显著复杂化。
2. 原子模式下，底层 source 不支持事务时只能采用补偿，复杂度较高。
3. 大批量 items 会加重编译和调度压力。

------

### 6.7.7 实现建议

1. 第一阶段建议限制 BATCH 仅支持写操作子项。
2. `atomic = true` 时应明确仅在支持事务 / 补偿的边界内承诺原子性。
3. 建议对子项数量设置上限。
4. 建议为每个子项生成独立 trace node，便于问题排查。