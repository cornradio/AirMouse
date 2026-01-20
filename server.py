import socket
import psutil
from flask import Flask, render_template
from flask_socketio import SocketIO
from pynput.mouse import Controller, Button
from pynput.keyboard import Controller as KeyController, Key

app = Flask(__name__)
# 允许所有来源跨域，确保手机能连上
socketio = SocketIO(app, cors_allowed_origins="*")

# 实例化硬件控制器
mouse = Controller()
keyboard = KeyController()

# 特殊按键映射表
SPECIAL_KEYS = {
    'ctrl': Key.ctrl, 'shift': Key.shift, 'alt': Key.alt, 'win': Key.cmd,
    'enter': Key.enter, 'esc': Key.esc, 'tab': Key.tab, 'backspace': Key.backspace,
    'space': Key.space,
    'f1': Key.f1, 'f2': Key.f2, 'f3': Key.f3, 'f4': Key.f4, 'f5': Key.f5, 'f6': Key.f6,
    'f7': Key.f7, 'f8': Key.f8, 'f9': Key.f9, 'f10': Key.f10, 'f11': Key.f11, 'f12': Key.f12
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/k')
def keyboard_page(): 
    return render_template('keyboard.html')
@app.route('/t')
def air_mouse_test():
    return render_template('t.html')
    
# --- 鼠标控制逻辑 ---
@socketio.on('move')
def handle_move(data):
    # dx, dy 由前端根据灵敏度计算后传入
    mouse.move(data['dx'], data['dy'])

@socketio.on('click')
def handle_click(data):
    btn = Button.right if data.get('button') == 'right' else Button.left
    mouse.click(btn)

@socketio.on('drag_start')
def handle_drag_start():
    # 三指按下：先释放再按住左键进入拖拽状态
    mouse.release(Button.left)
    mouse.press(Button.left)

@socketio.on('drag_end')
def handle_drag_end():
    # 三指抬起：释放左键
    mouse.release(Button.left)

@socketio.on('scroll')
def handle_scroll(data):
    # 处理双指滑动或按钮连发发来的滚动信号
    mouse.scroll(0, data['dy'])

# --- 键盘控制逻辑 ---
@socketio.on('type_text')
def handle_type(data):
    # 处理输入框发送的整段文字
    keyboard.type(data['text'])

@socketio.on('key_action')
def handle_key_action(data):
    # 处理单个按键的按下或抬起（如 Shift, Ctrl）
    action = data['action'] # 'down' 或 'up'
    key_code = data['key'].lower()
    
    if key_code in SPECIAL_KEYS:
        target_key = SPECIAL_KEYS[key_code]
        if action == 'down':
            keyboard.press(target_key)
        else:
            keyboard.release(target_key)
    elif len(key_code) == 1:
        if action == 'down':
            keyboard.press(key_code)
        else:
            keyboard.release(key_code)

@socketio.on('key_combo')
def handle_combo(data):
    # 处理组合快捷键（宏）
    keys = data['keys']
    for k in keys:
        target = SPECIAL_KEYS.get(k.lower(), k.lower())
        keyboard.press(target)
    for k in reversed(keys):
        target = SPECIAL_KEYS.get(k.lower(), k.lower())
        keyboard.release(target)

# --- 自动获取局域网 IP 逻辑 ---
def get_all_ip_addresses():
    ip_list = []
    for interface, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                ip_list.append((interface, addr.address))
    return ip_list

if __name__ == '__main__':
    port = 5888
    ips = get_all_ip_addresses()
    
    print("\n" + "═"*60)
    print("🚀 Remote Pro Server (Python版) 已启动！")
    print("📱 请确保手机与电脑在同一 WiFi，并尝试访问以下地址:")
    
    for interface, ip in ips:
        # 简单标记物理网卡
        tag = ""
        if any(keyword in interface.lower() for keyword in ["wlan", "wi-fi", "eth", "en0", "en1"]):
            tag = " [推荐]"
        print(f"  ➤  http://{ip}:{port}{tag}")
    
    print("═"*60 + "\n")
    
    # 使用 allow_unsafe_werkzeug 确保在开发环境下稳定运行
    socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)