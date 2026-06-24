# 验证传播证据

本文是 `alarm-propagation` 的传播证据验证知识片段。外层 `SKILL.md` 读取本文后，只需将下方 6 行内容按需变量替换并注入 `Ontology-based-planning-skill`。

```text
本体ID：network@1.0
业务意图：验证起始网元 ${neName} 在指定传播证据方向 ${directions} 上，是否存在名称属于 ${alarmNames} 的活动告警证据，并返回相关网元和告警对象结构。
业务领域知识：传播证据验证是在实例层检查传播链是否有活动告警支撑，不等同于查询传播关系定义；支持方向包括 same_site（同站点/同机房）、peer_ne（对端网元）、service_path（业务路径）；每个方向必须独立检索子图、独立规划、独立查询、独立汇总；同站点方向从起始网元定位同站点其他网元并查询其活动告警；对端网元方向从起始网元定位对端网元并查询其活动告警，必须排除起始网元自身；业务路径方向从起始网元定位同业务路径其他网元并查询其活动告警，businesspath 是对象类型不是关系边，业务路径设备名约束可使用 businesspath.aDeviceName = ${neName_service_path}；告警类型使用 alarm.alarmName，单条告警唯一标识使用 alarm.identifier；长告警列表必须变量化保存，后续步骤只引用变量名，只有最终查询参数允许展开；网元返回字段为 srcSpaceVid、name、className、domain、networkType；告警返回字段为 node、ownerVid、severity、alarmName、identifier、firstOccurrence、lastOccurrence、clearTime；S3 空结果是有效证据结果，表示该方向未发现支撑传播的活动告警，不自动放宽条件、不换路径、不重试；禁止无业务依据查询 Port、Link 或 site -> alarm 直连路径；禁止编造 OAG 未返回的对象、字段、关系或函数。
流程级定制：默认流程按每个方向独立执行 S1 -> S2 -> S3 -> S6；不执行 S4/S5 Function；多方向按用户指定顺序串行执行；S3 空结果视为有效结果并进入 S6 汇总。
步骤级定制：S1 子图检索根据 directionKey 选择检索规则：same_site 查询网元通过站点关联到其他网元及这些网元告警的本体子图，peer_ne 查询网元通过对端链路关联到其他网元及这些网元告警的本体子图，service_path 查询网元通过业务路径关联到其他网元及这些网元告警的本体子图；S2 基于 S1 子图事实规划 ASSOCIATION_QUERY，关系名、字段归属和路径必须来自子图返回，不得写死；S3 生成 OAC 查数据请求，过滤条件包含 ne.name = ${neName_<directionKey>}、alarm.alarmName IN ${alarmNames_<directionKey>}，peer_ne 追加 peerNe.name != ${neName_peer_ne}，service_path 追加 businesspath.aDeviceName = ${neName_service_path}，输出 {objects, relationships}，message_type 分别为 same_site_active_alarms、peer_ne_active_alarms、service_path_active_alarms；S6 按方向输出 FOUND、NOT_FOUND、MISSING_INFO 或 FAILED，并给出 evidenceCount、evidenceObjects、missingItems 和 nextAction。
缺失信息：如果用户未指定传播证据方向，填写“未指定规划方向”；如果缺少起始网元名称或告警类型列表，填写对应缺失变量；否则填写无。
```
