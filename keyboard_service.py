import time
import threading
import platform
import ctypes
from debug_logging import debug_log

_IS_MAC = platform.system() == 'Darwin'

# ---------------------------------------------------------------------------
# macOS: use ctypes to call Quartz C API directly (thread-safe).
# Keyboard events use CGEventPost which requires Accessibility permission.
# ---------------------------------------------------------------------------

if _IS_MAC:
    _quartz = ctypes.CDLL('/System/Library/Frameworks/Quartz.framework/Quartz')
    _core_foundation = ctypes.CDLL(
        '/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation'
    )
    _CFTypeRef = ctypes.c_void_p

    _quartz.CGEventCreateKeyboardEvent.restype = _CFTypeRef
    _quartz.CGEventCreateKeyboardEvent.argtypes = [_CFTypeRef, ctypes.c_uint16, ctypes.c_bool]
    _quartz.CGEventKeyboardSetUnicodeString.restype = None
    _quartz.CGEventKeyboardSetUnicodeString.argtypes = [
        _CFTypeRef, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint16),
    ]
    _quartz.CGEventSetIntegerValueField.restype = None
    _quartz.CGEventSetIntegerValueField.argtypes = [_CFTypeRef, ctypes.c_uint32, ctypes.c_int64]
    _quartz.CGEventPost.restype = None
    _quartz.CGEventPost.argtypes = [ctypes.c_uint32, _CFTypeRef]
    _core_foundation.CFRelease.restype = None
    _core_foundation.CFRelease.argtypes = [_CFTypeRef]

    _kCGHIDEventTap = 0
    _kCGKeyboardEventAutorepeat = 8

    def _release_event(event):
        """Release each Create-rule Quartz event after it has been posted."""
        if event:
            _core_foundation.CFRelease(event)

    # macOS virtual key codes (ANSI layout)
    _KEYCODES = {
        # letters
        'a': 0,  'b': 11, 'c': 8,  'd': 2,  'e': 14, 'f': 3,  'g': 5,
        'h': 4,  'i': 18, 'j': 38, 'k': 40, 'l': 37, 'm': 46, 'n': 45,
        'o': 31, 'p': 35, 'q': 12, 'r': 15, 's': 1,  't': 17, 'u': 32,
        'v': 9,  'w': 13, 'x': 7,  'y': 16, 'z': 6,
        # digits
        '0': 29, '1': 18, '2': 19, '3': 20, '4': 21, '5': 23,
        '6': 22, '7': 26, '8': 28, '9': 25,
        # special
        'enter': 36, 'tab': 48, 'space': 49, 'delete': 51,
        'backspace': 51, 'escape': 53, 'esc': 53, 'caps_lock': 57,
        # macOS function keys use non-contiguous virtual key codes.
        'f1': 122, 'f2': 120, 'f3': 99, 'f4': 118, 'f5': 96, 'f6': 97,
        'f7': 98, 'f8': 100, 'f9': 101, 'f10': 109, 'f11': 103, 'f12': 111,
        'f13': 105, 'f14': 107, 'f15': 113, 'f16': 106, 'f17': 64,
        'f18': 79, 'f19': 80, 'f20': 90,
        # arrows & nav
        'up': 126, 'down': 125, 'left': 123, 'right': 124,
        'page_up': 116, 'page_down': 121, 'home': 115, 'end': 119,
        'insert': 114,
        # modifiers
        'shift': 56, 'shift_l': 56, 'shift_r': 60,
        'ctrl': 59, 'ctrl_l': 59, 'ctrl_r': 62,
        'alt': 58, 'alt_l': 58, 'alt_r': 61,
        'cmd': 55, 'cmd_l': 55, 'cmd_r': 54,
        'command': 55, 'meta': 55,
        # macOS Fn/Globe 键的虚拟键码，用于组合触发 F11 等功能键快捷键。
        'fn': 63,
        # symbols
        ',': 43, '.': 47, '/': 44, ';': 41, "'": 39,
        '[': 33, ']': 30, '\\': 42, '`': 50,
        '-': 27, '=': 24,
        # Shifted symbols share their base physical key; Shift remains an
        # explicit modifier in key_combo so the receiving app sees the symbol.
        '!': 18, '@': 19, '#': 20, '$': 21, '%': 23, '^': 22, '&': 26,
        '*': 28, '(': 29, ')': 25, '_': 27, '+': 24, '{': 33, '}': 30,
        '|': 42, ':': 41, '"': 39, '<': 43, '>': 47, '?': 44, '~': 50,
    }

    from pynput.keyboard import Key, KeyCode

    _PYNPUT_KEY_MAP = {
        Key.ctrl: 59, Key.ctrl_l: 59, Key.ctrl_r: 62,
        Key.shift: 56, Key.shift_l: 56, Key.shift_r: 60,
        Key.alt: 58, Key.alt_l: 58, Key.alt_r: 61,
        Key.cmd: 55, Key.cmd_l: 55, Key.cmd_r: 54,
        Key.enter: 36, Key.esc: 53, Key.tab: 48,
        Key.backspace: 51, Key.space: 49, Key.delete: 117,
        Key.up: 126, Key.down: 125, Key.left: 123, Key.right: 124,
        Key.page_up: 116, Key.page_down: 121,
        Key.home: 115, Key.end: 119, Key.caps_lock: 57,
    }
    # Some pynput backends do not expose these keys as enum members. Only add
    # them when present so config_manager's cross-platform map remains safe.
    for _name, _vk in {'insert': 114}.items():
        _key = getattr(Key, _name, None)
        if _key is not None:
            _PYNPUT_KEY_MAP[_key] = _vk
    _F_KEYS = {i: _KEYCODES[f'f{i}'] for i in range(1, 21)}
    for _i, _vk in _F_KEYS.items():
        _key = getattr(Key, f'f{_i}', None)
        if _key is not None:
            _PYNPUT_KEY_MAP[_key] = _vk

    def _resolve_keycode(target) -> int:
        if isinstance(target, Key):
            return _PYNPUT_KEY_MAP.get(target)
        if isinstance(target, KeyCode):
            if target.char and len(target.char) == 1:
                return _KEYCODES.get(target.char.lower())
            return target.vk or None
        if isinstance(target, str):
            if len(target) == 1:
                return _KEYCODES.get(target.lower())
            return _KEYCODES.get(target)
        return None

    def _post_key_event(target, is_down, autorepeat=False):
        vk = _resolve_keycode(target)
        # Virtual key code zero is the physical A key; never turn an unknown
        # name into an accidental A press.
        if vk is None:
            debug_log('quartz', 'key_ignored', key=repr(target), reason='unknown_key')
            return
        event = _quartz.CGEventCreateKeyboardEvent(None, vk, is_down)
        if not event:
            debug_log('quartz', 'key_event_create_failed', keycode=vk,
                      is_down=is_down, autorepeat=autorepeat)
            return
        try:
            if autorepeat and is_down:
                _quartz.CGEventSetIntegerValueField(
                    event, _kCGKeyboardEventAutorepeat, 1
                )
            _quartz.CGEventPost(_kCGHIDEventTap, event)
            debug_log('quartz', 'key_event_posted', keycode=vk,
                      is_down=is_down, autorepeat=autorepeat)
        finally:
            _release_event(event)

    def _mac_key_down(target, autorepeat=False):
        _post_key_event(target, True, autorepeat=autorepeat)

    def _mac_key_up(target):
        _post_key_event(target, False)

    def _post_unicode_character(character):
        """Post one Unicode character without relying on the active layout."""
        # CGEventKeyboardSetUnicodeString takes UTF-16 code units (UniChar),
        # so supplementary-plane characters may produce a surrogate pair.
        encoded = character.encode('utf-16-le', errors='surrogatepass')
        units = [int.from_bytes(encoded[i:i + 2], 'little')
                 for i in range(0, len(encoded), 2)]
        unicode_buffer = (ctypes.c_uint16 * len(units))(*units)
        for is_down in (True, False):
            event = _quartz.CGEventCreateKeyboardEvent(None, 0, is_down)
            if not event:
                continue
            try:
                _quartz.CGEventKeyboardSetUnicodeString(
                    event, len(units), unicode_buffer
                )
                _quartz.CGEventPost(_kCGHIDEventTap, event)
                debug_log('quartz', 'unicode_event_posted', units=len(units),
                          is_down=is_down)
            finally:
                _release_event(event)

    def _mac_type_text(text):
        for ch in text:
            _post_unicode_character(ch)
            time.sleep(0.02)

    _MODIFIER_KEYS = frozenset({59, 62, 56, 60, 58, 61, 55, 54, 63})

    def _is_modifier(target) -> bool:
        vk = _resolve_keycode(target)
        return vk in _MODIFIER_KEYS

