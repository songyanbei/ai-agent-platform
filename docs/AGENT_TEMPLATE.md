# 智能体开发模板

快速创建新智能体的代码模板。

---

## 📁 目录结构模板

```bash
agents/template_agent/
├── __init__.py
├── config.py
├── README.md
├── api/
│   ├── __init__.py
│   └── endpoints.py
├── llm/
│   ├── __init__.py
│   └── agent.py
├── tools/
│   ├── __init__.py
│   └── example_tool.py
└── config/
    ├── __init__.py
    └── settings.json
```

---

## 📝 代码模板

### 1. `__init__.py`

```python
"""
模板智能体
"""
from .llm.agent import TemplateAgent

__all__ = ["TemplateAgent"]
```

---

### 2. `config.py`

```python
"""
智能体配置
"""
from pydantic import BaseModel
from typing import Optional


class TemplateAgentConfig(BaseModel):
    """智能体配置模型"""
    name: str = "模板智能体"
    version: str = "1.0.0"
    description: str = "这是一个智能体模板"
    
    # LLM 配置
    model: str = "deepseek-chat"
    max_tokens: int = 2000
    temperature: float = 0.7
    
    # 其他配置
    enable_logging: bool = True
    timeout: int = 30
```

---

### 3. `llm/agent.py`

```python
"""
智能体核心逻辑
"""
from openai import AsyncOpenAI
from typing import AsyncGenerator, Dict, Any
import httpx

from config.settings import get_settings
from shared.utils.logger import setup_logger
from agents.template_agent.config import TemplateAgentConfig

logger = setup_logger("template_agent")


class TemplateAgent:
    """模板智能体"""
    
    def __init__(self, config: TemplateAgentConfig = None):
        """
        初始化智能体
        
        Args:
            config: 智能体配置
        """
        self.config = config or TemplateAgentConfig()
        settings = get_settings()
        
        # 配置超时
        timeout = httpx.Timeout(
            connect=60.0,
            read=300.0,
            write=300.0,
            pool=60.0
        )
        
        # 初始化 LLM 客户端
        self.client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            timeout=timeout,
            max_retries=3
        )
        
        logger.info(f"✅ {self.config.name} 初始化完成")
    
    async def process(
        self, 
        query: str, 
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        处理用户查询
        
        Args:
            query: 用户输入
            **kwargs: 其他参数
            
        Yields:
            事件字典
        """
        logger.info(f"📝 开始处理: {query}")
        
        try:
            # 1. 发送开始事件
            yield {
                "type": "start",
                "message": "开始处理查询..."
            }
            
            # 2. 调用 LLM
            response = await self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": "你是一个有用的助手。"},
                    {"role": "user", "content": query}
                ],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                stream=True
            )
            
            # 3. 流式返回内容
            async for chunk in response:
                if chunk.choices[0].delta.content:
                    yield {
                        "type": "content",
                        "content": chunk.choices[0].delta.content
                    }
            
            # 4. 发送完成事件
            yield {
                "type": "end",
                "message": "处理完成"
            }
            
            logger.info("✅ 处理完成")
            
        except Exception as e:
            logger.error(f"❌ 处理失败: {e}", exc_info=True)
            yield {
                "type": "error",
                "error": str(e)
            }
```

---

### 4. `api/endpoints.py`

```python
"""
API 端点定义
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json

from agents.template_agent.llm.agent import TemplateAgent
from shared.utils.logger import setup_logger

logger = setup_logger("template_agent_api")

# 创建路由器
router = APIRouter()

# 初始化智能体
agent = TemplateAgent()


class QueryRequest(BaseModel):
    """查询请求模型"""
    query: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "你好，请介绍一下你自己"
            }
        }


@router.post("/process")
async def process_query(request: QueryRequest):
    """
    处理查询接口
    
    返回 SSE 流式响应
    """
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="查询内容不能为空")
    
    logger.info(f"收到请求: {request.query}")
    
    async def generate_events():
        """生成 SSE 事件流"""
        try:
            async for event in agent.process(request.query):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\\n\\n"
        except Exception as e:
            logger.error(f"生成事件失败: {e}")
            error_event = {"type": "error", "error": str(e)}
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\\n\\n"
    
    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "agent": "template_agent",
        "version": "1.0.0"
    }
```

---

### 5. `tools/example_tool.py`

