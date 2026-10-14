import platform
import os
import sys
import subprocess
import tempfile
import threading
import time
import webbrowser

# macOS 隐藏 Dock 图标逻辑 — 仅在打包模式或显式开启时执行，
# 在脚本模式下调用 setActivationPolicy_(Prohibited) 会干扰 AppKit 事件循环，
# 与 pystray NSStatusItem 线程共存时会触发 SIGILL。
if platform.system() == 'Darwin':
    _TRAY_MODE_AVAILABLE = False
    try:
        import AppKit
        _TRAY_MODE_AVAILABLE = True
    except ImportError:
        pass

from web_app import app, socketio, get_all_ip_addresses
from app_paths import app_dir, is_frozen, resource_path
from debug_logging import debug_socket_event
import mouse_service
import keyboard_service
import config_manager
import gamepad_service

PORT = 5888
# Ensure relative config/log paths stay next to the executable.
os.chdir(app_dir())

# 启动手柄后台服务 (如果已安装 inputs)
gamepad_service.start_threads()

def status_thread():
    while True:
        socketio.emit('gp_status', {
            'connected': gamepad_service.gamepad_connected,
            'name': gamepad_service.gamepad_name
        })
        time.sleep(1)

threading.Thread(target=status_thread, daemon=True).start()


def hide_console_window():
    """Hide the attached console window on Windows when launched via python.exe."""
    if platform.system() != 'Windows':
        return
    try:
        import ctypes
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
    except Exception:
        pass


def open_page(path='/', http_mode=False):
    scheme = 'http' if http_mode else 'https'
    webbrowser.open(f'{scheme}://127.0.0.1:{PORT}{path}', new=2)


def show_info_dialog(title, message, error=False):
    """Show a simple native dialog that works from the tray thread."""
    if platform.system() == 'Windows':
        try:
            import ctypes
            flags = 0x00000010 if error else 0x00000040  # ICONERROR / ICONINFORMATION
            ctypes.windll.user32.MessageBoxW(None, message, title, 0x00000000 | flags)
            return
        except Exception:
            pass

    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        if error:
            messagebox.showerror(title, message, parent=root)
        else:
            messagebox.showinfo(title, message, parent=root)
        root.destroy()
    except Exception:
        pass


def trust_ssl_certificate():
    """Import the bundled self-signed cert into the current user's Trusted Root store."""
    if platform.system() != 'Windows':
        show_info_dialog('信任 SSL 证书', '当前仅支持在 Windows 上自动导入证书。', error=True)
        return

    pem_path = resource_path('cert.pem')
    if not os.path.exists(pem_path):
        show_info_dialog('信任 SSL 证书', '未找到证书文件 cert.pem。', error=True)
        return

    der_path = None
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives.serialization import Encoding

        with open(pem_path, 'rb') as f:
            cert = x509.load_pem_x509_certificate(f.read())

        fd, der_path = tempfile.mkstemp(suffix='.cer', prefix='airmouse-cert-')
        os.close(fd)
        with open(der_path, 'wb') as f:
            f.write(cert.public_bytes(Encoding.DER))

        creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        result = subprocess.run(
            ['certutil', '-addstore', '-user', 'Root', der_path],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            creationflags=creationflags,
        )

        output = ((result.stdout or '') + '\n' + (result.stderr or '')).strip()
        already = 'already in store' in output.lower() or '已经在存储' in output or '已在存储' in output

        if result.returncode == 0 or already:
            show_info_dialog(
                '信任 SSL 证书',
                '已将 AirMouse 证书导入当前用户的“受信任的根证书颁发机构”。\n\n'
                '请完全退出并重新打开 Chrome / Edge 后再访问本机页面。\n'
                '手机端仍需在手机上自行选择继续访问或信任证书。',
            )
        else:
            show_info_dialog(
                '信任 SSL 证书',
                '导入失败。\n\n' + (output or f'certutil 退出码: {result.returncode}'),
                error=True,
            )
    except Exception as exc:
        show_info_dialog('信任 SSL 证书', f'导入失败：{exc}', error=True)
    finally:
        if der_path and os.path.exists(der_path):
            try:
                os.remove(der_path)
            except OSError:
                pass


def create_tray_image():
    from PIL import Image, ImageDraw

    icon_path = resource_path('static', 'app-icon.png')
    try:
        image = Image.open(icon_path).convert('RGBA')
        return image.resize((64, 64), Image.Resampling.LANCZOS)
    except Exception:
        size = 64
        image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((4, 4, 60, 60), radius=14, fill=(16, 38, 26, 255))
        draw.rounded_rectangle((14, 14, 50, 50), radius=8, outline=(89, 227, 145, 255), width=4)
        draw.rectangle((20, 20, 28, 28), fill=(89, 227, 145, 255))
        draw.rectangle((36, 36, 44, 44), fill=(89, 227, 145, 255))
        return image


def start_server(http_mode=False):
    ssl_ctx = None
    if not http_mode:
        ssl_ctx = (resource_path('cert.pem'), resource_path('key.pem'))
    socketio.run(
        app,
        host='0.0.0.0',
        port=PORT,
        ssl_context=ssl_ctx,
        allow_unsafe_werkzeug=True,
    )


