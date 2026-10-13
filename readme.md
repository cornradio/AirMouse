# Remote Touchpad & Keyboard
内部代号：feishu（飞鼠）

这是一个基于 Python 后端的轻量级远程控制工具，可将移动设备（Android/iOS）转化为电脑的：触控板、键盘、语音输入工具、宏按键面板。

<table style="border: none;">
  <tr style="border: none;">
    <td style="border: none;">
      <img src="img/Screenshot_20260120-225705.jpg" width="400">
    </td>
    <td style="border: none;">
      <img src="img/Screenshot_20260123-224640.jpg" width="400">
    </td>
    <td style="border: none;">
      <img src="img/Screenshot_20260121-210258.jpg" width="400">
    </td>
    <td style="border: none;">
      <img src="img/Screenshot_20260123-224503.jpg" width="400">
    </td>
  </tr>
</table>

2026 03 22
增加手柄映射功能
<img width="2274" height="1263" alt="image" src="https://github.com/user-attachments/assets/64ea98af-8477-4033-88f0-90103079fd03" />


## 🌟 项目亮点

### 1. 简单启动
python一键启动，无需安装手机客户端。

### 2. 触控操作

* **单指**：移动 / 左键单击。
* **双指**：滚动 / 右键单击。
* **三指**：拖拽 / 中键单击。
* **gyro**：陀螺仪飞鼠

并且有提供鼠标前进、后退、中键、上下滚轮的按钮。



## 🛠️ 要求

* **uv**（推荐，由 uv 按项目配置管理 Python 和依赖）
* 手动使用系统 Python 时需要 **Python 3.10 或更高版本**；默认版本见 `.python-version`（当前为 Python 3.11）

## 🚀 快速启动

### 使用 uv（推荐）

