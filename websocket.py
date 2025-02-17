import os
import subprocess
import eventlet
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

eventlet.monkey_patch()  # 必须在其他导入之前

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

ERIDANUS_DIR = os.path.abspath("./Eridanus")  # 确保路径正确

def get_python_executable():
    """ 优先使用 environments 里的 Python，否则尝试 venv，再否则使用系统 Python """


    custom_python_path = os.path.join("environments", "Python311", "python.exe")
    venv_python_win = os.path.join(ERIDANUS_DIR, "venv", "Scripts", "python.exe")
    venv_python_linux = os.path.join(ERIDANUS_DIR, "venv", "bin", "python")

    if os.path.exists(custom_python_path):
        return custom_python_path
    elif os.path.exists(venv_python_win):
        return venv_python_win
    elif os.path.exists(venv_python_linux):
        return venv_python_linux
    else:
        return "python"  # 兜底方案，使用系统 Python

def run_script(sid):
    """ 进入 Eridanus 目录，选择 Python 解释器并运行 main.py，实时返回输出 """
    try:
        if not os.path.exists(ERIDANUS_DIR):
            socketio.emit('output', {'data': f'错误: 目录 {ERIDANUS_DIR} 不存在'}, room=sid)
            return

        python_exe = get_python_executable()
        main_script = os.path.join(ERIDANUS_DIR, "main.py")

        # 确保进入 Eridanus 目录
        prev_cwd = os.getcwd()  # 记录当前工作目录
        os.chdir(ERIDANUS_DIR)  # 临时切换到 Eridanus

        process = subprocess.Popen(
            [python_exe, main_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        os.chdir(prev_cwd)  # 运行完后恢复原工作目录

        while True:
            output = process.stdout.readline()
            if not output and process.poll() is not None:
                break
            if output:
                socketio.emit('output', {'data': output.strip()}, room=sid)

    except Exception as e:
        socketio.emit('output', {'data': f'执行错误: {str(e)}'}, room=sid)

@socketio.on('start_script')
def handle_start_script():
    eventlet.spawn(run_script, request.sid)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    socketio.run(app, debug=True, host='127.0.0.1', port=5007)
