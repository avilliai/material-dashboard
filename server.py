# encoding: utf-8
import asyncio
import json
import threading
import time
from collections import OrderedDict

import websockets
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

from ruamel.yaml import YAML, comments
from threading import Thread
import subprocess
import os


from ruamel.yaml.scalarstring import DoubleQuotedScalarString, SingleQuotedScalarString

app = Flask(__name__,static_folder="websources", static_url_path="",template_folder='websources')
CORS(app)  # 启用跨域支持
custom_git_path = os.path.join("environments", "MinGit", "cmd", "git.exe")
if os.path.exists(custom_git_path):
    git_path = custom_git_path
else:
    git_path = "git"
print(f"Git path: {git_path}")
#可用的git源
REPO_SOURCES = [
   "https://ghfast.top/https://github.com/avilliai/Eridanus.git",
   "https://mirror.ghproxy.com/https://github.com/avilliai/Eridanus",
   "https://github.moeyy.xyz/https://github.com/avilliai/Eridanus",
   "https://github.com/avilliai/Eridanus.git",
   "https://gh.llkk.cc/https://github.com/avilliai/Eridanus.git",
   "https://gitclone.com/github.com/avilliai/Eridanus.git"
]

# 文件路径配置
YAML_FILES = {
    "basic_config.yaml": "Eridanus/config/basic_config.yaml",
    "api.yaml": "Eridanus/config/api.yaml",
    "settings.yaml": "Eridanus/config/settings.yaml",
    "controller.yaml": "Eridanus/config/controller.yaml"
}

# 初始化 YAML 解析器（支持注释）
yaml = YAML()
yaml.preserve_quotes = True
"""
新旧数据合并
"""

def merge_dicts(old, new):
    """
    递归合并旧数据和新数据
    """
    for k, v in old.items():
        # 如果值是一个字典，并且键在新的yaml文件中，那么我们就递归地更新键值对
        if isinstance(v, dict) and k in new and isinstance(new[k], dict):
            merge_dicts(v, new[k])
        # 如果值是列表，且新旧值都是列表，则合并并去重
        elif isinstance(v, list) and k in new and isinstance(new[k], list):
            # 合并列表并去重，保留旧列表顺序
            new[k] = [item for item in v if v is not None]
        elif k in new and type(v) != type(new[k]):
            if isinstance(v, DoubleQuotedScalarString) or isinstance(v, SingleQuotedScalarString):
                v = str(v)
                new[k] = v
            else:
                print(f"类型冲突 key: {k}, old value type: {type(v)}, new value type: {type(new[k])}")
                continue  # 跳过对新值的覆盖
        # 如果键在新的yaml文件中且类型一致，则更新值
        elif k in new:
            print(f"更新 key: {k}, old value: {v}, new value: {new[k]}")
            new[k] = v
        # 如果键不在新的yaml中，直接添加
        else:
            print(f"移除键 key: {k}, value: {v}")


def conflict_file_dealer(old_data: dict, file_new='new_aiReply.yaml'):
    print(f"冲突文件处理: {file_new}")

    old_data=yaml.load(json.dumps(old_data))
    # 加载新的YAML文件
    with open(file_new, 'r', encoding="utf-8") as file:
        new_data = yaml.load(file)

    # 遍历旧的YAML数据并更新新的YAML数据中的相应值
    merge_dicts(old_data, new_data)

    # 把新的YAML数据保存到新的文件中，保留注释
    with open(file_new, 'w', encoding="utf-8") as file:
        yaml.dump(new_data, file)
    return True

def extract_comments(data, path="", comments_dict=None):
    if comments_dict is None:
        comments_dict = {}

    if isinstance(data, comments.CommentedMap):
        for key, value in data.items():
            new_path = f"{path}.{key}" if path else key
            # 提取行尾注释
            if key in data.ca.items and data.ca.items[key][2]:
                comment = data.ca.items[key][2].value.strip("# \n")
                comments_dict[new_path] = comment
            # 递归处理子节点
            extract_comments(value, new_path, comments_dict)

    elif isinstance(data, comments.CommentedSeq):
        for index, item in enumerate(data):
            new_path = f"{path}[{index}]"
            # 序列整体注释（如果存在）
            if data.ca.comment and data.ca.comment[0]:
                comments_dict[path] = data.ca.comment[0].value.strip("# \n")
            # 递归处理子节点
            extract_comments(item, new_path, comments_dict)

    return comments_dict
