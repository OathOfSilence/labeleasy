# labeleasy

YOLO 格式图像标注应用，支持边界框和关键点标注，也支持纯目标检测（无关键点）模式。

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
- 框选关键点模式（支持 Ctrl+ 点击切换选中状态）
- **纯目标检测模式**（模板无关键点时自动启用）
- **框选边复制粘贴**（跨图对齐边框）
- **快捷键快速创建检测框**
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
├── icon.ico         # 应用图标
└── modes/           # 标注模式模块
    ├── __init__.py  # 模块导出
    ├── base.py      # 模式基类
    ├── keypoint.py  # 关键点模式
    ├── edge.py      # 框选边模式
    └── drawing.py   # 绘制框模式
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

| 快捷键 | 功能（有关键点） | 功能（无关键点/纯检测模式） |
|--------|-----------------|---------------------------|
| ← / → | 上一张/下一张图片 | 上一张/下一张图片 |
| ↑ | 绘制边界框 | 绘制边界框 |
| ↓ | 框选关键点 | **框选边**（需先选中标注框） |
| Q-M / 1-0 等 | **绘制对应关键点** | **绘制对应类别的检测框** |
| Ctrl+C | 复制关键点 | 复制边 |
| Ctrl+V | 粘贴关键点 | 粘贴边 |
| Ctrl+S | 保存 | 保存 |
| Ctrl+Z | 撤销 | 撤销 |
| Ctrl+Shift+Z | 重做 | 重做 |
| Delete | 删除选中 | 删除选中 |
| Esc | 取消当前操作 | 取消当前操作 |
| **Ctrl + 鼠标点击** | 切换关键点/边选中状态 | 切换边选中状态 |

#### 标注流程（关键点模式）

1. 启动应用后选择模板文件 (YAML 格式)、图像目录、标签目录
2. 按↑键或点击"绘制框"按钮进入绘制模式，拖动绘制边界框
3. 选中标注框后，**按快捷键选择关键点类型，点击位置放置关键点**
4. **拖动关键点**可微调位置
5. 按↓键进入**框选关键点模式**，拖动框选多个关键点
6. **Ctrl+ 点击**切换单个关键点选中状态
7. **Ctrl+C/V** 复制/粘贴关键点
8. 双击标注列表可修改类别或关键点可见性

#### 标注流程（纯目标检测模式/无关键点）

当模板 YAML 文件不包含 `keypoints` 字段时，自动进入纯目标检测模式：

1. 启动应用后选择模板文件（仅需 `names` 字段）、图像目录、标签目录
2. 右侧列表显示**类别列表**（带快捷键）
3. **按类别快捷键** → 进入绘制模式，预设类别，拖动创建检测框
4. **点击右侧类别列表** → 进入绘制模式，预设类别，拖动创建检测框
5. 选中一个标注框后，按↓键进入**框选边模式**
6. **拖动框选** → 选择框内的边（青色高亮显示）
7. **Ctrl+ 点击边** → 切换单条边的选中状态
8. **Ctrl+C** → 复制选中的边信息
9. 切换到其他图片，选中目标标注框
10. **Ctrl+V** → 粘贴边信息（自动检测冲突，如左边 x >= 右边 x 则拒绝）

#### 模板文件格式（关键点模式）

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

#### 模板文件格式（纯目标检测模式）

```yaml
names:
  - person
  - car
  - dog
  - cat

# 不包含 keypoints 字段 → 自动进入纯目标检测模式
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