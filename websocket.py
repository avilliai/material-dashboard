from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import subprocess
import os
import eventlet

eventlet.monkey_patch()  # 必须在其他导入之前

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app,
                    cors_allowed_origins="*",
                    async_mode='eventlet')  # 明确指定异步模式


def read_output(script_path, sid):
    try:
        # 直接传递路径，无需额外引号
        process = subprocess.Popen(
            ['cmd.exe', '/c', script_path],  # 直接传递路径
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding='gbk',
            bufsize=1,
            universal_newlines=True
        )

        while True:
            output = process.stdout.readline()
            if not output and process.poll() is not None:
                break
            if output:
                socketio.emit('output', {'data': output}, room=sid)
    except Exception as e:
        socketio.emit('output', {'data': f'执行错误: {str(e)}'}, room=sid)

@socketio.on('start_script')
def handle_start_script(data):
    script_path = data.get('path')

    # 增强路径校验
    if not os.path.exists(script_path):
        emit('output', {'data': f'路径不存在: {script_path}'})
        return

    if not script_path.lower().endswith('.bat'):
        emit('output', {'data': '仅支持.bat文件'})
        return

    # 使用eventlet的绿色线程
    eventlet.spawn(read_output, script_path, request.sid)


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    socketio.run(app, debug=True, host='127.0.0.1', port=5007)