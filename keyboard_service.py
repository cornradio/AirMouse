import time
import threading
import platform
from pynput.keyboard import Controller as KeyController, Key, KeyCode
from config_manager import get_special_keys

keyboard = KeyController()
active_repeats = {} # {key_code: stop_event}

def repeat_key(key_obj, stop_event):
    """模拟系统自动重复按键的线程"""
    keyboard.press(key_obj)
    if stop_event.wait(0.4): return
    
    while not stop_event.is_set():
        keyboard.press(key_obj)
        if stop_event.wait(0.05): break

def handle_key_action(data):
    action = data['action'] # 'down' 或 'up'
    key_code = data['key'].lower().strip()
    special_keys = get_special_keys()
    
    target_key = special_keys.get(key_code, key_code)

    if action == 'down':
        if key_code in active_repeats:
            return
        stop_event = threading.Event()
        active_repeats[key_code] = stop_event
        threading.Thread(target=repeat_key, args=(target_key, stop_event), daemon=True).start()
    else:
        if key_code in active_repeats:
            stop_event = active_repeats[key_code]
            stop_event.set()
            del active_repeats[key_code]
        keyboard.release(target_key)

def handle_type_text(data):
    keyboard.type(data['text'])

def handle_combo(data):
    keys = data['keys']
    if not keys: return
    
    special_keys = get_special_keys()
    is_mac = platform.system() == 'Darwin'
    
    pressed_keys = []
    try:
        # 按顺序按下所有键
        for k in keys:
            k_clean = k.lower().strip()
            target = special_keys.get(k_clean, k_clean)
            
            # macOS 修复：对于符号键，直接使用硬件虚拟键码同步位移标志
            # 这样 shift + 47 (dot) 就能被系统和浏览器（如 YouTube）正确识别为 >
            if is_mac and isinstance(target, str) and len(target) == 1:
                # 常见符号的 Mac 虚拟键码 (ANSI 布局)
                vk_map = {
                    '.': 47, ',': 43, '/': 44, ';': 41, "'": 39, 
                    '[': 33, ']': 30, '`': 50, '-': 27, '=': 24, '\\': 42
                }
                if target in vk_map:
                    target = KeyCode.from_vk(vk_map[target])
                else:
                    target = KeyCode.from_char(target)
            
            keyboard.press(target)
            pressed_keys.append(target)
            
            # macOS 下在按下 Shift 等修饰键后增加延迟，确保后续按键能识别到修饰状态
            if is_mac and target in (Key.shift, Key.shift_r, Key.ctrl, Key.ctrl_r, Key.alt, Key.alt_r, Key.cmd):
                time.sleep(0.1)
            else:
                # 维持组合键状态的时间
                delay = 0.05 if is_mac else 0.02
                time.sleep(delay)
        
        # 维持组合键状态的时间
        hold_time = 0.1 if is_mac else 0.05
        time.sleep(hold_time)
        
    finally:
        # 逆序释放所有键
        for target in reversed(pressed_keys):
            keyboard.release(target)
            if is_mac:
                time.sleep(0.01)