def show_startup_dialog():
    """Desktop tip shown when the packaged EXE starts."""
    import tkinter as tk
    from tkinter import font as tkfont

    root = tk.Tk()
    root.title("AirMouse")
    root.resizable(False, False)
    root.attributes('-topmost', True)

    try:
        root.iconphoto(True, tk.PhotoImage(file=resource_path('static', 'app-icon.png')))
    except Exception:
        pass

    width, height = 420, 210
    x = (root.winfo_screenwidth() - width) // 2
    y = (root.winfo_screenheight() - height) // 3
    root.geometry(f'{width}x{height}+{x}+{y}')
    root.configure(bg='#15151c')

    frame = tk.Frame(root, bg='#15151c', padx=28, pady=24)
    frame.pack(fill='both', expand=True)

    title_font = tkfont.Font(family='Microsoft YaHei UI', size=13, weight='bold')
    body_font = tkfont.Font(family='Microsoft YaHei UI', size=10)

    tk.Label(
        frame,
        text='AirMouse 已启动',
        font=title_font,
        fg='#ffffff',
        bg='#15151c',
        anchor='w',
    ).pack(fill='x')

    tk.Label(
        frame,
        text='请检查系统托盘，AirMouse 已在后台运行。\n之后可随时从托盘图标打开主页或扫码连接。',
        font=body_font,
        fg='#b0b0b8',
        bg='#15151c',
        justify='left',
        anchor='w',
        pady=(12, 22),
    ).pack(fill='x')

    buttons = tk.Frame(frame, bg='#15151c')
    buttons.pack(fill='x')

    def open_home():
        open_page('/')
        root.destroy()

    def dismiss():
        root.destroy()

    open_btn = tk.Button(
        buttons,
        text='打开网页',
        command=open_home,
        font=body_font,
        bg='#7b4dff',
        fg='#ffffff',
        activebackground='#6a3de6',
        activeforeground='#ffffff',
        relief='flat',
        padx=16,
        pady=8,
        cursor='hand2',
    )
    open_btn.pack(side='right')

    close_btn = tk.Button(
        buttons,
        text='知道了',
        command=dismiss,
        font=body_font,
        bg='#2a2a35',
        fg='#dddddd',
        activebackground='#3a3a48',
        activeforeground='#ffffff',
        relief='flat',
        padx=16,
        pady=8,
        cursor='hand2',
    )
    close_btn.pack(side='right', padx=(0, 10))

    root.protocol('WM_DELETE_WINDOW', dismiss)
    root.bind('<Escape>', lambda _event: dismiss())
    root.bind('<Return>', lambda _event: open_home())
    root.focus_force()
    root.mainloop()


def _tray_available():
    """Detect whether pystray can run in the current environment without crashing."""
    if platform.system() == 'Darwin' and not is_frozen():
        # 脚本模式下 macOS 的 AppKit NSApplication 与 pystray NSStatusItem 线程
        # 共存会触发 SIGILL，无法被 Python except 捕获，直接跳过。
        return False
    try:
        import pystray  # noqa: F401
        return True
    except ImportError:
        return False


def run_with_tray(http_mode=False):
    import pystray
    from pystray import MenuItem as Item

    def on_open_home(icon, item):
        open_page('/', http_mode=http_mode)

    def on_open_qr(icon, item):
        open_page('/connect', http_mode=http_mode)

    def on_trust_cert(icon, item):
        threading.Thread(target=trust_ssl_certificate, daemon=True).start()

    def on_quit(icon, item):
        icon.stop()
        os._exit(0)

    menu = pystray.Menu(
        Item('打开主页', on_open_home, default=True),
        Item('扫码连接', on_open_qr),
        Item('信任 SSL 证书', on_trust_cert),
        Item('退出', on_quit),
    )
    icon = pystray.Icon('AirMouse', create_tray_image(), 'AirMouse 已在后台运行', menu)

    server = threading.Thread(target=lambda: start_server(http_mode=http_mode), daemon=True)
    server.start()

    # Keep tkinter on the main thread; run the tray icon beside it.
    tray_thread = threading.Thread(target=icon.run, daemon=True)
    tray_thread.start()

    if is_frozen() or os.environ.get('AIRMOUSE_STARTUP_TIP') == '1':
        # Give the server a moment so “打开网页” is more likely to work immediately.
        time.sleep(0.8)
        try:
            show_startup_dialog()
        except Exception:
            pass

    tray_thread.join()


# --- SocketIO 事件绑定 ---

@socketio.on('connect')
def handle_connect():
    os_type = platform.system()
    socketio.emit('os_info', {'os': os_type})

@socketio.on('load_macros')
def handle_load():
    data = config_manager.load_macros()
    socketio.emit('macros_loaded', data)

@socketio.on('save_macros')
def handle_save(data):
    config_manager.save_macros(data)

@socketio.on('load_gp_macros')
def handle_gp_load():
    data = config_manager.load_gp_macros()
    socketio.emit('gp_macros_loaded', data)

