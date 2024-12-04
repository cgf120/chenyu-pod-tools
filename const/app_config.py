import os
from enum import Enum

from typing import Optional

from pydantic import BaseModel

CIVIAI_API_KEY=""
HUGGINGFACE_TOKEN=""
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
POD_MANAGER_URL = "https://models.chenyu.cn"

class AppType:
    def __init__(self, 
                 name, 
                 identity_key, 
                 model_dir, 
                 plugin_dir, 
                 cloud_app_dir):
        """
        :param name: 应用名称
        :param identity_key: 应用标识
        :param model_dir: 模型目录
        :param plugin_dir: 插件目录
        :param cloud_app_dir: 云端应用目录
        """
        self.name = name
        self.identity_key = identity_key
        self.model_dir = model_dir
        self.plugin_dir = plugin_dir
        self.cloud_app_dir = cloud_app_dir

class AppTypeEnum(Enum):
    ComfyUI = AppType(name = "ComfyUI",
                      identity_key = "custom_nodes",
                      model_dir = "models",
                      plugin_dir = "custom_nodes",
                      cloud_app_dir = "/root/ComfyUI")

    Forge = AppType(name = "Forge",
                    identity_key = "modules_forge",
                    model_dir = "models",
                    plugin_dir = "extensions",
                    cloud_app_dir = "/root/stable-diffusion-webui-forge")

    StableDiffusion = AppType(name = "StableDiffusion",
                              identity_key = "extensions",
                              model_dir = "models",
                              plugin_dir = "extensions",
                              cloud_app_dir = "/root/stable-diffusion-webui")

def get_app_type(app_dir):
    for app_type in AppTypeEnum:
        if app_type.value.identity_key in os.listdir(app_dir):
            return app_type.value
    return None

def get_app_type_by_identity_key(name):
    for app_type in AppTypeEnum:
        if app_type.value.name == name:
            return app_type.value
    return None

class Model(BaseModel):                 # 模型
    model_name: str                     # 模型名称
    model_id: Optional[int]             # 模型ID
    sha256: str                         # 模型SHA256
    cache_path: Optional[str]           # 缓存路径
    file_path: list[str]                # 文件路径
    download_url: Optional[str]         # 下载URL
    class Config:
        protected_namespaces = ()       # 保护命名空间

class Plugin(BaseModel):                # 插件
    name: str                           # 插件名称
    remote_url: str                     # 远程URL
    commit_log: str                     # 提交日志

class PythonPackage(BaseModel):         # Python包
    name: Optional[str]                 # 名称
    version: Optional[str]              # 版本
    remote_url: Optional[str]           # 远程URL
    type : Optional[str]                # 类型
    full_text: Optional[str]            # 完整文本

class PodConfig(BaseModel):             # Pod配置
    app_dir: str                        # 应用目录
    app_type: str                       # 应用类型
    model_dir: str                      # 模型目录
    plugin_dir: str                     # 插件目录
    python: str                         # Python路径
    python_version: str                 # Python版本
    models: list[Model]                 # 模型
    plugins: list[Plugin]               # 插件
    packages: list[PythonPackage]       # Python包
    class Config:
        protected_namespaces = ()       # 保护命名空间

