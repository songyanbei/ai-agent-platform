# AI 智能体平台开发指南

本文档提供平台开发的完整指南，包括环境搭建、开发流程、最佳实践等。

---

## 📋 目录

1. [环境准备](#环境准备)
2. [项目结构](#项目结构)
3. [开发流程](#开发流程)
4. [新智能体开发](#新智能体开发)
5. [协议规范](#协议规范)
6. [测试指南](#测试指南)
7. [部署指南](#部署指南)
8. [常见问题](#常见问题)

---

## 🛠️ 环境准备

### 系统要求

- Python 3.8+
- Git
- 虚拟环境工具（venv 或 conda）

### 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/songyanbei/ai-agent-platform.git
cd ai-agent-platform

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
.\venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 填写 API 密钥
```

### 必需的 API 密钥

在 `.env` 文件中配置：

```env
# 智谱 AI（用于知识库检索）
ZHIPU_API_KEY=your_zhipu_api_key
ZHIPU_KNOWLEDGE_ID=your_knowledge_base_id

# DeepSeek（用于 LLM 推理）
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

---

## 📁 项目结构

```
ai-agent-platform/
├── main.py                          # 服务入口
├── config/                          # 全局配置
│   ├── settings.py                  # 配置加载器
│   ├── agents.yaml                  # 智能体注册表
│   └── knowledge_bases.json         # 知识库配置（可选）
│
├── shared/                          # 共享基础设施
│   ├── protocols/                   # 消息协议
│   │   ├── base_protocol.py        # 协议基类
│   │   └── java_protocol.py        # Java 标准协议
│   ├── api/                         # API 网关
│   │   └── gateway.py               # 路由聚合器
│   └── utils/                       # 工具类
│       ├── logger.py                # 日志工具
│       └── document_manager.py      # 文档管理
│
├── agents/                          # 智能体目录
│   ├── base_agent.py                # 智能体基类
│   └── zhiku/                       # 知识检索智能体
│       ├── api/endpoints.py         # API 端点
│       ├── llm/                     # LLM 组件
│       │   ├── planning_agent.py   # 规划智能体
│       │   ├── retrieval_agent.py  # 检索智能体
│       │   ├── summary_agent.py    # 总结智能体
│       │   └── dual_agent_orchestrator.py
│       ├── tools/                   # 工具
│       │   └── knowledge_retrieval.py
│       └── config/                  # 配置
│           └── knowledge_bases.json
│
├── docs/                            # 文档
│   ├── ARCHITECTURE.md              # 架构文档
│   ├── AGENT_TEMPLATE.md            # 智能体模板
│   └── DEVELOPMENT.md               # 本文档
│
└── tests/                           # 测试
    ├── shared/
    └── agents/
```

---

## 🔄 开发流程

### 1. 创建功能分支

```bash
git checkout -b feature/your-feature-name
```

### 2. 开发和测试

```bash
# 启动开发服务器
python main.py

# 运行测试
pytest tests/

# 代码格式化（可选）
black .
flake8 .
```

### 3. 提交代码

```bash
git add .
git commit -m "feat: 添加新功能描述"
git push origin feature/your-feature-name
```

### 提交信息规范

使用语义化提交信息：

- `feat:` 新功能
- `fix:` 修复 bug
- `docs:` 文档更新
- `refactor:` 代码重构
- `test:` 测试相关
- `chore:` 构建/工具链更新

---

## 🤖 新智能体开发

### 快速开始

参考 [AGENT_TEMPLATE.md](AGENT_TEMPLATE.md) 获取完整的代码模板。

### 开发步骤

#### 1. 创建目录结构

```bash
mkdir -p agents/my_agent/{api,llm,tools,config}
touch agents/my_agent/__init__.py
touch agents/my_agent/api/{__init__.py,endpoints.py}
touch agents/my_agent/llm/{__init__.py,agent.py}
touch agents/my_agent/tools/__init__.py
touch agents/my_agent/config/__init__.py
```

#### 2. 实现核心逻辑

在 `agents/my_agent/llm/agent.py` 中：

```python
from openai import AsyncOpenAI
from typing import AsyncGenerator, Dict, Any
from config.settings import get_settings
from shared.utils.logger import setup_logger

logger = setup_logger("my_agent")

class MyAgent:
    def __init__(self):
        settings = get_settings()
        self.client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url
        )
        logger.info("✅ MyAgent 初始化完成")
    
    async def process(self, query: str) -> AsyncGenerator[Dict[str, Any], None]:
        # 实现您的业务逻辑
        yield {"type": "content", "content": "处理结果"}
```

#### 3. 定义 API 端点

在 `agents/my_agent/api/endpoints.py` 中：

```python
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json

router = APIRouter()

class QueryRequest(BaseModel):
    query: str

@router.post("/process")
async def process_query(request: QueryRequest):
    async def generate_events():
        # 生成 SSE 事件
        yield f"data: {json.dumps({'type': 'result'})}\n\n"
    
    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream"
    )
```

#### 4. 注册智能体

在 `config/agents.yaml` 中：

```yaml
agents:
  my_agent:
    enabled: true
    name: "我的智能体"
    version: "1.0.0"
    api_prefix: "/api/my_agent"
```

#### 5. 添加到网关

在 `shared/api/gateway.py` 中：

```python
from agents.my_agent.api.endpoints import router as my_agent_router

def create_app() -> FastAPI:
    app = FastAPI(...)
    app.include_router(
        my_agent_router,
        prefix="/api/my_agent",
        tags=["我的智能体"]
    )
    return app
```

---

## 📊 协议规范

### Java 标准协议

平台使用 Java 标准消息协议进行前后端通信。详见 [API_V2_SPECIFICATION.md](../API_V2_SPECIFICATION.md)。

### 主要事件类型

- `PLAN_DECLARED` - 声明所有阶段
- `PLAN_CHANGE` - 阶段状态变更
- `STREAM_THING` - 思考过程
- `STREAM_CONTENT` - 正文内容
- `INVOCATION_DECLARED` - 调用声明
- `INVOCATION_CHANGE` - 调用变更
- `ARTIFACT` - 产物声明
- `ARTIFACT_CHANGE` - 产物变更
- `END` - 结束

### 使用示例

```python
from shared.protocols.java_protocol import (
    build_plan_declared,
    build_stream_content,
    build_end
)

# 声明阶段
yield f"data: {json.dumps(build_plan_declared())}\n\n"

# 流式内容
yield f"data: {json.dumps(build_stream_content('内容'))}\n\n"

# 结束
yield f"data: {json.dumps(build_end())}\n\n"
```

---

## 🧪 测试指南

### 单元测试

```bash
# 运行所有测试
pytest tests/

# 运行特定测试
pytest tests/agents/zhiku/test_planning_agent.py

# 查看覆盖率
pytest --cov=agents --cov-report=html
```

### API 测试

使用 curl 测试：

```bash
curl -X POST http://localhost:8000/api/v2/query \
  -H "Content-Type: application/json" \
  -d '{"query": "测试查询"}'
```

使用 Python 测试：

```python
import httpx
import asyncio

async def test_api():
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            "http://localhost:8000/api/v2/query",
            json={"query": "测试"}
        ) as response:
            async for line in response.aiter_lines():
                print(line)

asyncio.run(test_api())
```

---

## 🚀 部署指南

### 开发环境

```bash
python main.py
```

### 生产环境

使用 Gunicorn + Uvicorn：

```bash
gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

### Docker 部署

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

---

## ❓ 常见问题

### Q: 如何添加新的知识库？

A: 编辑 `agents/zhiku/config/knowledge_bases.json`：

```json
[
  {
    "id": "your_kb_id",
    "name": "知识库名称",
    "description": "详细描述",
    "domain": "领域标签"
  }
]
```

### Q: 如何调试流式响应？

A: 使用日志和 curl：

```bash
# 启用 DEBUG 日志
export LOG_LEVEL=DEBUG
python main.py

# 使用 curl 查看实时输出
curl -N http://localhost:8000/api/v2/query \
  -H "Content-Type: application/json" \
  -d '{"query": "测试"}'
```

### Q: 如何处理超时问题？

A: 在 LLM 客户端中配置超时：

```python
import httpx

timeout = httpx.Timeout(
    connect=60.0,
    read=300.0,
    write=300.0,
    pool=60.0
)

client = AsyncOpenAI(timeout=timeout)
```

---

## 📚 参考资源

- [架构文档](ARCHITECTURE.md) - 系统设计和原理
- [API 规范](../API_V2_SPECIFICATION.md) - 接口文档
- [智能体模板](AGENT_TEMPLATE.md) - 代码模板
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [Pydantic 文档](https://docs.pydantic.dev/)

---

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交代码
4. 创建 Pull Request

欢迎贡献！🎉
