import ctypes
import threading
import time
import mouse_service
import keyboard_service
import config_manager
import platform
from ctypes import wintypes
from pynput.mouse import Controller as MouseController, Button as MouseButton

pmouse = MouseController()
OS_TYPE = platform.system()

# --- 驱动探测与加载 ---
inputs = None
xinput = None

if OS_TYPE == 'Windows':
    try:
        xinput = ctypes.windll.xinput1_4
    except Exception:
        try:
            xinput = ctypes.windll.xinput1_3
        except Exception:
            pass
else:
    # 非 Windows 系统，尝试加载 inputs 库作为冗余备份
    try:
        import inputs
    except ImportError:
        print("WARNING: 'inputs' library is not installed for non-Windows platform.")

# --- 状态变量 ---
gamepad_connected = False
gamepad_name = "未连接"
selected_index = 0 # 对应 Player 槽位 或 inputs 列表索引

# 坐标状态字典 (ABS_X, ABS_Y, ABS_RX, ABS_RY, ABS_Z, ABS_RZ, HAT_X, HAT_Y)
state = { k: 0 for k in ['ABS_X', 'ABS_Y', 'ABS_RX', 'ABS_RY', 'ABS_Z', 'ABS_RZ', 'HAT_X', 'HAT_Y'] }
active_keys = set()
_cached_cfg = None

# --- XInput 底层定义 (仅 Windows) ---
if OS_TYPE == 'Windows':
    class XINPUT_GAMEPAD(ctypes.Structure):
        _pack_ = 1
        _fields_ = [
            ("wButtons", wintypes.WORD),
            ("bLeftTrigger", ctypes.c_ubyte),
            ("bRightTrigger", ctypes.c_ubyte),
            ("sThumbLX", ctypes.c_short),
            ("sThumbLY", ctypes.c_short),
            ("sThumbRX", ctypes.c_short),
            ("sThumbRY", ctypes.c_short),
        ]
    class XINPUT_STATE(ctypes.Structure):
        _pack_ = 1
        _fields_ = [ ("dwPacketNumber", wintypes.DWORD), ("Gamepad", XINPUT_GAMEPAD) ]
    
    BTN_MAP_XIN = {
        0x1000: 'BTN_SOUTH', 0x2000: 'BTN_EAST', 0x4000: 'BTN_WEST', 0x8000: 'BTN_NORTH',
        0x0100: 'BTN_TL', 0x0200: 'BTN_TR', 0x0040: 'BTN_THUMBL', 0x0080: 'BTN_THUMBR',
        0x0020: 'BTN_SELECT', 0x0010: 'BTN_START'
    }

# --- 统一业务逻辑 ---

def update_config(data):
    global _cached_cfg
    _cached_cfg = data

def get_current_cfg():
    global _cached_cfg
    if _cached_cfg is None:
        _cached_cfg = config_manager.load_gp_macros()
    return _cached_cfg

def get_gamepad_list(force_rescan=False):
    """跨平台获取手柄列表"""
    if OS_TYPE == 'Windows' and xinput:
        res = []
        temp = XINPUT_STATE()
        for i in range(4):
            if xinput.XInputGetState(i, ctypes.byref(temp)) == 0:
                res.append({"name": f"Xbox 控制器 {i+1} (Windows)", "index": i})
        return res
    elif inputs:
        # 非 Windows 使用 inputs 库
        try:
            return [{"name": gp.name, "index": i} for i, gp in enumerate(inputs.devices.gamepads)]
        except Exception: return []
    return []

def handle_btn(btn_code, pressed):
    if not gamepad_connected: return
    mapping = {
        'BTN_SOUTH': 'btn_0', 'BTN_EAST': 'btn_1', 'BTN_WEST': 'btn_2', 'BTN_NORTH': 'btn_3',
        'BTN_TL': 'btn_4', 'BTN_TR': 'btn_5', 'BTN_THUMBL': 'btn_10', 'BTN_THUMBR': 'btn_11',
        'BTN_SELECT': 'btn_8', 'BTN_START': 'btn_9'
    }
    cfgId = mapping.get(btn_code)
    if not cfgId: return
    data = get_current_cfg()
    if not data or not data.get('current') or not data.get('enabled', True): return
    action = data['profiles'][data['current']].get(cfgId, 'none')
    execute_action(action, pressed)

