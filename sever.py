import json
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from flask_socketio import SocketIO
from ruamel.yaml import YAML, comments
from threading import Thread
import subprocess
import os

app = Flask(__name__,static_url_path='/assets',static_folder='websources/assets',template_folder='websources')
CORS(app)  # 启用跨域支持

#可用的git源
REPO_SOURCES = [
   "https://ghfast.top/https://github.com/avilliai/Eridanus.git",
   "https://mirror.ghproxy.com/https://github.com/avilliai/Eridanus",
   "https://github.moeyy.xyz/https://github.com/avilliai/Eridanus",
   "https://github.com/avilliai/Eridanus.git",
   "https://gh.llkk.cc/https://github.com/avilliai/Eridanus.git",
   "https://gitclone.com/https://github.com/avilliai/Eridanus.git"
]

# 文件路径配置
YAML_FILES = {
    # "test" : "config/test.yaml",
    "basic_config.yaml": "config/basic_config.yaml",
    "api.yaml": "config/api.yaml",
    "settings.yaml": "config/settings.yaml",
    "controller.yaml": "config/controller.yaml"
}

# 初始化 YAML 解析器（支持注释）
yaml = YAML()
yaml.preserve_quotes = True
"""
新旧数据合并
"""

def merge_dicts(old, new):
    for k, v in old.items():
        # 如果值是一个字典，并且键在新的yaml文件中，那么我们就递归地更新键值对
        if isinstance(v, dict) and k in new and isinstance(new[k], dict):
            merge_dicts(v, new[k])
        # 如果值是列表，且新旧值都是列表，则合并并去重
        elif isinstance(v, list) and k in new and isinstance(new[k], list):
            if k == "api_keys":  # 特殊处理 api_keys
                print(f"覆盖列表 key: {k}")
                new[k] = v  # 使用旧的列表覆盖新的列表
            else:
                print(f"合并列表 key: {k}")
                new[k] = list(dict.fromkeys(new[k] + v))  # 保持顺序去重
        # 如果键在新的yaml文件中，但值类型不同，以新值为准
        elif k in new and type(v) != type(new[k]):
            print(f"类型冲突，保留新的值 key: {k}, old value type: {type(v)}, new value type: {type(new[k])}")
            continue  # 跳过对新值的覆盖
        # 如果键在新的yaml文件中且类型一致，则更新值
        elif k in new:
            print(f"更新 key: {k}, old value: {v}, new value: {new[k]}")
            new[k] = v
        # 如果键不在新的yaml中，直接添加
        else:
            print(f"移除键 key: {k}, value: {v}")

def conflict_file_dealer(old_data: dict, file_new='new_aiReply.yaml'):

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
    """
    递归提取 YAML 文件中所有注释，并用嵌套路径表示。

    :param data: ruamel.yaml 解析后的数据
    :param path: 当前路径
    :param comments_dict: 用于存储注释的字典
    :return: 包含所有注释的字典
    """
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

def load_yaml_with_comments(file_path):
    """
    加载 YAML 文件并提取数据和注释。

    :param file_path: YAML 文件路径
    :return: 包含数据和注释的字典
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.load(f)
        # 提取所有注释
        comments = extract_comments(data)
        return {"data": data, "comments": comments}
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

    print(f"保存文件: {file_path}")
    print(f"数据: {data}")
    return conflict_file_dealer(data["data"], file_path)

def has_eridanus():
    """判断是否安装了Eridanus"""
    file_path = YAML_FILES["settings.yaml"]
    #测试不存在的路径
    file_path = "114514"
    if os.path.exists(file_path):
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
    return jsonify(data_with_comments)

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
    return jsonify({"sources": list(REPO_SOURCES)})

@app.route("/api/files", methods=["GET"])
def list_files():
    """列出所有可用的 YAML 文件"""
    return jsonify({"files": list(YAML_FILES.keys())})

@app.route("/api/pull", methods=["POST"])
def pull_eridanus():
    """从仓库拉取eridanus(未完成)"""
    print(request.json)
    return jsonify({"message": "success"})

@app.route("/", methods=["GET"])
def index():
    """显示主页，后面添加登录验证（需要吗）"""
    if has_eridanus():
        return render_template("dashboard.html")
    else:
        return render_template("setup.html")

@app.route("/yaml", methods=["GET"])
def yaml_editor():
    return render_template("yaml-editor.html")

if __name__ == "__main__":
    #load_yaml("config/api.yaml")
    app.run(debug=True, host="0.0.0.0", port=5007)