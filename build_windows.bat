@echo off
REM labeleasy Windows 构建脚本

echo ====================================
echo labeleasy Build Script for Windows
echo ====================================
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.8+
    pause
    exit /b 1
)

REM 检查是否在正确的目录
if not exist "labeleasy\__main__.py" (
    echo ERROR: Please run this script from the project root directory
    pause
    exit /b 1
)

echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Building application...
python build.py windows

echo.
echo ====================================
if exist "dist\labeleasy\labeleasy.exe" (
    echo Build successful!
    echo Output: dist\labeleasy\labeleasy.exe
) else (
    echo Build failed!
)
echo ====================================

pause