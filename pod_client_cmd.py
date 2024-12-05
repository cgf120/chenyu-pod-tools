import argparse
import os.path
import subprocess
import json
import time
import zipfile
import datetime

from const.app_config import PodConfig, Model, Plugin, PythonPackage
from utils.util import calculate_sha256, civitai_query_model, query_cache_path, add_models, get_git_repo_info, \
    parse_python_packages



pod_config = PodConfig(
    app_dir="",
    app_type="",
    model_dir="",
    plugin_dir="",
    python="",
    python_version="",
    models=list(),
    plugins=list(),
    packages=list(),
)

def reset_timestamp_if_needed(file_path):
    """
    Resets the file's timestamp to a date after 1980 if it's older.
    """
    stat = os.stat(file_path)
    if stat.st_mtime <= time.mktime(datetime.datetime(2000, 1, 1).timetuple()):
        os.utime(file_path, (time.time(), time.time()))  # Update to current time



def load_python_info(python_executable):
    """执行python --version 获取python版本"""
    python_version = subprocess.run([python_executable, '--version'], stdout=subprocess.PIPE, text=True).stdout.strip()
    return python_version

# 加载模型
def load_models():
    file_list = []
    for root_dir, dirs, files in os.walk(pod_config.model_dir):
        for file in files:
            file_list.append(os.path.join(root_dir, file))
    print( f"共需要处理模型{len(file_list)}个")
    models = {}
    for index, model_path in enumerate(file_list):
        model_name = os.path.basename(model_path)
        print(f"【提示】处理模型[{index + 1}/{len(file_list)}]：{model_path}")
        sha256 = calculate_sha256(model_path)
        model_id, download_url = civitai_query_model(sha256)
        cache_path = query_cache_path(sha256)
        if cache_path is None and download_url is not None:
            # 云端不存在，C站存在，添加到云端
            add_models(sha256)
        model_relpath = os.path.relpath(model_path, pod_config.model_dir)

        if sha256 not in models:
            models[sha256] = Model(model_name=model_name, model_id=model_id, sha256=sha256, cache_path=cache_path, file_path = [model_relpath], download_url= download_url)
        else:
            print(f"【警告】重复模型：{model_name}，只记录路径，后续做映射\n")
            models[sha256].file_path.append(model_relpath)
        print(f"【提示】模型信息[{index + 1}/{len(file_list)}]：{models.get(sha256)}\n")
    pod_config.models = list(models.values())

def load_plugins():
    items = os.listdir(pod_config.plugin_dir)
    repo_dirs = [d for d in items if os.path.isdir(os.path.join(pod_config.plugin_dir, d))]
    print(f"【提示】插件目录：{pod_config.plugin_dir},共需要处理插件{len(repo_dirs)}个")
    for index, repo_dir in enumerate(repo_dirs):
        repo_path = os.path.join(pod_config.plugin_dir, repo_dir)
        print( f"【提示】处理插件[{index + 1}/{len(repo_dirs)}]：{repo_path}")
        try:
            name, remote_url, commit_log = get_git_repo_info(repo_path)
            plugin = Plugin(name=name, remote_url=remote_url, commit_log=commit_log)
        except:
            pass
        pod_config.plugins.append(plugin)
        print(f"【提示】插件信息[{index + 1}/{len(repo_dirs)}]：{plugin}")

def load_python_packages():
    result = subprocess.check_output([pod_config.python, "-m", "pip", "freeze"], text=True).strip()
    packages = result.strip().split("\n")
    print(f"【提示】Python包数量：{len(packages)}\n")
    for index, line in enumerate(packages):
        print( f"【提示】Python包[{index + 1}/{len(packages)}]：{line}\n")
        name, version, remote_url, package_type, err = parse_python_packages(line)
        if err is not None:
            print(f"【警告】Python包解析失败：{err},忽略\n")
            continue
        package = PythonPackage(name=name, version=version, remote_url=remote_url, type=package_type,full_text=line)
        print(f"【提示】Python包信息[{index + 1}/{len(packages)}]：{package}\n")
        pod_config.packages.append(package)

def package_zip():
    pod_config_file = os.path.join(pod_config.app_dir, "pod_config.json")
    with open(pod_config_file, "w") as f:
        json.dump(pod_config.model_dump(), f, indent=4)  #

    pod_zip_file = os.path.join(pod_config.app_dir, "pod_config.zip")
    with zipfile.ZipFile(pod_zip_file, "w") as z:
        z.write(pod_config_file, "pod_config.json")
        for model in pod_config.models:
            if model.cache_path is not None:
                print(f"【提示】模型{model.model_name}云端已存在，忽略打包\n")
            elif model.download_url is not None:
                print(f"【警告】模型{model.model_name}C站已存在，忽略打包\n")
            else:
                file_path = os.path.join(pod_config.model_dir, model.file_path[0])
                # 获取file_path 相对于model_dir的相对路径
                relative_path = os.path.relpath(file_path, pod_config.model_dir)
                reset_timestamp_if_needed(file_path)
                z.write(file_path, f"models/{relative_path}")
                print(f"【提示】模型{model.model_name}打包完成\n")


def init(app_dir, python):
    if not os.path.exists(app_dir):
        raise Exception(f"应用目录不存在:{app_dir}")
    pod_config.app_dir = app_dir
    print(f"应用目录:{pod_config.app_dir}")

    # 模型目录
    model_dir = os.path.join(app_dir, "models")
    if not os.path.exists(model_dir):
        raise Exception(f"模型目录不存在:{model_dir}")
    pod_config.model_dir = model_dir
    print(f"模型目录:{pod_config.model_dir}")

    # 插件目录
    plugins_dir = os.path.join(app_dir, "custom_nodes")
    if not os.path.exists(plugins_dir):
        raise Exception(f"插件目录不存在:{plugins_dir}")
    pod_config.plugin_dir = plugins_dir
    print(f"插件目录:{pod_config.plugin_dir}")

    # python环境目录
    if not python:
        python = "python"
    python_version = load_python_info(python)
    if python_version is None:
        raise Exception(f"获取python版本失败:{python}")
    pod_config.python = python
    print(f"python环境:{pod_config.python}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='仙宫云ComfyUI数据采集。')
    # 添加命令行参数
    parser.add_argument('--app_dir', help='应用目录。',required=True)
    parser.add_argument('--python', help='python执行程序，比如 /usr/bin/python，默认 python。')
    parser.add_argument('--pod_config', help='根据配置文件读取。')
    args = parser.parse_args()
    # 应用目录
    app_dir = args.app_dir
    python = args.python
    config = args.pod_config
    if config is None:
        # 初始化
        print("初始化...")
        init(app_dir, python)
        print("初始化完成")

        print("加载模型...")
        load_models()
        print("加载模型完成")

        print("加载插件...")
        load_plugins()
        print("加载插件完成")

        print("加载python包...")
        load_python_packages()
        print("加载python包完成")
    else:
        with open(config, "r") as f:
            data= json.load(f)
            pod_config = PodConfig(**data)
            print(pod_config.app_dir)
    # 打包
    print("打包...")
    print()
    package_zip()
    print("打包完成")









