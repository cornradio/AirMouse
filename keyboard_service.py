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
            
            # macOS 修复：对于单个字符，使用 KeyCode.from_char 避免 pynput 自动释放 Shift
            # 这样 shift + . 就能正确产生 >
            if is_mac and isinstance(target, str) and len(target) == 1:
                target = KeyCode.from_char(target)
            
            keyboard.press(target)
            pressed_keys.append(target)
            
            # macOS 需要稍长的延迟来确保系统识别到组合状态
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
