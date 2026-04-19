# ontology-data-access-suite-full-v3.3-refactored

本目录采用四层组织方式：

- 顶层入口：只做意图识别与路由
- 操作层：只描述当前目录负责的请求边界、输入契约、输出契约与约束
- references：承载当前目录的详细语法说明、操作符说明、校验规则与边界样例
- scripts：负责转换、组装与校验；公共逻辑统一下沉到 `shared/`

## 当前调整重点

1. 顶层入口不再暴露内部语法名词或结构细节。
2. 各目录 `SKILL.md` 不再依赖外部说明书引用；所需规范说明均下沉到本目录 `references/`。
3. 各目录 `SKILL.md` 只保留与当前操作相关的结构说明，不混入其他操作语法。
4. 每个目录的 `references/examples.md` 都补充了最小有效结构、常见变体与边界样例。
5. 为所有 Python 脚本补充了测试用例，测试位于 `tests/`。

## 测试

```bash
cd ontology-data-access-suite-full-v3.3-refactored
pytest -q
```
