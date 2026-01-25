import os
import json
import platform
from pynput.keyboard import Key

# 宏按键配置存储逻辑
CONFIG_FILE = "macro_configs.json"

def load_macros():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def save_macros(data):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print("宏按键配置已保存到服务端")

# 特殊按键映射表
def get_special_keys():
    os_type = platform.system()
    keys = {
        'ctrl': Key.ctrl, 'ctrl_r': Key.ctrl_r,
        'shift': Key.shift, 'shift_r': Key.shift_r,
        'alt': Key.alt, 'alt_r': Key.alt_r,
        'win': Key.cmd, 'command': Key.cmd, 'meta': Key.cmd,
        'enter': Key.enter, 'esc': Key.esc, 'tab': Key.tab, 'backspace': Key.backspace,
        'space': Key.space, 'delete': Key.delete,
        'up': Key.up, 'down': Key.down, 'left': Key.left, 'right': Key.right,
        'f1': Key.f1, 'f2': Key.f2, 'f3': Key.f3, 'f4': Key.f4, 'f5': Key.f5, 'f6': Key.f6,
        'f7': Key.f7, 'f8': Key.f8, 'f9': Key.f9, 'f10': Key.f10, 'f11': Key.f11, 'f12': Key.f12,
        # 符号别名
        'comma': ',', 'dot': '.', 'slash': '/', 'semicolon': ';', 'quote': "'", 'bracket_l': '[', 'bracket_r': ']'
    }
    
    # Windows 特有
    if os_type == 'Windows':
        keys['prtsc'] = Key.print_screen
        
    return keys
