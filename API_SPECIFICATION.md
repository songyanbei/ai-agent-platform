# AI 智能体平台 API 规范

**版本**: 2.0.0  
**最后更新**: 2026-01-19

---

## 📋 目录

1. [概述](#概述)
2. [通用规范](#通用规范)
3. [认证与授权](#认证与授权)
4. [API 端点](#api-端点)
5. [Java 标准协议](#java-标准协议)
6. [错误处理](#错误处理)
7. [示例代码](#示例代码)

---

## 🌐 概述

AI 智能体平台提供统一的 RESTful API 接口，支持多个智能体的访问和管理。所有接口遵循 Java 标准消息协议，使用 Server-Sent Events (SSE) 进行流式响应。

### 基础信息

- **基础 URL**: `http://your-domain:8000`
- **协议**: HTTP/HTTPS
- **响应格式**: JSON (标准请求) / SSE (流式响应)
- **字符编码**: UTF-8

### 支持的智能体

| 智能体 | 前缀 | 版本 | 状态 |
|--------|------|------|------|
| 知识检索智能体 (Zhiku) | `/api/v2` | 2.0.0 | ✅ 可用 |

---

## 🔧 通用规范

### 请求头

所有请求应包含以下请求头：

```http
Content-Type: application/json
Accept: text/event-stream  # 流式接口
```

### 响应格式

#### 标准 JSON 响应

```json
{
  "success": true,
  "data": {},
  "message": "操作成功"
}
```

#### SSE 流式响应

```
data: {"event_type": "...", "context": {...}, "messages": [...]}\n\n
```

### 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 400 | 请求参数错误 |
| 401 | 未授权 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |
| 502 | 网关错误 |
| 503 | 服务不可用 |

---

## 🔐 认证与授权

### API 密钥认证（计划中）

```http
Authorization: Bearer YOUR_API_KEY
```

> **注意**: 当前版本暂未启用认证，生产环境部署时请配置。

---

## 📡 API 端点

### 1. 健康检查

检查服务状态。

#### 请求

```http
GET /health
```

#### 响应

```json
{
  "status": "healthy",
  "version": "2.0.0",
  "timestamp": "2026-01-19T10:00:00Z"
}
```

---

### 2. 获取 API 文档

访问交互式 API 文档。

#### Swagger UI

```http
GET /docs
```

#### ReDoc

```http
GET /redoc
```

---

### 3. 知识检索查询

使用知识检索智能体进行查询和总结。

#### 请求

```http
POST /api/v2/query
Content-Type: application/json
```

**请求体**:

```json
{
  "query": "string"  // 必填，用户问题
}
```

**示例**:

```json
{
  "query": "人工智能在金融领域的应用趋势"
}
```

#### 响应

SSE 流式响应，详见 [Java 标准协议](#java-标准协议)。

**完整流程**:

1. `PLAN_DECLARED` - 声明所有阶段
2. `PLAN_CHANGE` - 规划阶段开始
3. `STREAM_THING` - 思考过程
4. `PLAN_CHANGE` - 规划阶段完成
5. `PLAN_CHANGE` - 检索阶段开始
6. `INVOCATION_DECLARED` - 声明检索调用
7. `INVOCATION_CHANGE` - 检索完成
8. `PLAN_CHANGE` - 检索阶段完成
9. `ARTIFACT_DECLARED` - 声明参考文献产物
10. `ARTIFACT_CHANGE` - 参考文献内容
11. `PLAN_CHANGE` - 总结阶段开始
12. `ARTIFACT_DECLARED` - 声明总结产物
13. `ARTIFACT_CHANGE` - 总结内容（流式）
14. `STREAM_CONTENT` - 总结性正文
15. `PLAN_CHANGE` - 总结阶段完成
16. `END` - 结束

详细文档请参考: [智库查询接口规范](ZHIKU_API_SPECIFICATION.md)

---

## 📊 Java 标准协议

### 消息结构

所有 SSE 消息遵循统一格式：

```json
{
  "event_type": "EVENT_TYPE",
  "context": {
    "mode": "plan-executor",
    "stage_id": "stage_name",
    ...
  },
  "messages": [
    {
      ...
    }
  ]
}
```

### 事件类型

#### 1. PLAN_DECLARED - 声明所有阶段

声明整个流程的所有阶段。

```json
{
  "event_type": "PLAN_DECLARED",
  "context": {
    "mode": "plan-executor"
  },
  "messages": [
    {
      "stages": [
        {
          "id": "planning",
          "name": "规划",
          "status": "PENDING"
        },
        {
          "id": "retrieval",
          "name": "检索",
          "status": "PENDING"
        },
        {
          "id": "summary",
          "name": "总结",
          "status": "PENDING"
        }
      ]
    }
  ]
}
```

**字段说明**:
- `stages`: 阶段列表
  - `id`: 阶段唯一标识
  - `name`: 阶段显示名称
  - `status`: 状态（PENDING | RUNNING | COMPLETED | FAILED）

---

#### 2. PLAN_CHANGE - 阶段状态变更

更新某个阶段的状态。

```json
{
  "event_type": "PLAN_CHANGE",
  "context": {
    "mode": "plan-executor",
    "stage_id": "planning"
  },
  "messages": [
    {
      "status": "RUNNING"
    }
  ]
}
```

**状态枚举**:
- `PENDING` - 待执行
- `RUNNING` - 执行中
- `COMPLETED` - 已完成
- `FAILED` - 失败

---

#### 3. STREAM_THING - 思考过程

流式输出思考过程或状态信息。

```json
{
  "event_type": "STREAM_THING",
  "context": {
    "mode": "plan-executor"
  },
  "messages": [
    {
      "content": "正在分析用户问题..."
    }
  ]
}
```

---

#### 4. STREAM_CONTENT - 正文内容

流式输出最终的正文内容。

```json
{
  "event_type": "STREAM_CONTENT",
  "context": {
    "mode": "plan-executor"
  },
  "messages": [
    {
      "content": "综上所述，"
    }
  ]
}
```

---

#### 5. INVOCATION_DECLARED - 声明调用

声明一个工具调用或子任务。

```json
{
  "event_type": "INVOCATION_DECLARED",
  "context": {
    "mode": "plan-executor",
    "stage_id": "retrieval",
    "invocation_id": "inv_12345"
  },
  "messages": [
    {
      "name": "正在查询知识库: 人工智能",
      "invocation_type": "SEARCH"
    }
  ]
}
```

**invocation_type 枚举**:
- `SEARCH` - 搜索
- `TOOL_CALL` - 工具调用
- `API_CALL` - API 调用

---

#### 6. INVOCATION_CHANGE - 调用变更

更新调用状态或返回结果。

```json
{
  "event_type": "INVOCATION_CHANGE",
  "context": {
    "mode": "plan-executor",
    "stage_id": "retrieval",
    "invocation_id": "inv_12345"
  },
  "messages": [
    {
      "status": "COMPLETED",
      "content": "{\"success\": true, \"doc_count\": 5}"
    }
  ]
}
```

---

#### 7. ARTIFACT_DECLARED - 产物声明

声明一个产物（文件、数据等）。

```json
{
  "event_type": "ARTIFACT_DECLARED",
  "context": {
    "mode": "plan-executor",
    "artifact_id": "references-001",
    "stage_id": "summary"
  },
  "messages": [
    {
      "scope": "STAGE",
      "data_type": "STRUCTURED",
      "source": "知识库检索",
      "artifact_name": "参考文献",
      "artifact_type": "reference_list",
      "content": ""
    }
  ]
}
```

**字段说明**:
- `scope`: 作用域（STAGE | GLOBAL）
- `data_type`: 数据类型（FILE | STRUCTURED）
- `artifact_type`: 产物类型（reference_list | summary_report | ...）

---

#### 8. ARTIFACT_CHANGE - 产物变更

追加或修改产物内容。

```json
{
  "event_type": "ARTIFACT_CHANGE",
  "context": {
    "mode": "plan-executor",
    "artifact_id": "summary-content-001",
    "stage_id": "summary"
  },
  "messages": [
    {
      "scope": "STAGE",
      "change_type": "CONTENT_APPEND",
      "data_type": "FILE",
      "content": "根据检索结果，"
    }
  ]
}
```

**change_type 枚举**:
- `CONTENT_APPEND` - 追加内容
- `CONTENT_REPLACE` - 替换内容
- `METADATA_UPDATE` - 更新元数据

---

#### 9. END - 结束

标记流程结束。

```json
{
  "event_type": "END",
  "context": {
    "mode": "plan-executor"
  },
  "messages": []
}
```

---

### 协议辅助函数

平台提供了协议构建函数，位于 `shared/protocols/java_protocol.py`：

```python
from shared.protocols.java_protocol import (
    build_plan_declared,
    build_plan_change_status,
    build_stream_thing,
    build_stream_content,
    build_invocation_declared,
    build_invocation_complete,
    build_artifact,
    build_artifact_change,
    build_end
)
```

---

## ❌ 错误处理

### 错误响应格式

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述",
    "details": {}
  }
}
```

### 常见错误码

| 错误码 | HTTP 状态 | 说明 |
|--------|-----------|------|
| `INVALID_REQUEST` | 400 | 请求参数无效 |
| `MISSING_FIELD` | 400 | 缺少必填字段 |
| `UNAUTHORIZED` | 401 | 未授权访问 |
| `NOT_FOUND` | 404 | 资源不存在 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |
| `SERVICE_UNAVAILABLE` | 503 | 服务不可用 |

### SSE 错误事件

在流式响应中，错误通过特殊事件传递：

```json
{
  "event_type": "STREAM_THING",
  "context": {
    "mode": "plan-executor"
  },
  "messages": [
    {
      "content": "❌ 错误: 连接超时"
    }
  ]
}
```

---

## 💻 示例代码

### Python 客户端

```python
import httpx
import json
import asyncio

async def query_zhiku(question: str):
    """查询知识检索智能体"""
    url = "http://localhost:8000/api/v2/query"
    data = {"query": question}
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("POST", url, json=data) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    event = json.loads(line[6:])
                    handle_event(event)

def handle_event(event: dict):
    """处理 SSE 事件"""
    event_type = event.get("event_type")
    
    if event_type == "PLAN_DECLARED":
        print("📋 阶段声明:", event["messages"][0]["stages"])
    
    elif event_type == "PLAN_CHANGE":
        stage_id = event["context"]["stage_id"]
        status = event["messages"][0]["status"]
        print(f"🔄 {stage_id}: {status}")
    
    elif event_type == "STREAM_THING":
        print(f"💭 {event['messages'][0]['content']}")
    
    elif event_type == "ARTIFACT_CHANGE":
        content = event["messages"][0]["content"]
        print(content, end="", flush=True)
    
    elif event_type == "END":
        print("\n✅ 完成")

# 运行
asyncio.run(query_zhiku("人工智能在金融领域的应用"))
```

---

### JavaScript 客户端

```javascript
async function queryZhiku(question) {
  const response = await fetch('http://localhost:8000/api/v2/query', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ query: question })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const event = JSON.parse(line.slice(6));
        handleEvent(event);
      }
    }
  }
}

function handleEvent(event) {
  const eventType = event.event_type;

  switch (eventType) {
    case 'PLAN_DECLARED':
      console.log('📋 阶段声明:', event.messages[0].stages);
      break;
    
    case 'ARTIFACT_CHANGE':
      const content = event.messages[0].content;
      process.stdout.write(content);
      break;
    
    case 'END':
      console.log('\n✅ 完成');
      break;
  }
}
```

---

### cURL 测试

```bash
# 基本查询
curl -X POST http://localhost:8000/api/v2/query \
  -H "Content-Type: application/json" \
  -d '{"query": "人工智能在金融领域的应用"}' \
  --no-buffer

# 健康检查
curl http://localhost:8000/health
```

---

## 📚 相关文档

- **[智库查询接口详细规范](ZHIKU_API_SPECIFICATION.md)** - 知识检索智能体完整文档
- **[架构文档](docs/ARCHITECTURE.md)** - 系统架构设计
- **[开发指南](docs/DEVELOPMENT.md)** - 开发环境搭建和流程
- **[智能体开发指南](docs/AGENT_DEVELOPMENT_GUIDE.md)** - 新智能体开发教程

---

## 🔄 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 2.0.0 | 2026-01-19 | 完整的平台级 API 规范 |
| 1.0.0 | 2026-01-16 | 初始版本 |

---

## 📧 支持

如有问题或建议，请提交 Issue 或联系开发团队。

**文档维护**: AI Research Team  
**最后更新**: 2026-01-19
