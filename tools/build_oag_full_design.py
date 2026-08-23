from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
BACKUP = ROOT / "docs/archive/OAG本体锚点语义检索与向量索引设计方案-V5.16完整备份.md"
CURRENT = ROOT / "docs/OAG本体锚点语义检索与向量索引设计方案.md"
OUTPUT = ROOT / "docs/OAG本体语义索引管理和语义检索.md"

backup = BACKUP.read_text(encoding="utf-8").replace("\r\n", "\n")
current = CURRENT.read_text(encoding="utf-8").replace("\r\n", "\n")


def split_before_appendix(text: str):
    marker = "\n# 附录 A：PR #42 检视意见优化方案（V5.16 规范）"
    if marker not in text:
        raise RuntimeError("V5.16 backup appendix marker not found")
    main, appendix = text.split(marker, 1)
    return main.rstrip() + "\n", appendix.lstrip("\n")


def split_main_chapters(text: str):
    matches = list(re.finditer(r"(?m)^# ([1-7])\. ([^\n]+)$", text))
    if len(matches) != 7:
        raise RuntimeError(f"expected 7 main chapters, got {len(matches)}")
    preamble = text[:matches[0].start()].rstrip()
    chapters = {}
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chapters[int(m.group(1))] = {
            "title": m.group(2).strip(),
            "raw": text[m.start():end].rstrip(),
            "body": text[m.end():end].strip("\n"),
        }
    return preamble, chapters


def parse_appendix(text: str):
    matches = list(re.finditer(r"(?m)^# (\d+)\. ([^\n]+)$", text))
    if not matches:
        raise RuntimeError("appendix numbered sections not found")
    intro = text[:matches[0].start()].rstrip()
    sections = {}
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[int(m.group(1))] = {
            "title": m.group(2).strip(),
            "body": text[m.end():end].strip("\n"),
            "raw": text[m.start():end].rstrip(),
        }
    return intro, sections


def demote_headings(text: str, levels: int = 1):
    out = []
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append(line)
            continue
        if not in_fence:
            m = re.match(r"^(#{1,6}) (.*)$", line)
            if m:
                hashes = "#" * min(6, len(m.group(1)) + levels)
                line = f"{hashes} {m.group(2)}"
        out.append(line)
    return "\n".join(out).strip()


def quote_source(text: str):
    return "\n".join("> " + line if line else ">" for line in text.splitlines())


backup_main, appendix = split_before_appendix(backup)
b_preamble, b_chapters = split_main_chapters(backup_main)
c_preamble, c_chapters = split_main_chapters(current)
appendix_intro, appendix_sections = parse_appendix(appendix)

route_to_chapter_1 = [2]
route_to_chapter_3 = [3, 4, 5, 6, 7, 9]
route_to_chapter_7 = [8, 10, 11, 12, 13]
all_routed = set(route_to_chapter_1 + route_to_chapter_3 + route_to_chapter_7)
missing = sorted(set(appendix_sections) - all_routed)
if missing:
    raise RuntimeError(f"appendix sections not routed: {missing}")

chapter_titles = {
    1: "设计目标、术语与总体架构",
    2: "数据模型与语义索引结构",
    3: "语义索引管理：构建、数据接入、任务、MinIO 与一致性",
    4: "实体提取、Entity Linking 与 6 路混合召回",
    5: "LLM 精排与最终语义检索结果",
    6: "本体对象投影、子图策略、路径探测、nGQL 与最终返回",
    7: "性能、配置、可观测性、评测与迁移",
}

parts = []
parts.append("# OAG 本体语义索引管理和语义检索")
parts.append("""
> 版本：V6.0（全量整合版）  
> 日期：2026-08-23  
> 来源：`docs/archive/OAG本体锚点语义检索与向量索引设计方案-V5.16完整备份.md` + `docs/OAG本体锚点语义检索与向量索引设计方案.md`。  
> 整合原则：**信息完整性优先。V5.16 作为完整详细设计基线，V5.17 作为规范收敛与新增设计；重复内容可以分层归并，但任何具有独立语义的原始设计信息不得因重写而删除。PR #42 原附录内容已按主题合并回正文，不再作为独立附录。**
""".strip())
parts.append("""
## 文档结构

1. 设计目标、术语与总体架构  
2. 数据模型与语义索引结构  
3. 语义索引管理：构建、数据接入、任务、MinIO 与一致性  
4. 实体提取、Entity Linking 与 6 路混合召回  
5. LLM 精排与最终语义检索结果  
6. 本体对象投影、子图策略、路径探测、nGQL 与最终返回  
7. 性能、配置、可观测性、评测与迁移

阅读规则：每章的“V5.17 规范收敛与新增设计”用于说明当前推荐行为；“V5.16 完整详细设计”保留原有实现、接口、DDL、兼容方案、算法、错误处理、评测和灰度信息。若出现历史路径与当前收敛规范并存，明确标注为历史/兼容信息，当前执行以 V5.17/PR #42 收敛规则为准。
""".strip())