先根据 [uv 官方安装说明](https://docs.astral.sh/uv/getting-started/installation/)安装 uv，然后在项目根目录运行：

```bash
uv sync
```

`uv sync` 会读取 `pyproject.toml` 和 `uv.lock`，创建项目虚拟环境 `.venv` 并安装锁定的依赖；项目中的 `.python-version` 指定 Python 3.11。之后启动服务：

```bash
uv run python server.py
```

也可以通过 `pyproject.toml` 声明的命令启动：

```bash
uv run airmouse
```

在 macOS/Linux 上打开控制台并禁用托盘：

```bash
AIRMOUSE_NO_TRAY=1 AIRMOUSE_SHOW_CONSOLE=1 uv run python server.py
```

Windows PowerShell 对应写法：

```powershell
$env:AIRMOUSE_NO_TRAY = "1"
$env:AIRMOUSE_SHOW_CONSOLE = "1"
uv run python server.py
```

### 调试与运行选项

开启输入事件调试日志：

```bash
DEBUG=1 AIRMOUSE_NO_TRAY=1 AIRMOUSE_SHOW_CONSOLE=1 uv run python server.py
```

Windows PowerShell：

```powershell
$env:DEBUG = "1"
$env:AIRMOUSE_NO_TRAY = "1"
$env:AIRMOUSE_SHOW_CONSOLE = "1"
uv run python server.py
```

`DEBUG=1` 时控制台会记录鼠标/键盘 Socket.IO 事件及实际发送的 Quartz 事件；文本输入只记录字符数，不记录文本内容。调试结束后，可在 PowerShell 用 `$env:DEBUG = $null` 清除变量。

默认使用 HTTPS；如果仅需 HTTP（陀螺仪 gyro 将不可用），macOS/Linux 可运行：

```bash
AIRMOUSE_HTTP=1 uv run python server.py
```

PowerShell 可先运行 `$env:AIRMOUSE_HTTP = "1"`，然后执行 `uv run python server.py`。

### 其他启动方式

* Windows 桌面托盘：安装 Python 3.11 后双击 `AirMouseserver.bat`，脚本会检查依赖并启动服务。首次检查会生成 `deps_ok.txt`；需要重新检查时删除此文件。
* 手动使用系统 Python：`python -m pip install -r requirments.txt`，然后运行 `python server.py`。
* 添加或移除项目依赖：使用 `uv add 包名` 或 `uv remove 包名`，并保持 `pyproject.toml` 与 `uv.lock` 同步。
* 安装打包用的可选开发依赖：`uv sync --extra dev`。

如需控制高权限程序，请使用管理员权限启动服务。

**连接**：
确保手机与电脑在同一局域网，访问电脑 IP 的端口（默认 5888）。

从主页右上角进入扫码连接页；页面使用 qrcodejs CDN 在浏览器端生成二维码，不会在手机端安装任何应用。

例如： http://192.168.31.18:5888/ 

注意，浏览器会提示网页不安全，需要手工点进去信任，因为我们用的是自签的证书
> CHROME 浏览器安全限制，只有https网页才能传输陀螺仪数据。

---

## 📂 项目结构

* `server.py`: Python 后端逻辑，处理 Socket 信号并调用系统接口。
* `templates/index.html`: 触控板页面。
* `templates/keyboard.html`: 键盘输入页面。
* `templates/voice.html`: 语音输入页面。
* `macro.html`: 宏按键页面。
* `macro_config.json`: 宏按键配置文件。
---

## 🔧 调优说明
- 建议使用安卓手机+chrome浏览器。
- 虽然 ios  safari 浏览器也可以正常使用，但是鼠标的移动会变得卡卡的。

# macos相关
使用mac版本需要线修改一些py代码，才能正常使用。
```py
# 删除printscreen键

SPECIAL_KEYS = {
    'ctrl': Key.ctrl, 'ctrl_r': Key.ctrl_r,
    'shift': Key.shift, 'shift_r': Key.shift_r,
    'alt': Key.alt, 'alt_r': Key.alt_r,
    'win': Key.cmd, 'command': Key.cmd, 'meta': Key.cmd,
    'enter': Key.enter, 'esc': Key.esc, 'tab': Key.tab, 'backspace': Key.backspace,
    'space': Key.space, 'delete': Key.delete,
    'up': Key.up, 'down': Key.down, 'left': Key.left, 'right': Key.right,
    'f1': Key.f1, 'f2': Key.f2, 'f3': Key.f3, 'f4': Key.f4, 'f5': Key.f5, 'f6': Key.f6,
    'f7': Key.f7, 'f8': Key.f8, 'f9': Key.f9, 'f10': Key.f10, 'f11': Key.f11, 'f12': Key.f12
}

# 修改滚动方向,它滚动方向和 Windows 是反过来的
@socketio.on('scroll')
def handle_scroll(data):
    # 处理双指滑动或按钮连发发来的滚动信号
    mouse.scroll(0, -data['dy']) 
```

    
## 更新日志
2026-01-23 Day3
- [x]  两个手指快速抬起导致识别成鼠标跳转修复
- [x]  “单指长按拖拽”功能
- [x]  将触控板逻辑提取为独立模块 `touchpad.js`，实现多页面同步更新


2026-01-21 Day2
- [x]  点击返回时强制清除所有长按功能，以防止影响触控
- [x]  飞鼠增加一些微小动作滤除，防手抖

- [x]  键盘上下左右 无效 另外位置也不舒服
- [x]  键盘del 按钮位置不对 应该在F12右边
- [x]  缺少printscreen 按钮
- [x]  缺少反斜杠按钮（在括号右边）

- [x]  输入条太小并不能实时语音上屏（之前让他实时上屏存在一点问题）
- [x]  或许我可以再搞个独立页面专门用来语音上屏,并且可以切换实时上屏和输入框模式
- [x]  记住gyro模式，如果之前是开启那么回到页面自动开启
- [x]  键盘模式默认就横过来展示，无视手机的方向（如果检测到是手机）
  
2026-01-21 Day1
- [x]  实现整体基础架构
- [x]  实现飞鼠功能还有鼠标控制功能以及三指拖动功能等
- [x]  实现键盘功能
