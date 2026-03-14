# labeleasy

YOLO 格式图像标注应用，支持边界框和关键点标注。

## 功能特性

- 支持 YOLO 格式标注文件读写
- 边界框 (BBox) 绘制与调整
- 关键点标注（键盘快捷键映射）
- 关键点拖动微调
- 骨架连线显示
- 多类别目标支持
- 自动保存功能
- 撤销/重做操作
- 关键点复制粘贴
- 最近项目记忆

## 项目结构

```
labeleasy/
├── __init__.py      # 包初始化
├── __main__.py      # 入口点
├── app.py           # 主窗口
├── canvas.py        # 画布组件
├── config.py        # 配置管理
├── constants.py     # 常量定义
├── dialogs.py       # 对话框
├── models.py        # 数据模型
├── utils.py         # 工具函数
└── icon.ico         # 应用图标
```

## 使用说明

### 环境要求

- Python 3.8+
- conda (推荐)

### 安装依赖

```bash
# 创建 conda 环境
conda create -n labeleasy python=3.9
conda activate labeleasy

# 安装依赖
pip install -r requirements.txt
```

### 运行应用

```bash
# 方式 1: 模块方式运行
python -m labeleasy

# 方式 2: 直接运行入口
python labeleasy/__main__.py
```

### 操作说明

#### 快捷键

| 快捷键 | 功能 |
|--------|------|
| ← / → | 上一张/下一张图片 |
| ↑ | 进入绘制边界框模式 |
| ↓ | 进入框选关键点模式 |
| Q-M | 选择对应关键点进行标注 |
| Ctrl+C | 复制关键点 |
| Ctrl+V | 粘贴关键点 |
| Ctrl+S | 保存 |
| Ctrl+Z | 撤销 |
| Ctrl+Shift+Z | 重做 |
| Delete | 删除选中 |
| Esc | 取消当前操作 |

#### 标注流程

1. 启动应用后选择模板文件 (YAML 格式)、图像目录、标签目录
2. 按↑键或点击"绘制框"按钮进入绘制模式，拖动绘制边界框
3. 选中标注框后，按 Q-M 键选择关键点类型，点击框内位置标注关键点
4. 拖动关键点可微调位置
5. 双击标注列表可修改类别或关键点可见性

#### 模板文件格式

```yaml
names:
  - person
  - car

keypoints:
  - head
  - left_hand
  - right_hand

skeleton:
  - [[0, 1], [0, 2]]  # head 连接 left_hand 和 right_hand
```

## 构建说明

### 构建要求

- 已安装所有依赖（包括 pyinstaller）

### Linux 构建

```bash
# 方式 1: 使用 shell 脚本
./build_linux.sh

# 方式 2: 使用 Python 脚本
python build.py linux
```

输出：`dist/labeleasy/labeleasy`

### Windows 构建

```batch
# 方式 1: 使用 bat 脚本
build_windows.bat

# 方式 2: 使用 Python 脚本
python build.py windows
```

输出：`dist/labeleasy/labeleasy.exe`

### 构建命令

```bash
python build.py          # 自动检测系统并构建
python build.py linux    # 构建 Linux 版本
python build.py windows  # 构建 Windows 版本
python build.py clean    # 清理构建缓存
```

### 输出结构

```
dist/labeleasy/
├── labeleasy       # 可执行文件
├── _internal/      # 资源文件夹
└── config.json     # 配置文件（运行后生成）
```

## 配置说明

配置文件存储在可执行文件同目录下的 `config.json`：

- `recent_projects`: 最近打开的项目列表
- `auto_save`: 自动保存开关
- `last_image`: 上次打开的图片路径

## 许可证

Apache License 2.0
