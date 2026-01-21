# AI 智能体平台 - 架构文档

## 概述

AI 智能体平台是一个可扩展的多智能体协作系统，支持在单一代码仓库中管理多个 AI 智能体，通过统一服务的不同端点访问。

---

## 核心设计原则

### 1. 智能体隔离
- 每个智能体独立存放在 `agents/<智能体名称>/` 目录
- 智能体拥有自己的配置、端点和业务逻辑
- 智能体可以独立开发、测试和部署

### 2. 共享基础设施
- 通用代码存放在 `shared/` 目录
- 协议、工具类和工具可复用
- API 网关将请求路由到相应的智能体

### 3. 统一服务
- 单一 `main.py` 启动所有智能体
- 所有智能体通过一个服务访问（不同路由）
- 集中式日志、监控和配置管理

### 4. 可扩展性
- 添加新智能体简单（复制模板，实现接口）
- 通过 `config/agents.yaml` 注册智能体实现发现
- 支持智能体版本管理

---

## 目录结构

```
ai-agent-platform/
│
├── main.py                           # 统一服务入口
├── config/                           # 全局配置
│   ├── settings.py                   # 全局设置加载器
│   └── agents.yaml                   # 智能体注册配置
│
├── shared/                           # 共享基础设施
│   ├── protocols/                    # 消息协议
│   │   ├── java_protocol.py          # Java 标准协议
│   │   └── base_protocol.py          # 基础协议接口
│   ├── api/                          # API 网关
│   │   └── gateway.py                # 主 API 路由器
│   ├── utils/                        # 通用工具类
│   │   ├── logger.py
│   │   └── document_manager.py
│   └── tools/                        # 共享工具
│       └── base_tool.py
│
├── agents/                           # 所有智能体
│   ├── base_agent.py                 # 智能体基类接口
│   │
│   ├── zhiku/                        # 知识检索智能体
│   │   ├── config.py
│   │   ├── api/endpoints.py          # /api/v2/*
│   │   ├── llm/
│   │   │   ├── planning_agent.py
│   │   │   ├── retrieval_agent.py
│   │   │   ├── summary_agent.py
│   │   │   └── orchestrator.py
│   │   └── tools/
│   │       └── knowledge_retrieval.py
│   │
│   └── [其他智能体]/
│
└── tests/                            # 测试
    ├── shared/
    ├── agents/
    └── integration/
```

---

## 核心组件

### 1. API 网关 (`shared/api/gateway.py`)

负责聚合所有智能体的路由，提供统一的服务入口。

**功能**：
- 路由分发
- CORS 配置
- 中间件管理
- 统一错误处理

**示例**：
```python
from fastapi import FastAPI
from agents.zhiku.api.endpoints import router as zhiku_router

def create_app() -> FastAPI:
    app = FastAPI(title="AI 智能体平台")
    app.include_router(zhiku_router, prefix="/api/v2", tags=["知识智能体"])
    return app
```

---

### 2. 消息协议 (`shared/protocols/`)

定义智能体与前端/后端的通信格式。

**Java 标准协议**：
- `PLAN_DECLARED`: 声明所有阶段
- `PLAN_CHANGE`: 阶段状态变更
- `STREAM_THING`: 思考过程
- `STREAM_CONTENT`: 正文内容
- `INVOCATION_DECLARED`: 调用声明
- `INVOCATION_CHANGE`: 调用变更
- `ARTIFACT`: 产物
- `END`: 结束

**示例**：
```python
from shared.protocols.java_protocol import build_stream_content

message = build_stream_content("这是流式内容")
# 输出: {"event_type": "STREAM_CONTENT", "context": {...}, "messages": [...]}
```

---

### 3. 配置管理 (`config/`)

**全局配置** (`settings.py`)：
- 环境变量加载
- API 密钥管理
- 服务器配置

**智能体注册** (`agents.yaml`)：
```yaml
agents:
  zhiku:
    enabled: true
    name: "知识检索智能体"
    version: "2.0.0"
    api_prefix: "/api/v2"
```

---

### 4. 工具类 (`shared/utils/`)

**日志工具** (`logger.py`)：
```python
from shared.utils.logger import setup_logger

logger = setup_logger("my_module")
logger.info("✅ 操作成功")
```

**文档管理** (`document_manager.py`)：
- 文档去重
- 相似度计算
- 引用排序

---

## 智能体开发流程

### 1. 创建目录结构
```bash
mkdir -p agents/my_agent/{api,llm,tools,config}
```

### 2. 实现核心逻辑
在 `agents/my_agent/llm/agent.py` 中实现业务逻辑

### 3. 定义 API 端点
在 `agents/my_agent/api/endpoints.py` 中定义路由

### 4. 注册智能体
在 `config/agents.yaml` 中添加配置

### 5. 集成到网关
在 `shared/api/gateway.py` 中注册路由

---

## API 端点规范

### 知识检索智能体
- **端点**: `POST /api/v2/query`
- **请求**: `{"query": "用户问题"}`
- **响应**: SSE 流式事件

### 未来智能体示例
- **代码生成**: `POST /api/code/generate`
- **对话**: `POST /api/chat/message`

---

## 数据流

```
用户请求
    ↓
API 网关 (gateway.py)
    ↓
智能体路由 (endpoints.py)
    ↓
智能体逻辑 (agent.py)
    ↓
工具调用 (tools/)
    ↓
协议转换 (protocols/)
    ↓
SSE 流式响应
```

---

## 扩展点

### 1. 添加新智能体
复制模板 → 实现逻辑 → 注册配置

### 2. 添加新协议
继承 `BaseProtocol` → 实现 `build_message`

### 3. 添加新工具
实现工具函数 → 注册到 `TOOL_FUNCTIONS`

### 4. 智能体间通信
通过事件总线或直接调用

---

## 部署架构

### 单服务部署
```
[Nginx] → [FastAPI App] → [所有智能体]
```

### 微服务部署（未来）
```
[API Gateway]
    ├─→ [知识智能体服务]
    ├─→ [代码智能体服务]
    └─→ [对话智能体服务]
```

---

## 性能优化

### 1. 异步处理
所有 I/O 操作使用异步

### 2. 连接池
复用 HTTP 客户端连接

### 3. 缓存
缓存频繁访问的数据

### 4. 流式响应
使用 SSE 减少延迟

---

## 安全考虑

### 1. API 密钥管理
使用环境变量，不提交到代码库

### 2. 输入验证
使用 Pydantic 模型验证

### 3. 速率限制
使用中间件限制请求频率

### 4. CORS 配置
生产环境限制允许的域名

---

## 监控与日志

### 日志级别
- `DEBUG`: 详细调试信息
- `INFO`: 一般信息
- `WARNING`: 警告信息
- `ERROR`: 错误信息

### 日志格式
```
2026-01-16 13:50:50 - module_name - INFO - ✅ 消息内容
```

---

## 版本管理

### 智能体版本
在 `agents.yaml` 中定义版本号

### API 版本
通过路由前缀区分（如 `/api/v2/`）

---

## 未来规划

### 短期
- [ ] 智能体间通信机制
- [ ] 统一的错误处理
- [ ] 性能监控仪表板

### 中期
- [ ] 智能体市场
- [ ] 插件系统
- [ ] 多租户支持

### 长期
- [ ] 分布式部署
- [ ] 自动扩缩容
- [ ] AI 编排引擎

---

## 参考资源

- **FastAPI 文档**: https://fastapi.tiangolo.com/
- **Pydantic 文档**: https://docs.pydantic.dev/
- **异步编程**: https://docs.python.org/3/library/asyncio.html
