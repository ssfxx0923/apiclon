#!/bin/bash

echo "================================"
echo "AI API中继服务 - 启动脚本"
echo "================================"
echo ""

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python3，请先安装Python 3.8+"
    exit 1
fi

echo "[1/3] 检查依赖..."
if ! python3 -c "import fastapi" &> /dev/null; then
    echo "[2/3] 安装依赖..."
    pip3 install -r requirements.txt
else
    echo "[2/3] 依赖已安装"
fi

echo "[3/3] 启动服务..."
echo ""
echo "服务将在 http://localhost:8000 启动"
echo "按 Ctrl+C 停止服务"
echo ""

python3 main.py

