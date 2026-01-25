import platform
import socket
import psutil
from flask import Flask, render_template
from flask_socketio import SocketIO

app = Flask(__name__)
# 允许所有来源跨域，确保手机能连上
socketio = SocketIO(app, cors_allowed_origins="*")

def get_all_ip_addresses():
    ip_list = []
    for interface, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                ip_list.append((interface, addr.address))
    return ip_list

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/k')
def keyboard_page(): 
    return render_template('keyboard.html')

@app.route('/v')
def voice_page():
    return render_template('voice.html')

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
