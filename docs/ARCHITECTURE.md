# AI 智能体平台 - 架构文档

> **当前版本**: 2.0.0
> **更新日期**: 2026-01-21

## 概述

AI 智能体平台是一个可扩展的多智能体协作系统，基于 **FastAPI** 和 **异步编程** 构建。平台采用 **Orchestrator 模式** 协调多个专门的 LLM 智能体完成复杂任务，并通过 **Java 标准消息协议** 实现流式响应。

### 核心特性

- **多智能体编排**: 使用协调器模式管理规划、检索、总结等专门智能体
- **流式响应**: 基于 SSE (Server-Sent Events) 的实时通信
- **Java 标准协议**: 兼容 Java 后端定义的事件格式
- **多知识库支持**: 支持配置多个 ZhipuAI 知识库
- **网页搜索集成**: 可选的实时网络搜索能力
- **智能去重**: 文档级别的去重和引用管理

---

## 核心设计原则

### 1. 智能体隔离
- 每个智能体独立存放在 `agents/<智能体名称>/` 目录
- 智能体拥有自己的配置、端点和业务逻辑
- 智能体可以独立开发、测试和部署

### 2. 共享基础设施
- 通用代码存放在 `shared/` 目录
- 协议 (`shared/protocols/`)、工具类 (`shared/utils/`) 可复用
- API 网关 (`shared/api/gateway.py`) 统一路由管理

### 3. 编排器模式
- 使用 `DualAgentOrchestrator` 协调多个智能体的工作流程
- 智能体之间通过异步生成器 (AsyncGenerator) 通信
- 事件驱动的流式处理

### 4. Java 标准协议
- 使用 Java 后端定义的消息格式
- 支持多种事件类型：PLAN、INVOCATION、ARTIFACT、STREAM
- 统一的上下文和状态管理

---

## 目录结构

```
ai-agent-platform/
│
├── main.py                           # 统一服务入口
├── requirements.txt                  # Python 依赖
├── .env / .env.example               # 环境变量配置
│
├── config/                           # 全局配置
│   ├── settings.py                   # Pydantic 设置管理器
│   ├── knowledge_bases.json          # 知识库配置（可选）
│   └── agents.yaml                   # 智能体注册表
│
├── shared/                           # 共享基础设施
│   ├── protocols/                    # 消息协议
│   │   └── java_protocol.py          # Java 标准协议适配器
│   ├── api/                          # API 网关
│   │   └── gateway.py                # FastAPI 应用工厂
│   └── utils/                        # 通用工具类
│       ├── logger.py                 # 日志工具
│       └── document_manager.py       # 文档管理器（去重/引用）
│
├── agents/                           # 所有智能体
│   └── zhiku/                        # 知识检索智能体（v2.0）
│       ├── api/endpoints.py          # API 端点 (/api/v2/query)
│       ├── llm/
│       │   ├── planning_agent.py     # 规划智能体（DeepSeek）
│       │   ├── retrieval_agent.py    # 检索智能体（ZhipuAI）
│       │   ├── summary_agent.py      # 总结智能体（DeepSeek）
│       │   └── dual_agent_orchestrator.py  # 编排器
│       └── tools/
│           ├── knowledge_retrieval.py  # 知识库检索工具
│           └── web_search.py            # 网页搜索工具
│
├── docs/                             # 文档
│   ├── ARCHITECTURE.md               # 架构文档（本文档）
│   ├── AGENT_TEMPLATE.md             # 智能体开发模板
│   └── DEVELOPMENT.md                # 开发指南
│
└── tests/                            # 测试
    ├── shared/                       # 共享模块测试
    └── agents/                       # 智能体测试
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