```python
"""
示例工具
"""
from typing import Dict, Any
from shared.utils.logger import setup_logger

logger = setup_logger("template_tool")


async def example_tool(param: str) -> Dict[str, Any]:
    """
    示例工具函数
    
    Args:
        param: 参数
        
    Returns:
        Dict: 结果
    """
    logger.info(f"调用示例工具: {param}")
    
    try:
        # 执行工具逻辑
        result = f"处理结果: {param}"
        
        return {
            "success": True,
            "result": result
        }
    except Exception as e:
        logger.error(f"工具执行失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# 工具定义（用于 Function Calling）
EXAMPLE_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "example_tool",
        "description": "这是一个示例工具",
        "parameters": {
            "type": "object",
            "properties": {
                "param": {
                    "type": "string",
                    "description": "工具参数"
                }
            },
            "required": ["param"]
        }
    }
}

# 工具映射
TOOL_FUNCTIONS = {
    "example_tool": example_tool
}

# 可用工具列表
AVAILABLE_TOOLS = [
    EXAMPLE_TOOL_SCHEMA
]
```

---

### 6. `config/settings.json`

```json
{
  "name": "模板智能体",
  "version": "1.0.0",
  "description": "这是一个智能体模板",
  "parameters": {
    "model": "deepseek-chat",
    "max_tokens": 2000,
    "temperature": 0.7
  },
  "features": {
    "streaming": true,
    "function_calling": false
  }
}
```

---

### 7. `README.md`

```markdown
# 模板智能体

## 功能描述
这是一个智能体模板，用于快速创建新的智能体。

## API 端点

### 处理查询
- **URL**: `/api/template/process`
- **方法**: `POST`
- **请求体**:
  \`\`\`json
  {
    "query": "用户查询内容"
  }
  \`\`\`
- **响应**: SSE 流式事件

### 健康检查
- **URL**: `/api/template/health`
- **方法**: `GET`

## 配置

### 环境变量
无需额外环境变量（使用全局配置）

### 配置文件
- `config/settings.json`: 智能体配置

## 使用示例

\`\`\`bash
curl -X POST http://localhost:8000/api/template/process \\
  -H "Content-Type: application/json" \\
  -d '{"query": "你好"}'
\`\`\`

## 开发指南

1. 修改 `llm/agent.py` 实现业务逻辑
2. 更新 `api/endpoints.py` 定义 API
3. 在 `config/agents.yaml` 中注册
4. 在 `shared/api/gateway.py` 中添加路由

## 测试

\`\`\`bash
pytest tests/agents/template_agent/
\`\`\`
```

---

## 🔧 集成步骤

### 1. 注册到 `config/agents.yaml`

```yaml
agents:
  template:
    enabled: true
    name: "模板智能体"
    version: "1.0.0"
    description: "这是一个智能体模板"
    api_prefix: "/api/template"
```

### 2. 添加到 `shared/api/gateway.py`

```python
from agents.template_agent.api.endpoints import router as template_router

def create_app() -> FastAPI:
    app = FastAPI(...)
    
    # 注册模板智能体路由
    app.include_router(
        template_router,
        prefix="/api/template",
        tags=["模板智能体"]
    )
    
    return app
```

---

## 📋 创建脚本

将以下内容保存为 `create_agent.sh`：

```bash
#!/bin/bash

# 智能体名称（小写，下划线分隔）
AGENT_NAME=$1

if [ -z "$AGENT_NAME" ]; then
    echo "用法: ./create_agent.sh <agent_name>"
    exit 1
fi

# 创建目录结构
mkdir -p agents/${AGENT_NAME}/{api,llm,tools,config}

# 创建 __init__.py 文件
touch agents/${AGENT_NAME}/__init__.py
touch agents/${AGENT_NAME}/api/__init__.py
touch agents/${AGENT_NAME}/llm/__init__.py
touch agents/${AGENT_NAME}/tools/__init__.py
touch agents/${AGENT_NAME}/config/__init__.py

# 创建其他文件
touch agents/${AGENT_NAME}/config.py
touch agents/${AGENT_NAME}/README.md
touch agents/${AGENT_NAME}/api/endpoints.py
touch agents/${AGENT_NAME}/llm/agent.py
touch agents/${AGENT_NAME}/config/settings.json

echo "✅ 智能体 ${AGENT_NAME} 创建完成！"
echo "📁 位置: agents/${AGENT_NAME}/"
```

使用方法：
```bash
chmod +x create_agent.sh
./create_agent.sh my_agent
```

---

祝您开发顺利！🚀
