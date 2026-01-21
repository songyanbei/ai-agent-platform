# 启动脚本 (Windows PowerShell)

# 设置控制台编码为 UTF-8，避免中文乱码
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "智能研报知识库检索 Agent - 启动脚本" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 检查 .env 文件是否存在
if (-Not (Test-Path ".env")) {
    Write-Host "错误: .env 文件不存在" -ForegroundColor Red
    Write-Host "请复制 .env.example 为 .env 并填写 API Keys" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "执行命令:" -ForegroundColor Green
    Write-Host "  copy .env.example .env" -ForegroundColor White
    Write-Host ""
    exit 1
}

# 检查虚拟环境
if (-Not (Test-Path "venv")) {
    Write-Host "虚拟环境不存在，正在创建..." -ForegroundColor Yellow
    python -m venv venv
    Write-Host "虚拟环境创建成功" -ForegroundColor Green
}

# 激活虚拟环境
Write-Host "激活虚拟环境..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1

# 安装依赖
Write-Host "检查并安装依赖..." -ForegroundColor Yellow
pip install -r requirements.txt

# 启动服务
Write-Host ""
Write-Host "启动 FastAPI 服务..." -ForegroundColor Green
Write-Host "访问地址:" -ForegroundColor Cyan
Write-Host "  - API 文档: http://localhost:8000/docs" -ForegroundColor White
Write-Host "  - 健康检查: http://localhost:8000/health" -ForegroundColor White
Write-Host ""

python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