def extract_key_order(data, path="", order_dict=None):
    if order_dict is None:
        order_dict = {}

    if isinstance(data, comments.CommentedMap):
        order_dict[path] = list(data.keys())  # 记录当前层级 key 的顺序
        for key, value in data.items():
            new_path = f"{path}.{key}" if path else key
            extract_key_order(value, new_path, order_dict)

    elif isinstance(data, comments.CommentedSeq):
        # 对于序列，记录其位置
        for index, item in enumerate(data):
            new_path = f"{path}[{index}]"
            extract_key_order(item, new_path, order_dict)

    return order_dict
def load_yaml_with_comments(file_path):

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.load(f)
        # 提取所有注释
        order = extract_key_order(data)
        comments = extract_comments(data)
        return {"data": data, "comments": comments,"order": order}
    except Exception as e:
        return {"error": str(e)}

def load_yaml(file_path):
    """加载 YAML 文件并返回内容及注释"""
    try:
        return load_yaml_with_comments(file_path)
    except Exception as e:
        return {"error": str(e)}

def save_yaml(file_path, data):
    """将数据保存回 YAML 文件"""

    #print(f"保存文件: {file_path}")
    #print(f"数据: {data}")
    return conflict_file_dealer(data["data"], file_path)

def has_eridanus():
    """判断是否安装了Eridanus"""
    #测试不存在的路径
    dir_path = "Eridanus"
    if os.path.isdir(dir_path):
        return True
    else:
        return False

@app.route("/api/load/<filename>", methods=["GET"])
def load_file(filename):
    """加载指定的 YAML 文件"""
    if filename not in YAML_FILES:
        return jsonify({"error": "Invalid file name"}), 400

    file_path = YAML_FILES[filename]
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    data_with_comments = load_yaml(file_path)
    rtd=jsonify(data_with_comments)

    return rtd

@app.route("/api/save/<filename>", methods=["POST"])
def save_file(filename):
    """接收前端数据并保存到 YAML 文件"""
    if filename not in YAML_FILES:
        return jsonify({"error": "Invalid file name"}), 400

    file_path = YAML_FILES[filename]
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404


    data = request.json  # 获取前端发送的 JSON 数据
    if not data:
        return jsonify({"error": "No data provided"}), 400

    result = save_yaml(file_path, data)
    if result is True:
        return jsonify({"message": "File saved successfully"})
    else:
        return jsonify(result), 500

@app.route("/api/sources", methods=["GET"])
def list_sources():
    """列出所有可用的git源"""
    return jsonify(list(REPO_SOURCES))

@app.route("/api/files", methods=["GET"])
def list_files():
    """列出所有可用的 YAML 文件"""
    return jsonify({"files": list(YAML_FILES.keys())})

@app.route("/api/pull", methods=["POST"])
def pull_eridanus():
    """从仓库拉取eridanus(未完成)"""

    return jsonify({"message": "success"})
@app.route("/api/clone", methods=["POST"])
def clone_source():
    data = request.get_json()
    source_url = data.get("source")

    if not source_url:
        return jsonify({"error": "Missing source URL"}), 400
    if os.path.exists("Eridanus"):
        return jsonify({"error": "Eridanus already exists。请删除现有Eridanus后再尝试克隆"}), 400

    print(f"开始克隆: {source_url}")
    os.system(f"{git_path} clone --depth 1 {source_url}")

    return jsonify({"message": f"开始部署 {source_url}"})
@app.route("/")  # 定义根路由
def index():
    if not has_eridanus():
        return render_template("setup.html")  # 返回 setup.html
    else:
        return render_template("dashboard.html") # 返回 dashboard.html

@app.route("/yaml", methods=["GET"])
def yaml_editor():
    return render_template("yaml-editor.html")
import base64

