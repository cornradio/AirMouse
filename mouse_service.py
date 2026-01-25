import platform
from pynput.mouse import Controller, Button

mouse = Controller()

def handle_move(data):
    # dx, dy 由前端根据灵敏度计算后传入
    mouse.move(data['dx'], data['dy'])

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
    # macOS 滚动方向通常与 Windows 相反
    dy = data['dy']
    if platform.system() == 'Darwin':
        mouse.scroll(0, -dy)
    else:
        mouse.scroll(0, dy)
