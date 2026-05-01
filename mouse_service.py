import platform
import ctypes
import time
from pynput.mouse import Controller, Button

# macOS 兼容性补丁：处理某些 pyobjc 版本缺失 CGDisplayPixelsHigh 的问题
if platform.system() == 'Darwin':
    try:
        import Quartz
        if not hasattr(Quartz, 'CGDisplayPixelsHigh'):
            def CGDisplayPixelsHigh(display_id):
                return int(Quartz.CGDisplayBounds(display_id).size.height)
            Quartz.CGDisplayPixelsHigh = CGDisplayPixelsHigh
    except Exception:
        pass

mouse = Controller()

def wake_up_cursor():
    if platform.system() == 'Windows':
        MOUSEEVENTF_MOVE = 0x0001
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_MOVE, 1, 1, 0, 0)
        time.sleep(0.01)
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_MOVE, -1, -1, 0, 0)

def handle_move(data):
    mouse.move(data['dx'], data['dy'])
    wake_up_cursor()

def handle_click(data):
    button_type = data.get('button')
    if button_type == 'left':
        mouse.click(Button.left)
    elif button_type == 'right':
        mouse.click(Button.right)
    elif button_type == 'middle':
        mouse.click(Button.middle)
    elif button_type == 'x1':
        mouse.click(Button.x1)
    elif button_type == 'x2':
        mouse.click(Button.x2)

def handle_drag_start():
    mouse.release(Button.left)
    mouse.press(Button.left)

def handle_drag_end():
    mouse.release(Button.left)

def handle_mid_down():
    mouse.release(Button.middle)
    mouse.press(Button.middle)

def handle_mid_up():
    mouse.release(Button.middle)

def handle_scroll(data):
    # dx: 水平, dy: 垂直
    dx = data.get('dx', 0)
    dy = data.get('dy', 0)
    
    # macOS 滚动方向通常与 Windows 相反
    if platform.system() == 'Darwin':
        mouse.scroll(-dx, -dy)
    else:
        mouse.scroll(dx, dy)
