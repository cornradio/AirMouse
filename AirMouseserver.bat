@echo off
echo 正在检查 Python 依赖...
pip install flask flask-socketio pyOpenSSL pynput
python server.py
pause