parts.append("## 0. 版本来源、信息完整性与规范优先级")
parts.append("### 0.1 V5.16 完整设计原始元信息\n\n" + quote_source(b_preamble))
parts.append("### 0.2 V5.17 当前文档原始元信息\n\n" + quote_source(c_preamble))
parts.append("### 0.3 PR #42 检视方案原始定位信息\n\n" + demote_headings(appendix_intro, 1))
parts.append("### 0.4 PR #42 检视结论总表\n\n" + demote_headings(appendix_sections[2]["body"], 1))
parts.append("""
### 0.5 最终规范优先级

1. 本文 V6.0 各章中的“最终规范/规范收敛”条目为当前推荐行为；
2. V5.16 详细设计中的旧路径、旧接口值、旧 Checkpoint 描述等作为历史实现与兼容背景保留，不应覆盖已明确收敛的 V5.17/PR #42 规则；
3. 当前关键收敛包括：动态 Enum/Instance 统一 MinIO CSV 交付、`instanceDataSourceMode=OAC|BUSINESS_NOTICE`、Software ≤1W 源侧用户、SEC ≤100W 源侧用户、SHA-256、`T_OAG_INDEX_TASK.CHECKPOINT` TEXT JSON、未完成 Chunk 幂等重放、最终返回增加 `semanticExtensions.valueMappings`；
4. `retrievalResults` 是语义命中事实，`seedNodes/nodes/edges` 是图构建/兼容结构，`semanticExtensions.valueMappings` 是查询生成友好的确定性投影视图。
""".strip())

for n in range(1, 8):
    parts.append(f"# {n}. {chapter_titles[n]}")

    parts.append(f"## {n}.0 V5.17 规范收敛与新增设计（完整保留）")
    parts.append(demote_headings(c_chapters[n]["body"], 1))

    parts.append(f"## {n}.1 V5.16 完整详细设计（信息基线，完整保留）")
    parts.append(demote_headings(b_chapters[n]["body"], 1))

    if n == 1:
        parts.append("## 1.2 PR #42 检视结论在总体架构中的收敛")
        parts.append(demote_headings(appendix_sections[2]["body"], 1))
    elif n == 3:
        parts.append("## 3.100 PR #42 检视规范：数据接入、容量、文件身份、Checkpoint、性能与错误处理")
        for sid in route_to_chapter_3:
            s = appendix_sections[sid]
            parts.append(f"### 3.100.{sid} {s['title']}")
            parts.append(demote_headings(s["body"], 1))
    elif n == 7:
        parts.append("## 7.100 PR #42 检视规范：配置、可观测性、验收、修订规则与最终决策")
        for sid in route_to_chapter_7:
            s = appendix_sections[sid]
            parts.append(f"### 7.100.{sid} {s['title']}")
            parts.append(demote_headings(s["body"], 1))

parts.append("""
# 8. 全量信息覆盖与维护原则

## 8.1 信息覆盖原则

本文的生成策略不是“摘要替换原文”，而是：

```text
V5.16 完整详细设计
+ V5.17 当前规范与新增设计
+ PR #42 检视方案按主题回填正文
→ V6.0 全量整合设计
```

因此旧实现细节仍可用于代码迁移、问题定位和兼容评估；当前规范则用于新开发和接口评审。

## 8.2 后续维护原则

后续新增设计应直接修改本文对应章节，不再创建“覆盖正文”的规范附录。需要保留历史演进时，使用章节内“历史方案/兼容方案/迁移说明”明确标识，避免产生多个相互覆盖的权威文档。
""".strip())

final = "\n\n---\n\n".join(p.strip() for p in parts if p and p.strip()) + "\n"

