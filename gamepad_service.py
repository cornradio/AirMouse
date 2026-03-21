import threading
import time
import mouse_service
import keyboard_service
import config_manager

try:
    import inputs
except ImportError:
    inputs = None
    print("WARNING: 'inputs' library is not installed. PC gamepad support is disabled. Run 'pip install inputs' to enable it.")

# 当前手柄的状态
state = {
    'ABS_X': 0, 'ABS_Y': 0,
    'ABS_RX': 0, 'ABS_RY': 0,
    'ABS_Z': 0, 'ABS_RZ': 0, # LT, RT
    'HAT_X': 0, 'HAT_Y': 0   # Dpad
}

active_keys = set()
is_dragging = False
gamepad_connected = False

_cached_cfg = None

def update_config(data):
    global _cached_cfg
    _cached_cfg = data

def get_current_cfg():
    global _cached_cfg
    if _cached_cfg is None:
        _cached_cfg = config_manager.load_gp_macros()
    return _cached_cfg

def poll_gamepad_state():
    """纯粹的输入读取线程"""
    global gamepad_connected
    while True:
        if inputs is None: return
        try:
            events = inputs.get_gamepad()
            gamepad_connected = True
            for event in events:
                if event.ev_type == 'Absolute':
                    if event.code == 'ABS_HAT0X': state['HAT_X'] = event.state
                    elif event.code == 'ABS_HAT0Y': state['HAT_Y'] = event.state
                    else: state[event.code] = event.state
                elif event.ev_type == 'Key':
                    handle_btn(event.code, event.state == 1)
        except inputs.UnpluggedError:
            gamepad_connected = False
            time.sleep(2)
        except Exception as e:
            gamepad_connected = False
            time.sleep(1)

def apply_dz(val, max_val, deadzone=0.15):
    norm = val / max_val
    if abs(norm) > deadzone: return norm
    return 0

def handle_btn(btn_code, pressed):
    if not gamepad_connected: return
    
    mapping = {
        'BTN_SOUTH': 'btn_0', 'BTN_EAST': 'btn_1', 'BTN_WEST': 'btn_2', 'BTN_NORTH': 'btn_3',
        'BTN_TL': 'btn_4', 'BTN_TR': 'btn_5', 'BTN_THUMBL': 'btn_10', 'BTN_THUMBR': 'btn_11',
        'BTN_SELECT': 'btn_8', 'BTN_START': 'btn_9', 'BTN_MODE': 'btn_16'
    }
    
    cfgId = mapping.get(btn_code)
    if not cfgId: return
    
    data = get_current_cfg()
    if not data or not data.get('current'): return
    current_map = data['profiles'][data['current']]
    action = current_map.get(cfgId, 'none')
    
    execute_action(action, pressed)

def execute_action(action, pressed):
    global is_dragging
    if action == 'none': return
    
    if action.startswith('click_'):
        if pressed:
            btn = action.split('_')[1]
            try:
                mouse_service.handle_click({'button': btn})
            except Exception:
                pass
    elif action == 'drag':
        mouse_service.handle_drag_start() if pressed else mouse_service.handle_drag_end()
    elif action.startswith('key_'):
        mapped_key = action.replace('key_', '')
        keyboard_service.handle_key_action({'key': mapped_key, 'action': 'down' if pressed else 'up'})

