import json
import logging
import os.path
import zipfile

from const.app_config import PodConfig, get_app_type_by_identity_key, CIVIAI_API_KEY
from utils.util import clone_and_checkout, download_file, path_cover, query_cache_path

logging.basicConfig(filename='pod-cloud.log',
                    level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def load_pod_from_json(file_path: str) -> PodConfig:
    with open(file_path, 'r') as file:
        json_data = json.load(file)  # 读取 JSON 文件
    return PodConfig(**json_data)  # 使用 Pydantic 将字典转换为对象
base_dir = "/poddata"

if __name__ == "__main__":
    """读取当前pod压缩文件并解压到/poddata"""
    print("解压pod.zip开始")
    with zipfile.ZipFile(os.path.join(base_dir,"pod.zip"), 'r') as zip_ref:
        zip_ref.extractall(base_dir)
    print("解压pod.zip结束")
    """判断配置文件并解析为PODConfig对象"""
    pod_config = load_pod_from_json(os.path.join(base_dir,"pod_config.json"))

    print(f'类型: {pod_config.app_type}')
    app_config_val = get_app_type_by_identity_key(pod_config.app_type)
    cloud_app_dir = app_config_val.cloud_app_dir

    # 处理插件
    plugins_dir = os.path.join(cloud_app_dir,app_config_val.plugin_dir)
    print(f'插件目录:{plugins_dir}')
    for plugin in pod_config.plugins:
        print(f'插件:{plugin.name}')
        clone_and_checkout(plugin.remote_url,plugin.commit_log,plugins_dir)
    # 处理模型,缓存不存在，C站存在就下载，缓存存在就用缓存做软连接，其他的就用客户上传的模型做软连接
    print(f'模型预处理,模型目录:{os.path.join(cloud_app_dir,app_config_val.model_dir)}')
    for model in pod_config.models:
        # 模型默认路径是客户上传的模型
        model_file = os.path.join(base_dir,path_cover(model.file_path[0],pod_config.app_dir))
        # C站缓存在客户端处理的时候已经添加到模型管理了，在这里只需要查询下缓存文件路径即可
        if model.cache_path is None and model.download_url is not None:
            model.cache_path = query_cache_path(model.sha256)
        # 如果缓存存在就使用缓存文件
        if model.cache_path is not None:
            os.symlink(model.cache_path,model_file)
            model_file = model.cache_path
        #处理软连接
        if len(model.file_path) > 1:
            print(f'缓存模型:{model.cache_path}')
            for i in range(1,len(model.file_path)):
                target_model_file = os.path.join(base_dir,path_cover(model.file_path[i],pod_config.app_dir))
                print(f'重复模型,软连接:{model_file}->{target_model_file}')
                os.symlink(model_file,target_model_file)
    # print(f'模型预处理完成')
    print(f'模型映射:把/poddata下的模型及软连接，再次软连接到应用目录下')
    for root_dir, dirs, files in os.walk(os.path.join(base_dir,app_config_val.model_dir)):
        for file in files:
            if os.path.isdir(file):
                print(f'创建目录:{os.path.join(cloud_app_dir,app_config_val.model_dir,file)}')
                os.mkdir(os.path.join(cloud_app_dir,app_config_val.model_dir,root_dir,file))
            else:
                print(os.path.join(root_dir, file))
                source_file = os.path.join(root_dir,file)
                target_file = os.path.join(cloud_app_dir,os.path.relpath(source_file,base_dir))
                dest_dir = os.path.dirname(target_file)
                if not os.path.exists(dest_dir):
                    os.makedirs(dest_dir, exist_ok=True)
                print(f'软连接:{source_file}->{target_file}')
                os.symlink(source_file,target_file)