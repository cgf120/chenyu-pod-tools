import hashlib
import logging
import os
import platform
import shutil
import subprocess
import sys
import time

from huggingface_hub import HfApi
import requests
import re
import urllib.request
from urllib.parse import urlparse, parse_qs, unquote

from const.app_config import HUGGINGFACE_TOKEN, USER_AGENT, CIVIAI_API_KEY, POD_MANAGER_URL

logging.basicConfig(filename='app.log',
                    level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

"""查询 civitai 模型"""
def civitai_query_model(sha256):
    url = f"https://civitai.com/api/v1/model-versions/by-hash/{sha256}"
    logging.info(f"请求 civitai 模型: {url}")
    try:
        # 发出 GET 请求
        response = requests.get(url)
        response.raise_for_status()  # 如果响应状态码不是 200，抛出异常

        # 解析 JSON 响应
        data = response.json()

        # 提取 modelId 和 downloadUrl
        model_id = data.get('modelId')
        download_url = data.get('downloadUrl')
        logging.info(f"模型 ID: {model_id}, 下载地址: {download_url}")
        return model_id, download_url
    except requests.exceptions.RequestException as e:
        logging.error(f"请求失败: {e}")
        return None, None

"""判断是否在晨羽缓存数据"""
def query_cache_path(sha256):
    query_url = f"{POD_MANAGER_URL}/models/{sha256}"
    logging.info(f"请求缓存数据: {query_url}")
    try:
        # 发出 GET 请求
        response = requests.get(query_url)
        response.raise_for_status()  # 如果响应状态码不是 200，抛出异常
        # 解析 JSON 响应
        data = response.json()

        # 提取缓存路径
        cache_path = data.get('cache_path')
        logging.info(f"缓存路径: {cache_path}")
        return cache_path
    except requests.exceptions.RequestException as e:
        logging.error(f"请求失败: {e}")
        return None

def add_models(sha256):
    url = f"{POD_MANAGER_URL}/models"
    logging.info(f"添加模型: {url}")
    try:
        # 发出 POST 请求
        response = requests.post(url, json={"name": sha256, "model_type": "0"})
        response.raise_for_status()  # 如果响应状态码不是 200，抛出异常
    except requests.exceptions.RequestException as e:
        logging.error(f"请求失败: {e}")
        raise e

def get_git_repo_info(repo_path):
    """获取 Git 仓库的地址、名称和当前 commit log"""
    logging.info(f"获取 Git 仓库信息: {repo_path}")
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

        logging.info(f"仓库名称: {repo_name}, 地址: {remote_url}, commit log: {commit_log}")

        return repo_name,remote_url,commit_log
    except subprocess.CalledProcessError as e:
        logging.error(f"Error processing repo {repo_path}: {e}")
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
        elif package_str.startswith("file"):
            # 处理本地文件
            return package_str.split(" @ ")[0], None, None, "local", None
        else:
            return None, None, None,"unknown",None
    except Exception as e:
        return None, None, None, None, e


def link_file(src_file, dst_file):
    if not os.path.exists(src_file):
        raise FileNotFoundError(f"文件不存在: {src_file}")
    if not os.path.exists(dst_file):
        dst_dir = os.path.dirname(dst_file)
        os.makedirs(dst_dir, exist_ok=True)
        os.symlink(src_file, dst_file)

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
        logging.info(f"克隆仓库 {repo_url} 到 {clone_path}...")
        subprocess.run(['git', 'clone', repo_url, clone_path], check=True)

        # 2. 进入仓库目录并切换到指定提交
        logging.info(f"克隆仓库成功，切换到提交 {commit_log}...")
        subprocess.run(['git', '-C', clone_path, 'checkout', commit_log], check=True)

        logging.info(f"切换到提交 {commit_log} 成功")

    except subprocess.CalledProcessError as e:
        logging.error(f"错误: {e}")

def get_domain_from_url(url):
    parsed_url = urlparse(url)
    return parsed_url.netloc


class NoRedirection(urllib.request.HTTPErrorProcessor):
    def http_response(self, request, response):
        return response
    https_response = http_response

def download_file(url: str, output_path: str):
    logging.info(f"下载文件: {url} 到 {output_path}")
    path_dir = os.path.dirname(output_path)
    file_name = os.path.basename(output_path)
    os.makedirs(path_dir, exist_ok=True)  # 创建目录（如果不存在的话）
    dest_url = redirect_url(url)
    parsed_url = urlparse(dest_url)
    query_params = parse_qs(parsed_url.query)
    content_disposition = query_params.get('response-content-disposition', [None])[0]
    true_file_name = unquote(content_disposition.split('filename=')[1].strip('"'))
    response = urllib.request.urlopen(dest_url)
    total_size = response.getheader('Content-Length')
    total_size = int(total_size) if total_size is not None else None
    output_file = os.path.join(path_dir, file_name)
    logging.info(f"文件实际下载地址: {dest_url}, 文件名: {true_file_name}, 文件大小: {total_size} 字节")

    with open(output_file, 'wb') as f:
        downloaded = 0
        start_time = time.time()

        while True:
            chunk_start_time = time.time()
            buffer = response.read(1638400)
            chunk_end_time = time.time()
            if not buffer:
                break
            downloaded += len(buffer)
            f.write(buffer)
            chunk_time = chunk_end_time - chunk_start_time

            if chunk_time > 0:
                speed = len(buffer) / chunk_time / (1024 ** 2)  # Speed in MB/s

            if total_size is not None:
                progress = downloaded / total_size
                logging.info(f'\r下载中: {true_file_name} [{progress*100:.2f}%] - {speed:.2f} MB/s')
    end_time = time.time()
    time_taken = end_time - start_time
    hours, remainder = divmod(time_taken, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours > 0:
        time_str = f'{int(hours)}h {int(minutes)}m {int(seconds)}s'
    elif minutes > 0:
        time_str = f'{int(minutes)}m {int(seconds)}s'
    else:
        time_str = f'{int(seconds)}s'

    sys.stdout.write('\n')
    logging.info(f'下载完成. 文件路径: {file_name}')
    logging.info(f'下载耗时 {time_str}')
    return true_file_name,total_size



def redirect_url(url: str):
    if get_domain_from_url(url) != "huggingface.co":
        headers = {
            'Authorization': f'Bearer {CIVIAI_API_KEY}',
            'User-Agent': USER_AGENT,
        }
    else:
        headers = {
            'Authorization': f'Bearer {HUGGINGFACE_TOKEN}',
            'User-Agent': USER_AGENT,
        }
    request = urllib.request.Request(url, headers=headers)
    opener = urllib.request.build_opener(NoRedirection)
    response = opener.open(request)
    return response.getheader('Location')
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



