#!/bin/bash
# 启动脚本 (Linux/Mac/Git Bash)

echo "智能研报知识库检索 Agent - 启动脚本"
echo "=========================================="

# 检查 .env 文件是否存在
if [ ! -f ".env" ]; then
    echo "[ERROR] .env 文件不存在"
    echo "请复制 .env.example 为 .env 并填写 API Keys"
    echo ""
    echo "执行命令:"
    echo "  cp .env.example .env"
    echo ""
    exit 1
fi

# 检测 Python 命令
if command -v python &> /dev/null; then
    PYTHON_CMD=python
elif command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
else
    echo "[ERROR] 未找到 Python，请先安装 Python 3.10+"
    exit 1
fi

echo "使用 Python: $PYTHON_CMD"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "虚拟环境不存在，正在创建..."
    $PYTHON_CMD -m venv venv
    
    if [ $? -ne 0 ]; then
        echo "[ERROR] 虚拟环境创建失败"
        exit 1
    fi
    echo "虚拟环境创建成功"
fi

# 激活虚拟环境
echo "激活虚拟环境..."

# 智能检测虚拟环境路径（根据实际文件存在判断）
if [ -f "venv/Scripts/activate" ]; then
    # Windows (Git Bash/PowerShell)
    echo "检测到 Windows 环境"
    source venv/Scripts/activate
elif [ -f "venv/bin/activate" ]; then
    # Linux/Mac
    echo "检测到 Linux/Mac 环境"
    source venv/bin/activate
else
    echo "[ERROR] 找不到虚拟环境激活脚本"
    echo "venv/Scripts/activate 和 venv/bin/activate 都不存在"
    echo ""
    echo "请尝试删除 venv 目录后重新运行:"
    echo "  rm -rf venv"
    echo "  ./start.sh"
    exit 1
fi

if [ $? -ne 0 ]; then
    echo "[ERROR] 激活虚拟环境失败"
    echo ""
    echo "请手动激活虚拟环境后再运行:"
    if [ -f "venv/Scripts/activate" ]; then
        echo "  source venv/Scripts/activate"
    else
        echo "  source venv/bin/activate"
    fi
    echo "  $PYTHON_CMD -m pip install -r requirements.txt"
    echo "  $PYTHON_CMD main.py"
    exit 1
fi

# 安装依赖
echo "检查并安装依赖..."
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "[ERROR] 依赖安装失败"
    exit 1
fi

# 启动服务
echo ""
echo "启动 FastAPI 服务..."
echo "访问地址:"
echo "  - API 文档: http://localhost:8000/docs"
echo "  - 健康检查: http://localhost:8000/health"
echo ""

$PYTHON_CMD -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
