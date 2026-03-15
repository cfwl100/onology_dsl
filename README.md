# OAC 服务工程（Spring Boot Java）+ OSDK（Python）

根据《OAC服务设计说明书》《OAC（Ontology Access）服务职责》《OQL翻译成物理查询的开发指导》《本体对象操作语言(OQL)-DSL规范v1.2》，工程实现更新为：

- **OAC 服务主体：Java + Spring Boot**
- **OSDK：Python**

## 工程结构

- `java/src/main/java/com/onology/oac`
  - `Main`：Spring Boot 启动入口
  - `access`：`/oac/{mode}` REST 接口
  - `model`：OQL canonical 请求/响应模型与校验
  - `metadata`：Schema / Mapping 快照注册
  - `compiler`：Binder + Logical/Physical Plan + Translator
  - `execution`：AdapterFactory + DAG Orchestrator
  - `result`：结果装配
  - `operation`：validate/explain/execute 策略处理器
- `java/src/test/java/com/onology/oac`
  - `OacControllerTest`：Spring Boot API 测试
  - `OqlDialectTranslationTest`：基于元数据 source 的 SQL/nGQL 翻译测试
  - `OacServiceTestMain`：无 Web 容器模式的服务自检
- `sdk/python/oac_osdk`
  - `OacClient`：Python OSDK 客户端
- `tests/test_osdk.py`
  - OSDK 单元测试（本地 mock HTTP 服务）

## 运行

### 启动 Spring Boot OAC 服务

```bash
cd java
mvn spring-boot:run
```

服务启动后可调用：

- `POST /oac/validate`
- `POST /oac/explain`
- `POST /oac/execute`

### 测试

```bash
cd java && mvn test
pytest
```
