from flask import Flask, render_template
from flask_socketio import SocketIO
from pynput.mouse import Controller, Button
from pynput.keyboard import Controller as KeyController, Key

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# 这里的 keyboard 是键盘控制器实例
mouse = Controller()
keyboard = KeyController()

# 特殊按键映射表
SPECIAL_KEYS = {
    'ctrl': Key.ctrl, 'shift': Key.shift, 'alt': Key.alt, 'win': Key.cmd,
    'enter': Key.enter, 'esc': Key.esc, 'tab': Key.tab, 'backspace': Key.backspace,
    'space': Key.space, # 建议直接放在这里
    'f1': Key.f1, 'f2': Key.f2, 'f3': Key.f3, 'f4': Key.f4, 'f5': Key.f5, 'f6': Key.f6,
    'f7': Key.f7, 'f8': Key.f8, 'f9': Key.f9, 'f10': Key.f10, 'f11': Key.f11, 'f12': Key.f12
}

@app.route('/')
def index():
    return render_template('index.html')

# --- 修改点：函数名改为 keyboard_page，避免覆盖 keyboard 实例 ---
@app.route('/k')
def keyboard_page(): 
    return render_template('keyboard.html') # 如果你是单页面，统一指向 index

# --- 鼠标逻辑 ---
@socketio.on('move')
def handle_move(data):
    mouse.move(data['dx'], data['dy'])

@socketio.on('click')
def handle_click(data):
    btn = Button.right if data.get('button') == 'right' else Button.left
    mouse.click(btn)

@socketio.on('drag_start')
def handle_drag_start():
    mouse.release(Button.left)
    mouse.press(Button.left)

@socketio.on('drag_end')
def handle_drag_end():
    mouse.release(Button.left)

@socketio.on('scroll')
def handle_scroll(data):
    mouse.scroll(0, data['dy'])

# --- 键盘逻辑 ---
@socketio.on('type_text')
def handle_type(data):
    # 现在这里的 keyboard 指向的是 KeyController() 实例了
    keyboard.type(data['text'])

@socketio.on('key_action')
def handle_key_action(data):
    action = data['action'] # 'down' 或 'up'
    key_code = data['key'].lower()
    
    if key_code in SPECIAL_KEYS:
        target_key = SPECIAL_KEYS[key_code]
        if action == 'down':
            keyboard.press(target_key)
        else:
            keyboard.release(target_key)
    elif len(key_code) == 1: # 普通字母
        if action == 'down':
            keyboard.press(key_code)
        else:
            keyboard.release(key_code)

# 别忘了之前提到的组合键宏逻辑，建议一并加入
@socketio.on('key_combo')
def handle_combo(data):
    keys = data['keys']
    for k in keys:
        target = SPECIAL_KEYS.get(k.lower(), k.lower())
        keyboard.press(target)
    for k in reversed(keys):
        target = SPECIAL_KEYS.get(k.lower(), k.lower())
        keyboard.release(target)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5888, allow_unsafe_werkzeug=True)