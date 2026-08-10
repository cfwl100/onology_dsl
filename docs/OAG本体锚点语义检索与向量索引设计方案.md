# OAG 面向本体锚点的语义检索、混合排序与本体子图构建设计方案

> 版本：V5.0  
> 目标：在保留既有 OAG 索引设计、Anchor/Evidence 模型、DataSync 分工、混合召回、RRF、LLM 精排和三类子图策略的基础上，结合当前代码真实实现，形成一份可直接指导研发落地、灰度演进、性能评测和下游 Cypher 生成的完整方案。  
> 设计原则：**Anchor First，Evidence for Anchor，Evidence for Cypher，Core Graph 与 Semantic Extension 分离，兼容现状、渐进增强。**
