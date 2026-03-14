#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
labeleasy 构建脚本
支持 Linux 和 Windows
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

APP_NAME = "labeleasy"
MAIN_SCRIPT = "labeleasy"
VERSION = "2.0.0"
ICON_PATH = "labeleasy/icon.ico"


def clean():
    print("Cleaning build artifacts...")
    dirs_to_remove = ["build", "dist", "__pycache__"]
    for d in dirs_to_remove:
        if os.path.exists(d):
            shutil.rmtree(d)
            print(f"  Removed: {d}")
    
    for root, dirs, files in os.walk("."):
        for d in dirs:
            if d == "__pycache__":
                p = os.path.join(root, d)
                shutil.rmtree(p)
                print(f"  Removed: {p}")
    
    spec_file = f"{APP_NAME}.spec"
    if os.path.exists(spec_file):
        os.remove(spec_file)
        print(f"  Removed: {spec_file}")
    
    print("Clean completed.")


def build_linux():
    print("Building for Linux...")
    
    cmd = [
        "pyinstaller",
        "--name", APP_NAME,
        "--onedir",
        "--windowed",
        "--clean",
        f"--add-data", f"{MAIN_SCRIPT}{os.pathsep}{MAIN_SCRIPT}",
        "--hidden-import", "PySide6",
        "--hidden-import", "PySide6.QtCore",
        "--hidden-import", "PySide6.QtGui",
        "--hidden-import", "PySide6.QtWidgets",
        "--hidden-import", "cv2",
        "--hidden-import", "numpy",
        "--hidden-import", "yaml",
        "-y",
        f"{MAIN_SCRIPT}/__main__.py"
    ]
    
    if os.path.exists(ICON_PATH):
        cmd.extend(["--icon", ICON_PATH])
        print(f"Using icon: {ICON_PATH}")
    
    subprocess.run(cmd, check=True)
    
    output_dir = Path("dist") / APP_NAME
    if sys.platform == "win32":
        exe_path = output_dir / f"{APP_NAME}.exe"
    else:
        exe_path = output_dir / APP_NAME
    
    if exe_path.exists():
        print(f"\nBuild successful!")
        print(f"Output directory: {output_dir.absolute()}")
        print(f"Executable: {exe_path.absolute()}")
    else:
        print("Build failed!")
        sys.exit(1)


def build_windows():
    print("Building for Windows...")
    
    cmd = [
        "pyinstaller",
        "--name", APP_NAME,
        "--onedir",
        "--windowed",
        "--clean",
        f"--add-data", f"{MAIN_SCRIPT};{MAIN_SCRIPT}",
        "--hidden-import", "PySide6",
        "--hidden-import", "PySide6.QtCore",
        "--hidden-import", "PySide6.QtGui",
        "--hidden-import", "PySide6.QtWidgets",
        "--hidden-import", "cv2",
        "--hidden-import", "numpy",
        "--hidden-import", "yaml",
        "-y",
        f"{MAIN_SCRIPT}/__main__.py"
    ]
    
    if os.path.exists(ICON_PATH):
        cmd.extend(["--icon", ICON_PATH])
        print(f"Using icon: {ICON_PATH}")
    
    subprocess.run(cmd, check=True)
    
    output_dir = Path("dist") / APP_NAME
    exe_path = output_dir / f"{APP_NAME}.exe"
    
    if exe_path.exists():
        print(f"\nBuild successful!")
        print(f"Output directory: {output_dir.absolute()}")
        print(f"Executable: {exe_path.absolute()}")
    else:
        print("Build failed!")
        sys.exit(1)


def build():
    if sys.platform == "win32":
        build_windows()
    else:
        build_linux()


def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "clean":
            clean()
        elif arg == "build":
            build()
        elif arg == "linux":
            build_linux()
        elif arg == "windows":
            build_windows()
        else:
            print(f"Unknown command: {arg}")
            print("Usage: python build.py [clean|build|linux|windows]")
            sys.exit(1)
    else:
        clean()
        build()


if __name__ == "__main__":
    main()