# ---------------------------------------------------------------------------
# Windows / Linux: pynput
# ---------------------------------------------------------------------------

if not _IS_MAC:
    from pynput.keyboard import Controller as _KController, Key, KeyCode
    _keyboard = _KController()

    def _mac_key_down(target, autorepeat=False):
        _keyboard.press(target)

    def _mac_key_up(target):
        _keyboard.release(target)

    def _mac_type_text(text):
        _keyboard.type(text)

    def _is_modifier(target):
        from pynput.keyboard import Key as _K
        return target in (_K.ctrl, _K.ctrl_l, _K.ctrl_r,
                          _K.shift, _K.shift_l, _K.shift_r,
                          _K.alt, _K.alt_l, _K.alt_r,
                          _K.cmd, _K.cmd_l, _K.cmd_r)


from config_manager import get_special_keys

active_repeats = {}
_key_lock = threading.RLock()
_MOD_DELAY = 0.1 if _IS_MAC else 0.05
_HOLD_DELAY = 0.1 if _IS_MAC else 0.05


def _repeat_key(target, stop_event, key_code):
    # The initial key-down is sent synchronously by handle_key_action. This
    # worker only emits repeats, and checks the pressed-key registry while
    # holding the same lock used by key-up to prevent a late down after release.
    if stop_event.wait(0.4):
        return
    while not stop_event.is_set():
        with _key_lock:
            if active_repeats.get(key_code) is not stop_event or stop_event.is_set():
                return
            _mac_key_down(target, autorepeat=True)
        if stop_event.wait(0.05):
            return


