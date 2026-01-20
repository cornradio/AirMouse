# Remote Touchpad & Keyboard
内部代号：feishu（飞鼠）

这是一个基于 Python 后端的轻量级远程控制工具，可将移动设备（Android/iOS）转化为电脑的**无线触控板**与**多功能键盘**。

<table style="border: none;">
  <tr style="border: none;">
    <td style="border: none;">
      <img src="img/Screenshot_20260120-225709.jpg" width="400">
    </td>
    <td style="border: none;">
      <img src="img/Screenshot_20260120-225705.jpg" width="400">
    </td>
  </tr>
</table>

## 🌟 项目亮点

### 1. 简单启动
python一键启动 无需安装

### 2. 全键盘
提供完整的全键盘、并且支持组合键输入。

### 3. 经典触控操作

* 保留了最稳健的第一版触控逻辑：
* **单指**：移动 / 左键单击。
* **双指**：滚动 / 右键单击。
* **三指**：拖拽。

### 4. gyro
陀螺仪飞鼠。
/gyro/t-help.html 
但是在任何的非https页面上，无法启动。


---

## 🛠️ 要求

* **Python 3.x**
* **依赖库**：好几个依赖。

---

## 🚀 快速启动

1. **安装依赖**：
```bash
pip install -r requirements.txt
```


2. **运行服务端**：
```bash
python server.py
```

如果你是macos，你要修改一下，主要滚动它和 Windows 是反过来的
```bash
@socketio.on('scroll')
def handle_scroll(data):
    # 处理双指滑动或按钮连发发来的滚动信号
    mouse.scroll(0, -data['dy']) # 这里改成 -data['dy'] 就可以了
```

1. **连接**：
确保手机与电脑在同一局域网，访问电脑 IP 的端口（默认 5888）。
例如： http://192.168.31.18:5888/ 

注意，可能会提示网页不安全，需要手工点进去信任，因为我们用的是自签的证书。

---

## 📂 项目结构

* `server.py`: Python 后端逻辑，处理 Socket 信号并调用系统接口。
* `templates/index.html`: 触控板页面（包含灵敏度持久化与横屏适配）。
* `templates/keyboard.html`: 键盘输入页面（包含防挤压布局与全屏控制）。

---

## 🔧 调优说明

如果你觉得按钮滚动的步长不够快，可以在 `index.html` 中找到以下部分进行修改：

```javascript
function startScroll(step) {
    // step 为正数向上滚，负数向下滚
    // 60ms 是触发频率，2 是单次滚动步长
    scrollTimer = setInterval(() => socket.emit('scroll', { dy: step }), 60); 
}

```

