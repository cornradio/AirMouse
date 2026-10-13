"""
AirMouse mouse service.

macOS strategy (all via ctypes, thread-safe):
  - Mouse movement: CGWarpMouseCursorPosition  (no Accessibility permission needed)
  - Click / drag  : CGEventPost + CGEventCreateMouseEvent
  - Scroll        : CGEventPost + CGEventCreateScrollWheelEvent

Windows / Linux: pyautogui.
"""

import platform
import ctypes
import math
import time
import threading

from debug_logging import debug_log

_IS_MAC = platform.system() == 'Darwin'
_SMOOTH_SCROLL_X = 0.0
_SMOOTH_SCROLL_Y = 0.0


def _smooth_pixels_to_wheel_steps(dx, dy, threshold=40):
    """Convert touchpad pixel deltas to cross-platform wheel steps without loss."""
    global _SMOOTH_SCROLL_X, _SMOOTH_SCROLL_Y
    _SMOOTH_SCROLL_X += dx
    _SMOOTH_SCROLL_Y += dy
    wheel_x = int(_SMOOTH_SCROLL_X / threshold)
    wheel_y = int(_SMOOTH_SCROLL_Y / threshold)
    _SMOOTH_SCROLL_X -= wheel_x * threshold
    _SMOOTH_SCROLL_Y -= wheel_y * threshold
    return wheel_x, wheel_y

# =============================================================================
# macOS — all Quartz calls go through ctypes (thread-safe, no pyobjc race)
# =============================================================================