def handle_key_action(data):
    action = data.get('action', 'down')
    key_code = data.get('key', '').lower().strip()
    special_keys = get_special_keys()
    target = special_keys.get(key_code, key_code)

    if action == 'down':
        with _key_lock:
            if key_code in active_repeats:
                return
            # Send the first down before starting the timer. This closes the
            # race where a quick up arrived before the worker's first down.
            _mac_key_down(target)
            if data.get('no_repeat'):
                active_repeats[key_code] = None
                return
            stop_event = threading.Event()
            active_repeats[key_code] = stop_event
            threading.Thread(
                target=_repeat_key, args=(target, stop_event, key_code), daemon=True
            ).start()
    else:
        with _key_lock:
            stop_event = active_repeats.pop(key_code, None)
            if stop_event is not None:
                stop_event.set()
            _mac_key_up(target)


def handle_type_text(data):
    _mac_type_text(data.get('text', ''))


def handle_combo(data):
    keys = data.get('keys')
    if not keys:
        return

    special_keys = get_special_keys()
    pressed = []
    try:
        for k in keys:
            k_clean = k.lower().strip()
            target = special_keys.get(k_clean, k_clean)
            _mac_key_down(target)
            pressed.append(target)
            if _is_modifier(target):
                time.sleep(_MOD_DELAY)
            else:
                time.sleep(0.05 if _IS_MAC else 0.02)

        time.sleep(_HOLD_DELAY)

    finally:
        for target in reversed(pressed):
            _mac_key_up(target)
            time.sleep(0.01)