def execute_action(action, pressed):
    if action == 'none': return
    if action.startswith('click_'):
        btn_map = {'left': MouseButton.left, 'right': MouseButton.right, 'middle': MouseButton.middle}
        btn_str = action.split('_')[1]
        try:
            if pressed: pmouse.press(btn_map[btn_str])
            else: pmouse.release(btn_map[btn_str])
        except Exception: pass
    elif action.startswith('key_'):
        if '+' in action:
            if pressed:
                keys = [k.replace('key_', '') for k in action.split('+')]
                keyboard_service.handle_combo({'keys': keys})
        else:
            mapped_key = action.replace('key_', '')
            keyboard_service.handle_key_action({'key': mapped_key, 'action': 'down' if pressed else 'up', 'no_repeat': True})

def handle_stick(mode, xVal, yVal, res_m, res_k):
    if mode == "mouse":
        if abs(xVal)>0: res_m['mx'] += xVal
        if abs(yVal)>0: res_m['my'] += yVal
        return
    if mode.startswith("scroll"):
        mult = -1 if mode == "scroll_rev" else 1
        if abs(xVal)>0: res_m['sx'] += xVal * mult
        if abs(yVal)>0: res_m['sy'] += yVal * mult
        return
    layout = {}
    if mode == "wasd": layout = {'up': "w", 'down': "s", 'left': "a", 'right': "d"}
    elif mode == "hjkl": layout = {'up': "k", 'down': "j", 'left': "h", 'right': "l"}
    elif mode == "arrows": layout = {'up': "up", 'down': "down", 'left': "left", 'right': "right"}
    else: return
    threshold = 0.5
    if yVal < -threshold: res_k.add(layout['up'])
    if yVal > threshold: res_k.add(layout['down'])
    if xVal < -threshold: res_k.add(layout['left'])
    if xVal > threshold: res_k.add(layout['right'])

# --- 线程循环实现 ---