@socketio.on('save_gp_macros')
def handle_gp_save(data):
    config_manager.save_gp_macros(data)
    gamepad_service.update_config(data)

@socketio.on('get_gamepads')
def handle_get_gps():
    gps = gamepad_service.get_gamepad_list()
    socketio.emit('gamepads_list', gps)

@socketio.on('select_gamepad')
def handle_select_gp(index):
    gamepad_service.selected_index = index
    handle_get_gps() # 刷新状态

@socketio.on('check_permissions')
def on_check_permissions():
    import platform
    from mouse_service import is_accessibility_granted
    import os as _os
    socketio.emit('permissions_status', {
        'accessibility': is_accessibility_granted() if platform.system() == 'Darwin' else True,
        'os': platform.system(),
        'is_https': not (_os.environ.get('AIRMOUSE_HTTP') == '1'),
    })

# 鼠标事件
@socketio.on('move')
def on_move(data):
    debug_socket_event('move', data)
    mouse_service.handle_move(data)

@socketio.on('click')
def on_click(data):
    debug_socket_event('click', data)
    mouse_service.handle_click(data)

@socketio.on('drag_start')
def on_drag_start():
    debug_socket_event('drag_start')
    mouse_service.handle_drag_start()

@socketio.on('drag_end')
def on_drag_end():
    debug_socket_event('drag_end')
    mouse_service.handle_drag_end()

@socketio.on('mid_down')
def on_mid_down():
    debug_socket_event('mid_down')
    mouse_service.handle_mid_down()

@socketio.on('mid_up')
def on_mid_up():
    debug_socket_event('mid_up')
    mouse_service.handle_mid_up()

@socketio.on('scroll')
def on_scroll(data):
    debug_socket_event('scroll', data)
    mouse_service.handle_scroll(data)

# 键盘事件
@socketio.on('type_text')
def on_type(data):
    debug_socket_event('type_text', data)
    keyboard_service.handle_type_text(data)

@socketio.on('key_action')
def on_key(data):
    debug_socket_event('key_action', data)
    keyboard_service.handle_key_action(data)

@socketio.on('key_combo')
def on_combo(data):
    debug_socket_event('key_combo', data)
    keyboard_service.handle_combo(data)


@socketio.on('disconnect')
def on_disconnect(reason=None):
    debug_socket_event('disconnect', {'reason': str(reason)} if reason else None)
    # A dropped browser connection can skip the matching drag_end packet.
    # Release any held Mac buttons so the next single-finger move is a warp.
    mouse_service.release_all_buttons()

def _check_mac_permissions():
    """On macOS, ensure the current process has Accessibility permission.
    Without it, CGEventPost (keyboard / click / scroll) is silently dropped.
    Mouse move (CGWarpMouseCursorPosition) still works without the permission.
    """
    if platform.system() != 'Darwin':
        return
    try:
        from mouse_service import is_accessibility_granted
        if is_accessibility_granted():
            return
        print("\n⚠️  未检测到 macOS 辅助功能权限！键盘 / 鼠标点击 / 滚动功能将不生效。", flush=True)
        print("   请打开：系统设置 → 隐私与安全性 → 辅助功能 → 添加 Python", flush=True)
        print("   （uv 管理的 Python 路径：", end="", flush=True)
        import shutil
        print(shutil.which('python3') or sys.executable, "）", flush=True)
        print("   授权后重启 AirMouse 即可正常使用。", flush=True)
        print("═"*60 + "\n", flush=True)
    except Exception:
        pass


def main():
    use_tray = os.environ.get('AIRMOUSE_NO_TRAY') != '1'
    hide_console = os.environ.get('AIRMOUSE_SHOW_CONSOLE') != '1'
    http_mode = os.environ.get('AIRMOUSE_HTTP') == '1'
    scheme = 'http' if http_mode else 'https'

    if hide_console:
        hide_console_window()

    if use_tray:
        if _tray_available():
            try:
                run_with_tray(http_mode=http_mode)
                sys.exit(0)
            except Exception:
                # Fall back to console mode if tray dependencies are unavailable.
                pass
        else:
            print("⚠️  托盘不可用（当前环境不支持），使用控制台模式。", flush=True)

    _check_mac_permissions()

    ips = get_all_ip_addresses()

    print("\n" + "═"*60)
    print("🚀 Remote Pro Server 已启动！" + ("  [HTTP 模式]" if http_mode else ""))
    print(f"🏠 当前系统: {platform.system()}")
    print("📱 请在浏览器访问以下地址:")
    print(f"🖥️  本机主页: {scheme}://127.0.0.1:{PORT}/")
    print(f"📷  扫码连接: {scheme}://127.0.0.1:{PORT}/connect")
    if http_mode:
        print("💡 当前为 HTTP 模式，陀螺仪（gyro）功能不可用。", flush=True)

    for interface, ip in ips:
        tag = ""
        if any(keyword in interface.lower() for keyword in ["wlan", "wi-fi", "eth", "en0", "en1"]):
            tag = " [推荐]"
        print(f"  ➤  {scheme}://{ip}:{PORT}{tag}")

    print("═"*60 + "\n")

    start_server(http_mode=http_mode)


if __name__ == '__main__':
    main()
