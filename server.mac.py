import os
from OpenSSL import crypto
import socket
import psutil
import json
import time
import threading
from flask import Flask, render_template
from flask_socketio import SocketIO
from pynput.mouse import Controller, Button
from pynput.keyboard import Controller as KeyController, Key

app = Flask(__name__)
# 允许所有来源跨域，确保手机能连上
socketio = SocketIO(app, cors_allowed_origins="*")

import platform

# 实例化硬件控制器
mouse = Controller()
keyboard = KeyController()

@socketio.on('connect')
def handle_connect():
    # 发送服务器操作系统信息给前端
    os_type = platform.system() # 'Windows', 'Darwin' (Mac), 'Linux'
    socketio.emit('os_info', {'os': os_type})

# 特殊按键映射表
SPECIAL_KEYS = {
    'ctrl': Key.ctrl, 'ctrl_r': Key.ctrl_r,
    'shift': Key.shift, 'shift_r': Key.shift_r,
    'alt': Key.alt, 'alt_r': Key.alt_r,
    'win': Key.cmd, 'command': Key.cmd, 'meta': Key.cmd,
    'enter': Key.enter, 'esc': Key.esc, 'tab': Key.tab, 'backspace': Key.backspace,
    'space': Key.space, 'delete': Key.delete, 'up': Key.up, 'down': Key.down, 'left': Key.left, 'right': Key.right,
    'f1': Key.f1, 'f2': Key.f2, 'f3': Key.f3, 'f4': Key.f4, 'f5': Key.f5, 'f6': Key.f6,
    'f7': Key.f7, 'f8': Key.f8, 'f9': Key.f9, 'f10': Key.f10, 'f11': Key.f11, 'f12': Key.f12,
    # 符号别名
    'comma': ',', 'dot': '.', 'slash': '/', 'semicolon': ';', 'quote': "'", 'bracket_l': '[', 'bracket_r': ']'
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/k')
def keyboard_page(): 
    return render_template('keyboard.html')
@app.route('/v')
def voice_page():
    return render_template('voice.html')
@app.route('/test')
def vibe_test():
    return render_template('vibe_test.html')
@app.route('/t')
def air_mouse_test():
    return render_template('t.html')
@app.route('/r')
def real_mouse_page():
    return render_template('realmouse.html')
@app.route('/b')
def buttons_page():
    return render_template('buttons.html')

# --- 宏按键配置存储逻辑 ---
CONFIG_FILE = "macro_configs.json"

@socketio.on('load_macros')
def handle_load_macros():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            configs = json.load(f)
            socketio.emit('macros_loaded', configs)
    else:
        socketio.emit('macros_loaded', None)

@socketio.on('save_macros')
def handle_save_macros(data):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print("宏按键配置已保存到服务端")

# --- 鼠标控制逻辑 ---
@socketio.on('move')
def handle_move(data):
    # dx, dy 由前端根据灵敏度计算后传入
    mouse.move(data['dx'], data['dy'])

@socketio.on('click')
def handle_click(data):
    button_type = data.get('button')
    if button_type == 'left':
        mouse.click(Button.left)
    elif button_type == 'right':
        mouse.click(Button.right)
    elif button_type == 'middle':
        # 释放并点击中键，用于关闭浏览器标签页或自动滚动
        mouse.click(Button.middle)
    elif button_type == 'x1':
        # 侧键1 (通常是后退)
        mouse.click(Button.x1)
    elif button_type == 'x2':
        # 侧键2 (通常是前进)
        mouse.click(Button.x2)

@socketio.on('drag_start')
def handle_drag_start():
    # 三指按下：先释放再按住左键进入拖拽状态
    mouse.release(Button.left)
    mouse.press(Button.left)

@socketio.on('drag_end')
def handle_drag_end():
    # 三指抬起：释放左键
    mouse.release(Button.left)

@socketio.on('mid_down')
def handle_mid_down():
    # 按下中键
    mouse.release(Button.middle)
    mouse.press(Button.middle)

@socketio.on('mid_up')
def handle_mid_up():
    # 释放中键
    mouse.release(Button.middle)

@socketio.on('scroll')
def handle_scroll(data):
    # 处理双指滑动或按钮连发发来的滚动信号
    mouse.scroll(0, -data['dy'])

# --- 键盘控制逻辑 ---
@socketio.on('type_text')
def handle_type(data):
    # 处理输入框发送的整段文字
    keyboard.type(data['text'])

# 存储当前正在按下的键及其重复触发的标志
active_repeats = {} # {key_code: stop_event}

def repeat_key(key_obj, stop_event):
    """模拟系统自动重复按键的线程"""
    # 先发一次初始按下
    keyboard.press(key_obj)
    # 系统的第一个重复延迟通常较久 (500ms)
    if stop_event.wait(0.4): return
    
    while not stop_event.is_set():
        keyboard.press(key_obj)
        # 之后的连发频率 (约 30Hz)
        if stop_event.wait(0.05): break

@socketio.on('key_action')
def handle_key_action(data):
    # 处理单个按键的按下或抬起（如 Shift, Ctrl）
    action = data['action'] # 'down' 或 'up'
    key_code = data['key'].lower().strip()
    
    # 确定目标按键对象
    target_key = SPECIAL_KEYS.get(key_code, key_code)

    if action == 'down':
        # 如果这个键已经在连发了，先不管（或者你可以选择重新开始）
        if key_code in active_repeats:
            return
            
        # 所有的单键操作我们都开启“连发”模式，以模拟真实键盘行为
        stop_event = threading.Event()
        active_repeats[key_code] = stop_event
        threading.Thread(target=repeat_key, args=(target_key, stop_event), daemon=True).start()
    else:
        # 抬起按键：停止连发线程
        if key_code in active_repeats:
            stop_event = active_repeats[key_code]
            stop_event.set()
            del active_repeats[key_code]
        keyboard.release(target_key)

@socketio.on('key_combo')
def handle_combo(data):
    # 处理组合快捷键（原子操作）
    keys = data['keys']
    if not keys: return
    
    pressed_keys = []
    try:
        # 按顺序按下所有键
        for k in keys:
            target = SPECIAL_KEYS.get(k.lower().strip(), k.lower().strip())
            keyboard.press(target)
            pressed_keys.append(target)
            time.sleep(0.02) # 微小延迟，确保 OS 识别组合状态
        
        time.sleep(0.05) # 组合键维持一小段时间
    finally:
        # 逆序释放所有键
        for target in reversed(pressed_keys):
            keyboard.release(target)
            time.sleep(0.01)


# --- 自动获取局域网 IP 逻辑 ---
def get_all_ip_addresses():
    ip_list = []
    for interface, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                ip_list.append((interface, addr.address))
    return ip_list

# --- 证书生成函数 ---
# import time # 需要导入 time 模块来获取时间

# def generate_self_signed_cert(cert_file="cert.pem", key_file="key.pem"):
#     if not os.path.exists(cert_file) or not os.path.exists(key_file):
#         print("正在生成自签名 SSL 证书...")
#         k = crypto.PKey()
#         k.generate_key(crypto.TYPE_RSA, 4096)
        
#         cert = crypto.X509()
#         cert.get_subject().CN = "127.0.0.1"
#         cert.set_serial_number(1000)
        
#         # 修正部分：使用 set_notBefore 和 set_notAfter
#         # 格式必须是 YYYYMMDDhhmmssZ 的字节流
#         now = time.strftime("%Y%m%d%H%M%SZ", time.gmtime()).encode('ascii')
#         expire = time.strftime("%Y%m%d%H%M%SZ", time.gmtime(time.time() + 10*365*24*60*60)).encode('ascii')
        
#         cert.set_notBefore(now)
#         cert.set_notAfter(expire)
        
#         cert.set_issuer(cert.get_subject())
#         cert.set_pubkey(k)
#         cert.sign(k, 'sha256')
        
#         with open(cert_file, "wb") as f:
#             f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
#         with open(key_file, "wb") as f:
#             f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k))
#         print("证书生成完毕！")

        
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
        print(f"  ➤  https://{ip}:{port}{tag}")
    
    print("═"*60 + "\n")

    # generate_self_signed_cert()
    # 使用 allow_unsafe_werkzeug 确保在开发环境下稳定运行
    
    socketio.run(
            app, 
            host='0.0.0.0', 
            port=5888, 
            ssl_context=('cert.pem', 'key.pem')
        )