def windows_loop():
    """Windows 原生 XInput 驱动逻辑"""
    global gamepad_connected, gamepad_name, active_keys
    x_state = XINPUT_STATE()
    last_buttons = 0; prev_lt, prev_rt = False, False; prev_hat = {'u':False,'d':False,'l':False,'r':False}
    target_fps = 120; frame_time = 1.0 / target_fps
    rem_mx, rem_my = 0.0, 0.0; rem_sx, rem_sy = 0.0, 0.0
    
    while True:
        start_t = time.perf_counter()
        if xinput.XInputGetState(selected_index, ctypes.byref(x_state)) != 0:
            if gamepad_connected: print(f"[Gamepad] Windows XInput 断开")
            gamepad_connected = False; gamepad_name = "未连接"
            for k in list(active_keys): keyboard_service.handle_key_action({'key': k, 'action': 'up', 'no_repeat': True})
            active_keys.clear(); time.sleep(1); continue
        
        gamepad_connected = True; gamepad_name = f"Xbox 手柄 {selected_index+1}"
        gp = x_state.Gamepad
        # 按键
        current_buttons = gp.wButtons; changed = current_buttons ^ last_buttons
        if changed:
            for bit, code in BTN_MAP_XIN.items():
                if changed & bit: handle_btn(code, bool(current_buttons & bit))
            last_buttons = current_buttons
        # 坐标
        state['ABS_X'], state['ABS_Y'] = gp.sThumbLX, gp.sThumbLY
        state['ABS_RX'], state['ABS_RY'] = gp.sThumbRX, gp.sThumbRY
        state['ABS_Z'], state['ABS_RZ'] = gp.bLeftTrigger, gp.bRightTrigger
        # DPad
        u = bool(current_buttons & 0x0001); d = bool(current_buttons & 0x0002); l = bool(current_buttons & 0x0004); r = bool(current_buttons & 0x0008)
        state['HAT_X'] = 1 if r else (-1 if l else 0); state['HAT_Y'] = 1 if d else (-1 if u else 0)
        
        # 持续业务
        data = get_current_cfg()
        if data and data.get('current') and data.get('enabled', True):
            cur_map = data['profiles'][data['current']]
            sens = float(data.get('sens', 5.0)); sc_sens = float(data.get('scroll_sens', 5.0)); dz = float(data.get('deadzone', 0.15)); curve = data.get('curve', 'medium')
            apply_dz = lambda v, max_v: (v/max_v) if abs(v/max_v) > dz else 0
            lx, ly = apply_dz(gp.sThumbLX, 32767.0), apply_dz(gp.sThumbLY, 32767.0)
            rx, ry = apply_dz(gp.sThumbRX, 32767.0), apply_dz(gp.sThumbRY, 32767.0)
            # LT/RT 映射 (消抖)
            t_lt, t_rt = (gp.bLeftTrigger > 45), (gp.bRightTrigger > 45)
            if t_lt != prev_lt: handle_btn('BTN_TL2', t_lt); prev_lt = t_lt # 借用 inputs 名或自定义
            # 这里统一使用 execute_action 方便
            lt_p = True if gp.bLeftTrigger > 45 else (False if gp.bLeftTrigger < 20 else prev_lt)
            rt_p = True if gp.bRightTrigger > 45 else (False if gp.bRightTrigger < 20 else prev_rt)
            if lt_p != prev_lt: execute_action(cur_map.get('btn_6', 'none'), lt_p); prev_lt = lt_p
            if rt_p != prev_rt: execute_action(cur_map.get('btn_7', 'none'), rt_p); prev_rt = rt_p
            # Dpad
            if u != prev_hat['u']: execute_action(cur_map.get('btn_12', 'none'), u); prev_hat['u'] = u
            if d != prev_hat['d']: execute_action(cur_map.get('btn_13', 'none'), d); prev_hat['d'] = d
            if l != prev_hat['l']: execute_action(cur_map.get('btn_14', 'none'), l); prev_hat['l'] = l
            if r != prev_hat['r']: execute_action(cur_map.get('btn_15', 'none'), r); prev_hat['r'] = r

            rm, rk = {'mx':0.0,'my':0.0,'sx':0.0,'sy':0.0}, set()
            handle_stick(cur_map.get('stick_left', 'none'), lx, -ly, rm, rk)
            handle_stick(cur_map.get('stick_right', 'none'), rx, -ry, rm, rk)
            mag = (rm['mx']**2 + rm['my']**2)**0.5
            acc = 1.0 + (mag**2 * 5.0) if curve == 'aggressive' else (1.0 + mag**1.5 * 2.5 if curve == 'medium' else 1.0)
            dfx, dfy = rm['mx']*acc*sens*4.0+rem_mx, rm['my']*acc*sens*4.0+rem_my
            sfx, sfy = rm['sx']*sc_sens*0.05+rem_sx, rm['sy']*sc_sens*0.05+rem_sy
            dx, dy = int(dfx), int(dfy); sx, sy = int(sfx), int(sfy)
            rem_mx, rem_my, rem_sx, rem_sy = dfx-dx, dfy-dy, sfx-sx, sfy-sy
            if dx != 0 or dy != 0: mouse_service.handle_move({'dx': dx, 'dy': dy})
            if sx != 0 or sy != 0: mouse_service.handle_scroll({'dx': sx, 'dy': sy})
            for k in list(active_keys):
                if k not in rk: keyboard_service.handle_key_action({'key':k, 'action':'up', 'no_repeat':True}); active_keys.remove(k)
            for k in rk:
                if k not in active_keys: keyboard_service.handle_key_action({'key':k, 'action':'down', 'no_repeat':True}); active_keys.add(k)
        
        slp = frame_time - (time.perf_counter() - start_t)
        if slp > 0: time.sleep(slp)

def unix_loop():
    """非 Windows fallback (inputs 库模式)"""
    global gamepad_connected, gamepad_name
    while True:
        if not inputs: time.sleep(5); continue
        try:
            gps = inputs.devices.gamepads
            if not gps or selected_index >= len(gps):
                gamepad_connected = False; gamepad_name = "未连接"; time.sleep(2); continue
            target = gps[selected_index]; gamepad_name = target.name
            # 这里简化处理，不包含高级消抖，仅作为非 Windows 的备份
            events = target.read()
            gamepad_connected = True
            for event in events:
                if event.ev_type == 'Absolute':
                    if event.code == 'ABS_HAT0X': state['HAT_X'] = event.state
                    elif event.code == 'ABS_HAT0Y': state['HAT_Y'] = event.state
                    else: state[event.code] = event.state
                elif event.ev_type == 'Key':
                    handle_btn(event.code, event.state == 1)
        except Exception:
            gamepad_connected = False; time.sleep(2)

def unix_continuous_loop():
    """非 Windows 的摇杆持续处理辅助线程"""
    while True:
        time.sleep(0.01) # 100Hz
        if not gamepad_connected or OS_TYPE == 'Windows': continue
        # 这里的持续逻辑可以复用 handle_stick 等，简化实现略
        pass

def start_threads():
    if OS_TYPE == 'Windows' and xinput:
        threading.Thread(target=windows_loop, daemon=True).start()
    else:
        threading.Thread(target=unix_loop, daemon=True).start()
        threading.Thread(target=unix_continuous_loop, daemon=True).start()