if _IS_MAC:
    _quartz = ctypes.CDLL('/System/Library/Frameworks/Quartz.framework/Quartz')
    _core_foundation = ctypes.CDLL(
        '/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation'
    )

    class _CGPoint(ctypes.Structure):
        _fields_ = [('x', ctypes.c_double), ('y', ctypes.c_double)]

    _CFTypeRef = ctypes.c_void_p

    _quartz.CGEventCreate.restype = _CFTypeRef
    _quartz.CGEventCreate.argtypes = [_CFTypeRef]
    _quartz.CGEventGetLocation.restype = _CGPoint
    _quartz.CGEventGetLocation.argtypes = [_CFTypeRef]
    _quartz.CGWarpMouseCursorPosition.restype = None
    _quartz.CGWarpMouseCursorPosition.argtypes = [_CGPoint]
    _quartz.CGEventCreateMouseEvent.restype = _CFTypeRef
    _quartz.CGEventCreateMouseEvent.argtypes = [_CFTypeRef, ctypes.c_uint32, _CGPoint, ctypes.c_uint32]
    _quartz.CGEventCreateScrollWheelEvent.restype = _CFTypeRef
    _quartz.CGEventCreateScrollWheelEvent.argtypes = [
        _CFTypeRef, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_int32, ctypes.c_int32,
    ]
    _quartz.CGEventPost.restype = None
    _quartz.CGEventPost.argtypes = [ctypes.c_uint32, _CFTypeRef]
    _core_foundation.CFRelease.restype = None
    _core_foundation.CFRelease.argtypes = [_CFTypeRef]

    _kCGHIDEventTap   = 0
    _kCGScrollUnitPixel = 1

    _BTN = {
        'left':   (0, 1,  2),
        'right':  (1, 3,  4),
        'middle': (2, 25, 26),
        # Quartz supports other mouse buttons by USB button number; macOS
        # emits the same OtherMouse event type for these side buttons.
        'x1':     (3, 25, 26),
        'x2':     (4, 25, 26),
    }
    # Quartz event types for pointer movement while a button remains down.
    # A cursor warp changes the pointer location but does not deliver the drag
    # stream applications expect, so active gestures must post these events.
    _DRAG_EVENT = {'left': 6, 'right': 7}
    _pressed_buttons = set()
    _pressed_buttons_lock = threading.Lock()

    def _release_event(event):
        """Release a Quartz event created by one of the CGEventCreate APIs."""
        if event:
            _core_foundation.CFRelease(event)

    def _get_pos() -> tuple:
        ev = _quartz.CGEventCreate(None)
        if not ev:
            return 0.0, 0.0
        try:
            p = _quartz.CGEventGetLocation(ev)
            return p.x, p.y
        finally:
            _release_event(ev)

    def _warp(x, y):
        _quartz.CGWarpMouseCursorPosition(_CGPoint(x, y))

    def _post_mouse_event(event_type, button_id, x, y):
        ev = _quartz.CGEventCreateMouseEvent(None, event_type, _CGPoint(x, y), button_id)
        if not ev:
            debug_log('quartz', 'mouse_event_create_failed', event_type=event_type,
                      button_id=button_id, x=x, y=y)
            return
        try:
            _quartz.CGEventPost(_kCGHIDEventTap, ev)
            debug_log('quartz', 'mouse_event_posted', event_type=event_type,
                      button_id=button_id, x=x, y=y)
        finally:
            _release_event(ev)

    def _post_scroll(dy, dx=0):
        # Quartz orders scroll deltas as vertical (wheel1), then horizontal (wheel2).
        ev = _quartz.CGEventCreateScrollWheelEvent(
            None, _kCGScrollUnitPixel, 2, int(dy), int(dx)
        )
        if not ev:
            debug_log('quartz', 'scroll_event_create_failed', dx=dx, dy=dy)
            return
        try:
            _quartz.CGEventPost(_kCGHIDEventTap, ev)
            debug_log('quartz', 'scroll_event_posted', dx=dx, dy=dy)
        finally:
            _release_event(ev)

    def mac_move(dx, dy):
        with _pressed_buttons_lock:
            cx, cy = _get_pos()
            x, y = cx + dx, cy + dy
            if not _pressed_buttons:
                _warp(x, y)
                debug_log('quartz', 'cursor_warped', from_x=cx, from_y=cy, x=x, y=y)
                return

            # Drag events carry both the new location and the held button.
            # Quartz has dedicated left/right types; center and side buttons
            # share OtherMouseDragged (27) and retain their button number.
            button = next(iter(_pressed_buttons))
            button_id = _BTN.get(button, _BTN['left'])[0]
            event_type = _DRAG_EVENT.get(button, 27)
            _post_mouse_event(event_type, button_id, x, y)

    def mac_click(button):
        btn_id, down_evt, up_evt = _BTN.get(button, _BTN['left'])
        x, y = _get_pos()
        try:
            _post_mouse_event(down_evt, btn_id, x, y)
            time.sleep(0.02)
        finally:
            # Even if posting down raises, a release prevents a stuck button.
            _post_mouse_event(up_evt, btn_id, x, y)

    def mac_down(button):
        btn_id, down_evt, _ = _BTN.get(button, _BTN['left'])
        with _pressed_buttons_lock:
            x, y = _get_pos()
            _post_mouse_event(down_evt, btn_id, x, y)
            _pressed_buttons.add(button)

    def mac_up(button):
        btn_id, _, up_evt = _BTN.get(button, _BTN['left'])
        with _pressed_buttons_lock:
            x, y = _get_pos()
            try:
                _post_mouse_event(up_evt, btn_id, x, y)
            finally:
                # Do not leave stale button state if Quartz posting fails.
                _pressed_buttons.discard(button)

    def mac_scroll(dx, dy, speed=1, smooth=False):
        # speed multiplier: 2-finger scroll → speed 2, 4-finger → speed 4
        # Match the pre-adapter macOS behavior, which inverted pynput's wheel
        # direction to follow the touch surface's natural scroll direction.
        # Smooth trackpad events are already pixel deltas; preserve their
        # granularity instead of converting them into large wheel jumps.
        scale = 1 if smooth else speed * 5
        _post_scroll(-dy * scale, -dx * scale)

    # Permission check
    _ax = ctypes.CDLL('/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices')
    _ax.AXIsProcessTrusted.restype = ctypes.c_bool
    _ax.AXIsProcessTrusted.argtypes = []

    def is_accessibility_granted() -> bool:
        return bool(_ax.AXIsProcessTrusted())

# =============================================================================
# Windows / Linux
# =============================================================================

