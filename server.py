import os
from OpenSSL import crypto
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
    'ctrl': Key.ctrl, 'ctrl_r': Key.ctrl_r,
    'shift': Key.shift, 'shift_r': Key.shift_r,
    'alt': Key.alt, 'alt_r': Key.alt_r,
    'win': Key.cmd,
    'enter': Key.enter, 'esc': Key.esc, 'tab': Key.tab, 'backspace': Key.backspace,
    'space': Key.space, 'delete': Key.delete, 'prtsc': Key.print_screen,
    'up': Key.up, 'down': Key.down, 'left': Key.left, 'right': Key.right,
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