@app.route("/api/file2base64", methods=["POST"])
def file_to_base64():
    """将本地文件转换为 Base64 并返回"""
    data = request.json
    file_path = data.get("path")

    if not file_path:
        return jsonify({"error": "Missing file path"}), 400

    if file_path.startswith("file://"):
        file_path = file_path[7:]  # 去掉 "file://"

    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    try:
        with open(file_path, "rb") as file:
            base64_str = base64.b64encode(file.read()).decode("utf-8")

            file_extension = os.path.splitext(file_path)[1].lower()
            if file_extension in ['.jpg', '.jpeg']:
                mime_type = 'image/jpeg'
            elif file_extension == '.png':
                mime_type = 'image/png'
            elif file_extension == '.gif':
                mime_type = 'image/gif'
            elif file_extension == '.mp3':
                mime_type = 'audio/mpeg'
            elif file_extension == '.wav':
                mime_type = 'audio/wav'
            elif file_extension == '.flac':
                mime_type = 'audio/flac'
            elif file_extension == '.mp4':
                mime_type = 'video/mp4'
            elif file_extension == '.webm':
                mime_type = 'video/webm'
            else:
                return jsonify({"error": "Unsupported file type"}), 400

            return jsonify({"base64": f"data:{mime_type};base64,{base64_str}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
clients = set()

async def handle_connection(websocket):
    print("WebSocket 客户端已连接")
    clients.add(websocket)

    try:
        # 发送连接成功消息
        #await websocket.send(json.dumps({'time': 1739849686, 'self_id': 3377428814, 'post_type': 'meta_event', 'meta_event_type': 'lifecycle', 'sub_type': 'connect'}))

        while True:
            # 接收来自前端的消息
            message = await websocket.recv()
            print(f"收到前端消息: {message} {type(message)}")
            message = json.loads(message)
            if "echo" in message:
                for client in clients:
                    await client.send(json.dumps({'status': 'ok',
                                       'retcode': 0,
                                       'data': {'message_id': 1253451396},
                                       'message': '',
                                       'wording': '',
                                       'echo': message['echo']}))



            if isinstance(message,list):

                message.insert(0,{'type': 'at', 'data': {'qq': '1000000', 'name': 'Eridanus'}})

            print(message, type(message))

            onebot_event = {
                'self_id': 1000000,
                'user_id': 111111111,
                'time': int(time.time()),
                'message_id': 1253451396,
                'real_id': 1253451396,
                'message_seq': 1253451396,
                'message_type': 'group',
                'sender':
                    {'user_id': 111111111, 'nickname': '主人', 'card': '', 'role': 'member', 'title': ''},
                'raw_message': "",
                'font': 14,
                'sub_type': 'normal',
                'message': message,
                'message_format': 'array',
                'post_type': 'message',
                'group_id': 879886836}

            event_json = json.dumps(onebot_event, ensure_ascii=False)

            # 发送给所有连接的客户端（后端）
            for client in clients:
                if client != websocket:  # 避免回传给前端
                    await client.send(event_json)


            print(f"已发送 OneBot v11 事件: {event_json}")
    except websockets.exceptions.ConnectionClosed as e:
        print(f"客户端连接关闭: {e}")
    finally:
        print("WebSocket 客户端断开连接")
        clients.remove(websocket)

# 启动 WebSocket 服务器
async def start_server():
    server = await websockets.serve(
        handle_connection,
        "0.0.0.0",
        5008,
        max_size=None  # 取消大小限制
    )

    print("WebSocket 服务端已启动，在 5008 端口监听...")
    await server.wait_closed()
def run_websocket_server():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_server())
    loop.run_forever()

#启动Eridanus并捕获输出，反馈到前端。
#不会写，不写！
if __name__ == "__main__":

    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        server_thread = threading.Thread(target=run_websocket_server, daemon=True)
        server_thread.start()
        print("WebSocket 服务器已在后台运行")
    print("启动 Eridanus 主程序")
    print("浏览器访问 http://localhost:5007")
    print("浏览器访问 http://localhost:5007")
    print("浏览器访问 http://localhost:5007")
    app.run(debug=True, host="0.0.0.0", port=5007)