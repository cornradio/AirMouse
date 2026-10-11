import os
import json
import platform
from pynput.keyboard import Key
from app_paths import app_path

# 宏按键配置存储逻辑（可执行文件旁可写目录）
CONFIG_FILE = app_path("macro_configs.json")

def load_macros():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def save_macros(data):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print("宏按键配置已保存到服务端")

GP_CONFIG_FILE = app_path("gamepad_configs.json")

def load_gp_macros():
    default_cfg = {
        "current": "Default",
        "profiles": { "Default": {} }
    }
    if os.path.exists(GP_CONFIG_FILE):
        try:
            with open(GP_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return default_cfg

def save_gp_macros(data):
    with open(GP_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 特殊按键映射表
def get_special_keys():
    os_type = platform.system()
    # keys = {
    #     'ctrl': Key.ctrl, 'ctrl_r': Key.ctrl_r,
    #     'shift': Key.shift, 'shift_r': Key.shift_r,
    #     'alt': Key.alt, 'alt_r': Key.alt_r,
    #     'win': Key.cmd, 'command': Key.cmd, 'meta': Key.cmd,
    #     'enter': Key.enter, 'esc': Key.esc, 'tab': Key.tab, 'backspace': Key.backspace,
    #     'space': Key.space, 'delete': Key.delete,
    #     'up': Key.up, 'down': Key.down, 'left': Key.left, 'right': Key.right,
    #     'f1': Key.f1, 'f2': Key.f2, 'f3': Key.f3, 'f4': Key.f4, 'f5': Key.f5, 'f6': Key.f6,
    #     'f7': Key.f7, 'f8': Key.f8, 'f9': Key.f9, 'f10': Key.f10, 'f11': Key.f11, 'f12': Key.f12,
    #     # 符号别名
    #     'comma': ',', 'dot': '.', 'slash': '/', 'semicolon': ';', 'quote': "'", 'bracket_l': '[', 'bracket_r': ']'
    # }

    keys = {
        # 修饰键 (Modifiers)
        'ctrl': Key.ctrl, 'ctrl_l': Key.ctrl_l, 'ctrl_r': Key.ctrl_r,
        'shift': Key.shift, 'shift_l': Key.shift_l, 'shift_r': Key.shift_r,
        'alt': Key.alt, 'alt_l': Key.alt_l, 'alt_r': Key.alt_r,
        'win': Key.cmd, 'command': Key.cmd, 'meta': Key.cmd, 'cmd': Key.cmd,

        # 导航键 (Navigation) - 你的错误就在这里补全
        'up': Key.up, 'down': Key.down, 'left': Key.left, 'right': Key.right,
        'page_up': Key.page_up, 'page_down': Key.page_down, 
        'home': Key.home, 'end': Key.end,
        'insert': Key.insert, 'delete': Key.delete,

        # 常用功能键 (Standard Keys)
        'enter': Key.enter, 'esc': Key.esc, 'tab': Key.tab, 
        'backspace': Key.backspace, 'space': Key.space,
        'caps_lock': Key.caps_lock, 'num_lock': Key.num_lock,
        'scroll_lock': Key.scroll_lock, 'print_screen': Key.print_screen,
        'pause': Key.pause,

        # F1-F20 (Function Keys)
        **{f'f{i}': getattr(Key, f'f{i}') for i in range(1, 21)},

        # 符号别名 (Symbols & Punctuation)
        'comma': ',', 'dot': '.', 'slash': '/', 'semicolon': ';', 
        'quote': "'", 'bracket_l': '[', 'bracket_r': ']',
        'backslash': '\\', 'backtick': '`', 'minus': '-', 'equal': '=',
        
        # 额外补充可能用到的媒体键 (Media Keys)
        'media_play_pause': Key.media_play_pause,
        'media_volume_mute': Key.media_volume_mute,
        'media_volume_up': Key.media_volume_up,
        'media_volume_down': Key.media_volume_down,
        'media_next': Key.media_next,
        'media_previous': Key.media_previous
    }
    # Windows 特有
    if os_type == 'Windows':
        keys['prtsc'] = Key.print_screen
        
    return keys
