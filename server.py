import platform
import os

# macOS 隐藏 Dock 图标逻辑
if platform.system() == 'Darwin':
    try:
        from AppKit import NSBundle, NSApplication, NSApplicationActivationPolicyProhibited
        bundle = NSBundle.mainBundle()
        if bundle:
            info = bundle.localizedInfoDictionary() or bundle.infoDictionary()
            if info:
                info['LSUIElement'] = '1'
        # 立即锁定激活策略，防止 Dock 栏图标跳跃或显示
        NSApplication.sharedApplication().setActivationPolicy_(NSApplicationActivationPolicyProhibited)
    except Exception:
        # 如果没有安装相应的库或环境不支持，静默失败
        pass

from web_app import app, socketio, get_all_ip_addresses
import mouse_service
import keyboard_service
import config_manager
import gamepad_service

# 启动手柄后台服务 (如果已安装 inputs)
gamepad_service.start_threads()

# --- SocketIO 事件绑定 ---

@socketio.on('connect')
def handle_connect():
    os_type = platform.system()
    socketio.emit('os_info', {'os': os_type})

@socketio.on('load_macros')
def handle_load():
    data = config_manager.load_macros()
    socketio.emit('macros_loaded', data)

@socketio.on('save_macros')
def handle_save(data):
    config_manager.save_macros(data)

@socketio.on('load_gp_macros')
def handle_gp_load():
    data = config_manager.load_gp_macros()
    socketio.emit('gp_macros_loaded', data)

@socketio.on('save_gp_macros')
def handle_gp_save(data):
    config_manager.save_gp_macros(data)
    gamepad_service.update_config(data)

# 鼠标事件
@socketio.on('move')
def on_move(data): mouse_service.handle_move(data)

@socketio.on('click')
def on_click(data): mouse_service.handle_click(data)

@socketio.on('drag_start')
def on_drag_start(): mouse_service.handle_drag_start()

@socketio.on('drag_end')
def on_drag_end(): mouse_service.handle_drag_end()

@socketio.on('mid_down')
def on_mid_down(): mouse_service.handle_mid_down()

@socketio.on('mid_up')
def on_mid_up(): mouse_service.handle_mid_up()

@socketio.on('scroll')
def on_scroll(data): mouse_service.handle_scroll(data)

# 键盘事件
@socketio.on('type_text')
def on_type(data): keyboard_service.handle_type_text(data)

@socketio.on('key_action')
def on_key(data): keyboard_service.handle_key_action(data)

@socketio.on('key_combo')
def on_combo(data): keyboard_service.handle_combo(data)

if __name__ == '__main__':
    port = 5888
    ips = get_all_ip_addresses()
    
    print("\n" + "═"*60)
    print("🚀 Remote Pro Server 已启动！")
    print(f"🏠 当前系统: {platform.system()}")
    print("📱 请在浏览器访问以下地址:")
    
    for interface, ip in ips:
        tag = ""
        if any(keyword in interface.lower() for keyword in ["wlan", "wi-fi", "eth", "en0", "en1"]):
            tag = " [推荐]"
        print(f"  ➤  https://{ip}:{port}{tag}")
    
    print("═"*60 + "\n")

    socketio.run(
        app, 
        host='0.0.0.0', 
        port=5888, 
        ssl_context=('cert.pem', 'key.pem'),
        allow_unsafe_werkzeug=True # 确保稳定性
    )