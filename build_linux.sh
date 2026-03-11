#!/bin/bash
# labeleasy Linux 构建脚本

echo "===================================="
echo "labeleasy Build Script for Linux"
echo "===================================="
echo

# 检查 Python 是否安装
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 not found. Please install Python 3.8+"
    exit 1
fi

# 检查是否在正确的目录
if [ ! -f "labeleasy/__main__.py" ]; then
    echo "ERROR: Please run this script from the project root directory"
    exit 1
fi

echo "Installing dependencies..."
pip install -r requirements.txt

echo
echo "Building application..."
python3 build.py linux

echo
echo "===================================="
if [ -f "dist/labeleasy/labeleasy" ]; then
    echo "Build successful!"
    echo "Output: dist/labeleasy/labeleasy"
else
    echo "Build failed!"
fi
echo "===================================="