def process_continuous():
    """持续处理摇杆坐标，每 16ms 执行一次以保持丝滑移动"""
    global active_keys
    
    while True:
        time.sleep(0.016)
        if not gamepad_connected: continue
        
        data = get_current_cfg()
        if not data or not data.get('current'): continue
        
        current_map = data['profiles'][data['current']]
        sens = float(data.get('sens', 5.0))
        dz = float(data.get('deadzone', 0.15))
        
        # 解析摇杆 (-1.0 to 1.0)
        # Xbox controllers: X/Y range from -32768 to 32767. Y is usually inverted (negative is up).
        # However, to match Web Gamepad API where -1.0 is LEFT/UP and 1.0 is RIGHT/DOWN:
        l_x = apply_dz(state['ABS_X'], 32767, dz)
        l_y = apply_dz(state['ABS_Y'], -32767, dz)  # inputs gives negative for UP, HTML5 gives negative for UP. Wait, negative / 32767 = negative. To make -1.0 = UP, we divide by -32767. So if Y=32767 (Up), 32767 / -32767 = -1.0 (UP). Perfect.
        r_x = apply_dz(state['ABS_RX'], 32767, dz)
        r_y = apply_dz(state['ABS_RY'], -32767, dz)
        lt  = apply_dz(state['ABS_Z'], 255, dz)
        rt  = apply_dz(state['ABS_RZ'], 255, dz)
        
        # 兼容扳机键 (L2/R2) 的阈值控制 (当按钮处理)
        lt_pressed = lt > 0.5
        rt_pressed = rt > 0.5
        # ... 可以通过状态机单独处理扳机键的 pressed，这里为了简便我们用 event 比较好
        # 但是 inputs 把扳机键当轴，只能在这里处理：
        global prev_lt, prev_rt
        if 'prev_lt' not in globals(): prev_lt = False
        if 'prev_rt' not in globals(): prev_rt = False
        
        if lt_pressed != prev_lt:
            execute_action(current_map.get('btn_6', 'none'), lt_pressed)
            prev_lt = lt_pressed
        if rt_pressed != prev_rt:
            execute_action(current_map.get('btn_7', 'none'), rt_pressed)
            prev_rt = rt_pressed
            
        # 兼容十字键 (D-pad) 的持续读取 (因为 inputs 中的帽子视作轴，只有 -1, 0, 1)
        hat_x = state['HAT_X']
        hat_y = state['HAT_Y']
        global prev_hat
        if 'prev_hat' not in globals(): prev_hat = {'u':False, 'd':False, 'l':False, 'r':False}
        
        # D-pad Up/Down (Y is -1 for UP, 1 for DOWN)
        u_p = hat_y == -1; d_p = hat_y == 1
        l_p = hat_x == -1; r_p = hat_x == 1
        
        if u_p != prev_hat['u']: execute_action(current_map.get('btn_12', 'none'), u_p); prev_hat['u'] = u_p
        if d_p != prev_hat['d']: execute_action(current_map.get('btn_13', 'none'), d_p); prev_hat['d'] = d_p
        if l_p != prev_hat['l']: execute_action(current_map.get('btn_14', 'none'), l_p); prev_hat['l'] = l_p
        if r_p != prev_hat['r']: execute_action(current_map.get('btn_15', 'none'), r_p); prev_hat['r'] = r_p

        # 处理摇杆移动和虚拟键
        res = {'mx':0, 'my':0, 'sx':0, 'sy':0, 'keys': set()}
        handle_stick(current_map.get('stick_left', 'none'), l_x, l_y, res)
        handle_stick(current_map.get('stick_right', 'none'), r_x, r_y, res)
        
        if res['mx'] != 0 or res['my'] != 0:
            mouse_service.handle_move({'dx': res['mx'] * sens * 4, 'dy': res['my'] * sens * 4})
        if res['sx'] != 0 or res['sy'] != 0:
            mouse_service.handle_scroll({'dx': res['sx'] * sens * 2, 'dy': res['sy'] * sens * 2})
            
        # 释放不在 target 里的 key
        for k in list(active_keys):
            if k not in res['keys']:
                keyboard_service.handle_key_action({'key': k, 'action': 'up'})
                active_keys.remove(k)
        # 按下未在 active 里的 key
        for k in res['keys']:
            if k not in active_keys:
                keyboard_service.handle_key_action({'key': k, 'action': 'down'})
                active_keys.add(k)


def handle_stick(mode, xVal, yVal, res_dict):
    if mode == "mouse":
        if abs(xVal)>0: res_dict['mx'] += xVal
        if abs(yVal)>0: res_dict['my'] += yVal
        return
    if mode == "scroll":
        if abs(xVal)>0: res_dict['sx'] += xVal
        if abs(yVal)>0: res_dict['sy'] += yVal
        return

    layout = {}
    if mode == "wasd": layout = {'up': "w", 'down': "s", 'left': "a", 'right': "d"}
    elif mode == "hjkl": layout = {'up': "k", 'down': "j", 'left': "h", 'right': "l"}
    elif mode == "arrows": layout = {'up': "up", 'down': "down", 'left': "left", 'right': "right"}
    else: return

    threshold = 0.5
    if yVal < -threshold: res_dict['keys'].add(layout['up'])
    if yVal > threshold: res_dict['keys'].add(layout['down'])
    if xVal < -threshold: res_dict['keys'].add(layout['left'])
    if xVal > threshold: res_dict['keys'].add(layout['right'])

def start_threads():
    if inputs is not None:
        threading.Thread(target=poll_gamepad_state, daemon=True).start()
        threading.Thread(target=process_continuous, daemon=True).start()