# Clarify known conflicts without deleting the original design intent.
final = final.replace(
    "索引构建统一支持三种服务端配置模式，不把数据源选择暴露成业务侧每次请求都要判断的参数：",
    "**历史方案（保留演进信息，不作为当前最终规范）：** 索引构建曾设计三种服务端配置模式，不把数据源选择暴露成业务侧每次请求都要判断的参数："
)
final = final.replace(
    "| `CHECKPOINT`           | VARCHAR(1024) |          | CSV 文件/行号或内部 Chunk Checkpoint                           |",
    "| `CHECKPOINT`           | TEXT          |          | 版本化 JSON Checkpoint；历史版本曾为 `VARCHAR(1024)`，当前通过升级脚本扩展为 TEXT |"
)
final = final.replace(
    "    CHECKPOINT            VARCHAR(1024),",
    "    CHECKPOINT            TEXT, -- 历史版本为 VARCHAR(1024)，V5.16 检视后升级为 TEXT JSON"
)
final = final.replace(
    "| `gauss_status` / `opensearch_status` | 两端提交状态 |",
    "| `gauss_status` / `opensearch_status` | 历史方案曾建议持久化两端提交状态；当前仅作为运行时日志/指标，不逐 Chunk 持久化 |"
)
final = final.replace(
    "三种数据交付方式只在进入 OAG 前不同：OMS 提供种子资产，OAC 可以交付小批/分页记录，OAC/DataSync/业务服务可以通过 MinIO 交付大文件。从 `Schema Validator` 开始统一使用 Normalize/Dedup/Embedding/双写/Verify/Publish 流水线。",
    "**历史兼容描述：** 三种数据交付方式曾在进入 OAG 前区分 OMS、OAC 小批/分页和 MinIO 大文件；当前动态 Enum/Instance 已统一收敛为 MinIO CSV + notice，原小批/分页信息仅用于理解旧实现。从 `Schema Validator` 开始统一使用 Normalize/Dedup/Embedding/双写/Verify/Publish 流水线。"
)
final = final.replace(
    "| 人工触发索引更新，小数据量  | 手动构建 → 任务查询                        | `INCREMENTAL`  | OAC 小批/分页返回 OAG | OAC 返回 UPSERT/DELETE 变化记录                   |",
    "| 人工触发索引更新，小数据量  | 手动构建 → OAC → MinIO → notice → 任务查询 | `INCREMENTAL` | MinIO CSV | 历史曾支持 OAC 小批/分页直返并返回 UPSERT/DELETE 变化记录；当前统一 MinIO |"
)

# Coverage validation: headings can be reorganized, but every substantive source line must remain.
def norm(line: str):
    x = line.strip()
    x = re.sub(r"^(?:>\s*)+", "", x)
    x = re.sub(r"^#{1,6}\s+", "", x)
    return x.strip()

final_norm_lines = {norm(line) for line in final.splitlines() if norm(line)}

# Exact source lines intentionally rewritten to reconcile old and current norms.
rewrite_contains = [
    "索引构建统一支持三种服务端配置模式",
    "CHECKPOINT`           | VARCHAR(1024)",
    "CHECKPOINT            VARCHAR(1024)",
    "gauss_status` / `opensearch_status",
    "三种数据交付方式只在进入 OAG 前不同",
    "人工触发索引更新，小数据量",
]


def is_heading(line: str):
    return bool(re.match(r"^\s*#{1,6}\s+", line))


def coverage(source: str, name: str):
    missing_lines = []
    checked = 0
    for line in source.splitlines():
        n = norm(line)
        if not n or n == "---" or is_heading(line):
            continue
        checked += 1
        if n in final_norm_lines:
            continue
        if any(token in line for token in rewrite_contains):
            continue
        missing_lines.append(line)
    if missing_lines:
        sample = "\n".join(missing_lines[:40])
        raise RuntimeError(f"{name} substantive coverage failure: {len(missing_lines)}/{checked} missing lines\n{sample}")
    print(f"{name}: {checked} substantive lines covered")

coverage(backup, "V5.16 backup")
coverage(current, "V5.17 current")

required = [
    "# OAG 本体语义索引管理和语义检索",
    "instanceDataSourceMode",
    "BUSINESS_NOTICE",
    "softwareMaxUsers: 10000",
    "secMaxUsers: 1000000",
    "SHA-256",
    "T_OAG_INDEX_TASK.CHECKPOINT",
    "semanticExtensions",
    "valueMappings",
    "PathProbePlan",
    "Weighted RRF",
    "GraphTopologyCache",
    "metric_closure_mst",
    "multi_source_bfs",
    "dsu_cached",
]
for token in required:
    if token not in final:
        raise RuntimeError(f"required token missing: {token}")
if "# 附录 A：PR #42" in final:
    raise RuntimeError("standalone Appendix A heading must not remain")

OUTPUT.write_text(final, encoding="utf-8")
print(f"generated: {OUTPUT}")
print(f"characters: {len(final)}")
print(f"lines: {len(final.splitlines())}")
print("coverage: V5.16=PASS, V5.17=PASS")