if not _IS_MAC:
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0

    def _extra_button_action(button, pressed):
        """Use native mouse APIs for side buttons absent from pyautogui."""
        if button not in ('x1', 'x2'):
            return False
        if platform.system() == 'Windows':
            # mouse_event uses XBUTTON1/XBUTTON2 in dwData for side buttons.
            flag = 0x0080 if pressed else 0x0100  # XDOWN / XUP
            button_id = 1 if button == 'x1' else 2
            ctypes.windll.user32.mouse_event(flag, 0, 0, button_id, 0)
            return True
        if platform.system() == 'Linux':
            # pyautogui exposes horizontal scrolling on Linux but only three
            # mouse buttons; pynput retains X11 buttons 8 and 9.
            from pynput.mouse import Button, Controller
            controller = Controller()
            (controller.press if pressed else controller.release)(
                Button.x1 if button == 'x1' else Button.x2
            )
            return True
        return False

    def mac_move(dx, dy):
        pyautogui.moveRel(dx, dy)

    def mac_click(button):
        if _extra_button_action(button, True):
            _extra_button_action(button, False)
        else:
            pyautogui.click(button=button if button in ('left', 'right', 'middle') else 'left')

    def mac_down(button):
        if not _extra_button_action(button, True):
            pyautogui.mouseDown(button=button if button in ('left', 'right', 'middle') else 'left')

    def mac_up(button):
        if not _extra_button_action(button, False):
            pyautogui.mouseUp(button=button if button in ('left', 'right', 'middle') else 'left')

    def mac_scroll(dx, dy, speed=1, smooth=False):
        if smooth:
            # A Mac browser can control a Windows/Linux host too. Accumulate
            # its pixel deltas into wheel notches rather than truncating each
            # small movement independently.
            wheel_x, wheel_y = _smooth_pixels_to_wheel_steps(dx, dy)
            vertical = -wheel_y
            horizontal = -wheel_x
        else:
            vertical = int(dy * speed)
            horizontal = int(dx * speed)

        if vertical:
            pyautogui.scroll(vertical)
        if horizontal:
            if platform.system() == 'Linux':
                pyautogui.hscroll(horizontal)
            elif platform.system() == 'Windows':
                # Windows expects horizontal wheel deltas in multiples of 120.
                ctypes.windll.user32.mouse_event(
                    0x01000, 0, 0, horizontal * 120, 0
                )

    def is_accessibility_granted():
        return True


# =============================================================================
# Public handlers
# =============================================================================

def _wake_up_cursor():
    if platform.system() == 'Windows':
        ctypes.windll.user32.mouse_event(0x0001, 1, 1, 0, 0)
        time.sleep(0.01)
        ctypes.windll.user32.mouse_event(0x0001, -1, -1, 0, 0)


def handle_move(data):
    # A NaN from browser sensor data is serialized by Socket.IO as JSON null.
    # Treat missing/invalid axes as zero so one malformed sample cannot kill
    # the Socket.IO worker or disable later single-finger input.
    data = data if isinstance(data, dict) else {}
    dx = _finite_delta(data.get('dx', 0))
    dy = _finite_delta(data.get('dy', 0))
    debug_log('mouse', 'move', dx=dx, dy=dy, raw=data)
    mac_move(dx, dy)
    _wake_up_cursor()


def _finite_delta(value):
    """Return a finite pointer delta, converting malformed values to zero."""
    if isinstance(value, bool):
        return 0.0
    try:
        value = float(value)
    except (TypeError, ValueError):
        return 0.0
    return value if math.isfinite(value) else 0.0


def handle_click(data):
    mac_click(data.get('button', 'left'))


def handle_button_action(button, pressed):
    """Hold or release a mouse button through the active platform backend."""
    (mac_down if pressed else mac_up)(button)


def handle_drag_start():
    mac_down('left')


def handle_drag_end():
    mac_up('left')


def release_all_buttons():
    """Release buttons held by the Mac backend, such as after socket loss."""
    if not _IS_MAC:
        return
    with _pressed_buttons_lock:
        buttons = tuple(_pressed_buttons)
    for button in buttons:
        mac_up(button)


def handle_mid_down():
    mac_down('middle')


def handle_mid_up():
    mac_up('middle')


def handle_scroll(data):
    dx = data.get('dx', 0)
    dy = data.get('dy', 0)
    speed = data.get('speed', 1)
    smooth = bool(data.get('smooth', False))
    mac_scroll(dx, dy, speed, smooth=smooth)
