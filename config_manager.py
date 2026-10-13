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

    # macOS 的 pynput Key 枚举缺少 insert / num_lock / scroll_lock / print_screen
    # 等键（这些键在 macOS 键盘上不存在），统一用 getattr 安全获取。
    def _k(name, default=None):
        return getattr(Key, name, default)

    keys = {
        # 修饰键 (Modifiers)
        'ctrl': _k('ctrl'), 'ctrl_l': _k('ctrl_l'), 'ctrl_r': _k('ctrl_r'),
        'shift': _k('shift'), 'shift_l': _k('shift_l'), 'shift_r': _k('shift_r'),
        'alt': _k('alt'), 'alt_l': _k('alt_l'), 'alt_r': _k('alt_r'),
        'win': _k('cmd'), 'command': _k('cmd'), 'meta': _k('cmd'), 'cmd': _k('cmd'),

        # 导航键 (Navigation)
        'up': _k('up'), 'down': _k('down'), 'left': _k('left'), 'right': _k('right'),
        'page_up': _k('page_up'), 'page_down': _k('page_down'),
        'home': _k('home'), 'end': _k('end'),
        'insert': _k('insert'), 'delete': _k('delete'),

        # 常用功能键 (Standard Keys)
        'enter': _k('enter'), 'esc': _k('esc'), 'tab': _k('tab'),
        'backspace': _k('backspace'), 'space': _k('space'),
        'caps_lock': _k('caps_lock'), 'num_lock': _k('num_lock'),
        'scroll_lock': _k('scroll_lock'), 'print_screen': _k('print_screen'),
        'pause': _k('pause'),

        # F1-F20 (Function Keys)
        **{f'f{i}': getattr(Key, f'f{i}') for i in range(1, 21)
           if hasattr(Key, f'f{i}')},

        # 符号别名 (Symbols & Punctuation)
        'comma': ',', 'dot': '.', 'slash': '/', 'semicolon': ';',
        'quote': "'", 'bracket_l': '[', 'bracket_r': ']',
        'backslash': '\\', 'backtick': '`', 'minus': '-', 'equal': '=',

        # 额外补充可能用到的媒体键 (Media Keys)
        'media_play_pause': _k('media_play_pause'),
        'media_volume_mute': _k('media_volume_mute'),
        'media_volume_up': _k('media_volume_up'),
        'media_volume_down': _k('media_volume_down'),
        'media_next': _k('media_next'),
        'media_previous': _k('media_previous'),
    }
    # 移除值为 None 的键（当前平台不支持的按键）
    keys = {k: v for k, v in keys.items() if v is not None}

    # Windows 特有
    if os_type == 'Windows':
        keys['prtsc'] = _k('print_screen')

    return keys
