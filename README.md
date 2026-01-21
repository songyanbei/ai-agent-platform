# AI 智能体平台

一个可扩展的多智能体协作平台，支持在单一代码仓库中管理多个 AI 智能体。

## ✨ 特性

- 🎯 **模块化架构**：每个智能体独立开发和部署
- 🔌 **统一网关**：所有智能体通过统一服务访问
- 🛠️ **共享基础设施**：复用协议、工具和工具类
- 📦 **快速扩展**：5 分钟创建新智能体
- 🔄 **流式响应**：支持 SSE 实时数据流
- 📊 **Java 标准协议**：与后端无缝集成

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填写配置：

```bash
cp .env.example .env
```

编辑 `.env`：
```env
# 智谱 AI 配置
ZHIPU_API_KEY=your_zhipu_api_key
ZHIPU_KNOWLEDGE_ID=your_knowledge_base_id

# DeepSeek 配置
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

### 3. 启动服务

```bash
python main.py
```

服务将在 `http://localhost:8000` 启动。

### 4. 测试 API

```bash
curl -X POST http://localhost:8000/api/v2/query \
  -H "Content-Type: application/json" \
  -d '{"query": "人工智能在金融领域的应用"}'
```

## 📁 项目结构

```
ai-agent-platform/
├── main.py                    # 服务入口
├── config/                    # 全局配置
│   ├── settings.py
│   └── agents.yaml            # 智能体注册表
├── shared/                    # 共享基础设施
│   ├── protocols/             # 消息协议
│   ├── api/gateway.py         # API 网关
│   └── utils/                 # 工具类
├── agents/                    # 所有智能体
│   ├── base_agent.py
│   └── zhiku/                 # 知识检索智能体
│       ├── api/endpoints.py
│       ├── llm/               # LLM 组件
│       └── tools/             # 智能体工具
└── docs/                      # 文档
```

## 🤖 当前智能体

### 知识检索智能体 (Zhiku)

基于多知识库的智能检索和总结服务。

**功能**：
- 🎯 智能规划检索策略
- 🔍 并行多知识库检索
- 📝 生成带引用的总结报告

**API**：
- `POST /api/v2/query` - 查询接口（[详细文档](ZHIKU_API_SPECIFICATION.md)）

## 📚 文档

- **[API 规范](API_SPECIFICATION.md)** - 平台完整 API 接口文档
- **[开发指南](docs/DEVELOPMENT.md)** - 环境搭建、开发流程、部署指南
- **[架构文档](docs/ARCHITECTURE.md)** - 系统架构和设计原则
- **[智能体开发](docs/AGENT_DEVELOPMENT_GUIDE.md)** - 如何开发新智能体
- **[代码模板](docs/AGENT_TEMPLATE.md)** - 新智能体代码模板

## 🛠️ 开发新智能体

### 快速创建

```bash
# 1. 创建目录结构
mkdir -p agents/my_agent/{api,llm,tools,config}

# 2. 复制模板文件
# 参考 docs/AGENT_TEMPLATE.md

# 3. 在 config/agents.yaml 中注册
# 4. 在 shared/api/gateway.py 中添加路由
# 5. 实现业务逻辑
```

详细步骤请参考 [开发指南](docs/AGENT_DEVELOPMENT_GUIDE.md)。

## 🧪 测试

```bash
# 运行所有测试
pytest tests/

# 运行特定智能体测试
pytest tests/agents/zhiku/
```

## 📊 API 文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🔧 配置

### 全局配置 (`config/settings.py`)
- 环境变量加载
- API 密钥管理
- 服务器配置

### 智能体注册 (`config/agents.yaml`)
```yaml
agents:
  zhiku:
    enabled: true
    name: "知识检索智能体"
    version: "2.0.0"
    api_prefix: "/api/v2"
```

## 🌟 核心特性

### 1. 模块化架构
每个智能体独立开发，互不干扰。

### 2. 统一网关
所有智能体通过 API 网关统一管理。

### 3. 流式响应
支持 SSE (Server-Sent Events) 实时数据流。

### 4. 协议标准化
使用 Java 标准消息协议，与后端无缝集成。

## 🚧 开发中功能

- [ ] 智能体间通信机制
- [ ] 智能体市场
- [ ] 性能监控仪表板
- [ ] 多租户支持

## 📝 更新日志

### v2.0.0 (2026-01-16)
- ✨ 重构为多智能体架构
- 🔧 添加 API 网关
- 📚 完善开发文档
- 🎯 优化知识检索智能体

### v1.0.0
- 🎉 初始版本
- 🔍 知识检索功能

## 🤝 贡献

欢迎贡献新的智能体或改进现有功能！

## 📄 许可证

MIT License

## 📧 联系方式

如有问题或建议，请提交 Issue。

---

**开始构建您的智能体吧！** 🚀
