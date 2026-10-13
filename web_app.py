import platform
import socket
import psutil
from flask import Flask, render_template, request
from flask_socketio import SocketIO
from app_paths import resource_path

app = Flask(
    __name__,
    template_folder=resource_path('templates'),
    static_folder=resource_path('static'),
)
# 允许所有来源跨域，确保手机能连上
socketio = SocketIO(app, cors_allowed_origins="*")


def get_default_input_mode():
    """Choose Mac or Windows interaction defaults from the server OS."""
    return 'mac' if platform.system() == 'Darwin' else 'windows'

WIRELESS_HINTS = ("wlan", "wi-fi", "wifi", "wireless", "en0", "en1")
WIRED_HINTS = ("ethernet", "eth", "enp", "eno", "realtek", "intel")
VIRTUAL_HINTS = (
    "virtual", "vmware", "virtualbox", "vbox", "hyper-v", "vethernet",
    "wsl", "docker", "loopback", "tailscale", "zerotier", "radmin",
    "hamachi", "bluetooth", "tap-", "tun"
)

def get_all_ip_addresses():
    ip_list = []
    for interface, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                ip_list.append((interface, addr.address))
    return ip_list


def get_outbound_ip():
    """Return the local address the OS would use for a normal outbound route."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(0.3)
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return None


def get_interface_kind(interface):
    name = interface.casefold()
    if any(hint in name for hint in VIRTUAL_HINTS):
        return "虚拟网络"
    if any(hint in name for hint in WIRELESS_HINTS):
        return "Wi-Fi"
    if any(hint in name for hint in WIRED_HINTS):
        return "有线网络"
    return "其他网络"


def get_interface_score(interface, ip, outbound_ip, stats):
    name = interface.casefold()
    score = 0

    if any(hint in name for hint in VIRTUAL_HINTS):
        score -= 40
    elif any(hint in name for hint in WIRELESS_HINTS):
        score += 50
    elif any(hint in name for hint in WIRED_HINTS):
        score += 35
    else:
        score += 10

    interface_stats = stats.get(interface)
    if interface_stats is None or interface_stats.isup:
        score += 5
    else:
        score -= 20

    if ip == outbound_ip:
        score += 15
    if ip.startswith("169.254."):
        score -= 25

    return score


def get_connection_targets(port, http_mode=False):
    try:
        stats = psutil.net_if_stats()
    except Exception:
        stats = {}

    outbound_ip = get_outbound_ip()
    scheme = 'http' if http_mode else 'https'
    seen = set()
    targets = []

    for interface, ip in get_all_ip_addresses():
        if ip in seen:
            continue
        seen.add(ip)
        url = f"{scheme}://{ip}:{port}/"
        targets.append({
            "interface": interface,
            "ip": ip,
            "kind": get_interface_kind(interface, ip, outbound_ip, stats),
            "url": url,
            "score": get_interface_score(interface, ip, outbound_ip, stats),
        })

    targets.sort(key=lambda target: target["score"], reverse=True)
    return targets

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/connect')
def connect_page():
    port = int(request.environ.get('SERVER_PORT', 5888))
    # 自动检测协议：Werkzeug 下 SSL 握手由 socketio 处理，
    # 若请求是 http:// 进来的则 http_mode=True
    http_mode = request.environ.get('wsgi.url_scheme') == 'http'
    targets = get_connection_targets(port, http_mode=http_mode)
    return render_template(
        'connect.html',
        recommended=targets[0] if targets else None,
        alternatives=targets[1:] if len(targets) > 1 else [],
        target_count=len(targets),
    )

@app.route('/healthz')
def healthz():
    return 'ok'

@app.route('/touchpad')
def touchpad_page():
    return render_template('index.html', default_input_mode=get_default_input_mode())

@app.route('/k')
def keyboard_page(): 
    return render_template('keyboard.html', default_input_mode=get_default_input_mode())

@app.route('/v')
def voice_page():
    return render_template('voice.html', default_input_mode=get_default_input_mode())

@app.route('/test')
def vibe_test():
    return render_template('vibe_test.html')

@app.route('/t')
def air_mouse_test():
    return render_template('t.html')

@app.route('/r')
def real_mouse_page():
    return render_template('realmouse.html')

@app.route('/b')
def buttons_page():
    return render_template('buttons.html')

@app.route('/controller')
def controller_page():
    return render_template('controller.html')

@app.route('/settings')
def settings_page():
    return render_template('settings.html', os_type=platform.system())
