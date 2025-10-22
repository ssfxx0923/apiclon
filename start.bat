@echo off
chcp 65001 >nul
echo ================================
echo AI API中继服务 - 启动脚本
echo ================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

echo [1/3] 检查依赖...
pip show fastapi >nul 2>&1
if %errorlevel% neq 0 (
    echo [2/3] 安装依赖...
    pip install -r requirements.txt
) else (
    echo [2/3] 依赖已安装
)

echo [3/3] 启动服务...
echo.
echo 服务将在 http://localhost:8000 启动
echo 按 Ctrl+C 停止服务
echo.

python main.py
pause

