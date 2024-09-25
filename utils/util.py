import hashlib
import os
import platform
import shutil
import subprocess
import sys
from huggingface_hub import HfApi
import requests
import re

from const.app_config import HUGGINGFACE_TOKEN

"""查询 civitai 模型"""
def civitai_query_model(sha256):
    url = f"https://civitai.com/api/v1/model-versions/by-hash/{sha256}"
    try:
        # 发出 GET 请求
        response = requests.get(url)
        response.raise_for_status()  # 如果响应状态码不是 200，抛出异常

        # 解析 JSON 响应
        data = response.json()

        # 提取 modelId 和 downloadUrl
        model_id = data.get('modelId')
        download_url = data.get('downloadUrl')

        return model_id, download_url

    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return None, None

"""判断是否在晨羽缓存数据"""
def query_cache_path(sha256):
    return None


def get_git_repo_info(repo_path):
    """获取 Git 仓库的地址、名称和当前 commit log"""
    try:
        if get_os() == "Windows":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        else:
            startupinfo = None
        # 进入 Git 仓库目录
        os.chdir(repo_path)

        # 获取 Git 地址
        remote_url = subprocess.check_output(["git", "remote", "get-url", "origin"], text=True,startupinfo=startupinfo).strip()

        # 获取当前 commit log
        commit_log = subprocess.check_output(["git", "log", "-1", "--format=%h"], text=True,startupinfo=startupinfo).strip()

        # 提取仓库名称（假设仓库目录名即为仓库名称）
        repo_name = os.path.basename(repo_path)

        return repo_name,remote_url,commit_log
    except subprocess.CalledProcessError as e:
        print(f"Error processing repo {repo_path}: {e}")
        return None, None, None

def parse_python_packages(package_str:str):
    try:
        if "==" in package_str:
            package, version = package_str.split("==")
            return package, version,None,"normal",None
        elif package_str.find("git+") != -1:
            # 处理 Git 地址
            package_info = re.match(r'([\w\-]+) @ (git\+.*)', package_str)
            if package_info:
                package_name = package_info.group(1)
                git_url = package_info.group(2)
                return package_name, None, git_url,"git",None
        elif package_str.find("http") != -1:
            # 处理 HTTP 地址
            package_info = re.match(r'([\w\-]+) @ (https://.*)', package_str)
            if package_info:
                package_name = package_info.group(1)
                http_url = package_info.group(2)
                return package_name, None, http_url, "remote",None
        elif package_str.find("file") != -1:
            # 处理本地文件
            package_info = re.match(r'([\w\-]+) @ (file.*)', package_str)
            if package_info:
                package_name = package_info.group(1)
                return package_name, None, None, "local", None
        else:
            return None, None, None,"unknown",None
    except Exception as e:
        return None, None, None, None, e




def path_cover(file_path :str,base_dir):
    return file_path[file_path.index(base_dir):].replace("\\","/")


def get_os():
    system_name = platform.system()

    if system_name == "Windows":
        return "Windows"
    elif system_name == "Linux":
        return "Linux"
    elif system_name == "Darwin":
        return "macOS"
    else:
        return "Unknown"

def open_file_or_directory(path):
    if sys.platform == "win32":  # Windows
        os.startfile(path)
    elif sys.platform == "darwin":  # macOS
        subprocess.run(["open", path])
    else:  # Linux 和其他 Unix 系统
        subprocess.run(["xdg-open", path])

"""计算文件的 sha256 哈希值"""
def calculate_sha256(file_path):
    sha256_hash = hashlib.sha256()

    # 以二进制模式读取文件，并逐块更新哈希
    with open(file_path, "rb") as f:
        # 逐块读取文件，以节省内存（特别是对于大文件）
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)

    # 返回十六进制形式的哈希值
    return sha256_hash.hexdigest()

# 克隆仓库并切换到指定提交
def clone_and_checkout(repo_url: str, commit_log: str, output_dir: str):
    # 如果没有提供输出目录，默认为当前目录
    if output_dir is None:
        output_dir = os.getcwd()

    # 拼接仓库的目标路径
    repo_name = os.path.basename(repo_url).replace('.git', '')
    clone_path = os.path.join(output_dir, repo_name)

    # 1. 克隆仓库
    try:
        print(f"Cloning repository {repo_url} into {clone_path}...")
        subprocess.run(['git', 'clone', repo_url, clone_path], check=True)

        # 2. 进入仓库目录并切换到指定提交
        print(f"Checking out commit {commit_log} in {repo_name}...")
        subprocess.run(['git', '-C', clone_path, 'checkout', commit_log], check=True)

        print(f"Successfully checked out to commit {commit_log} in {clone_path}.")

    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")

# 下载文件
def download_file(url: str, output_dir: str = None, api_key: str = None):
    # 如果没有指定输出目录，使用当前目录
    file_name = os.path.basename(output_dir)
    path_dir = os.path.dirname(output_dir)
    os.makedirs(path_dir, exist_ok=True)  # 创建目录（如果不存在的话）

    print(f"从 {url} 下载到 {output_dir}...")
    # 如果提供了 API 密钥，添加到请求头中
    headers = {}
    if api_key:
        headers['Authorization'] = f"Bearer {api_key}"
    try:
        # 发起 GET 请求
        response = requests.get(url, headers=headers, stream=True)
        # 检查请求是否成功
        response.raise_for_status()
        # 写入文件
        with open(os.path.join(path_dir, file_name), 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"文件下载成功 {output_dir}")
    except requests.exceptions.HTTPError as e:
        print(f"HTTP 错误: {e}")
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")

# 删除目录及其内容
def remove_subdirectories(parent_dir: str):
    # 遍历 parent_dir 下的所有项目
    for item in os.listdir(parent_dir):
        item_path = os.path.join(parent_dir, item)
        # 检查是否是目录
        if os.path.isdir(item_path):
            try:
                shutil.rmtree(item_path)  # 删除目录及其内容
                print(f"删除目录: {item_path}")
            except Exception as e:
                print(f"删除目录 {item_path} 时出错: {e}")

# 获取仓库大文件，lfs文件
def huggingface_query_lfs(repo_id: str):
    files = {}
    hf_client = HfApi()
    repo_files = hf_client.list_repo_files(repo_id=repo_id, revision="main")
    for file in repo_files:
        infos = hf_client.get_paths_info(
            repo_id=repo_id,
            repo_type="model",
            revision="main",
            paths=file,
        )
        if len(infos) == 1 and infos[0].lfs is not None:
            sha256 = infos[0].lfs.sha256
            path = infos[0].path
            files[sha256] = path
    return  files

# 获取仓库的基本信息
def huggingface_repo_info(repo_id: str):
    hf_client = HfApi()
    repo_info = hf_client.repo_info(repo_id=repo_id)
    return repo_info



