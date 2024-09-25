import os
from enum import Enum

from typing import Optional

from pydantic import BaseModel

CIVIAI_API_KEY="fb5e87bce2c0d69ab913e4828cd643e6"
HUGGINGFACE_TOKEN="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"
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
POD_MANAGER_URL = "192.168.200.8:5001"


class AppType:
    def __init__(self, name,identity_key,model_dir,plugin_dir,cloud_app_dir):
        self.name = name
        self.identity_key = identity_key
        self.model_dir = model_dir
        self.plugin_dir = plugin_dir
        self.cloud_app_dir = cloud_app_dir



class AppTypeEnum(Enum):
    ComfyUI = AppType("ComfyUI","custom_nodes","models","custom_nodes","/root/ComfyUI")
    Forge = AppType("Forge","modules_forge","models","extensions","/root/stable-diffusion-webui-forge")
    StableDiffusion = AppType("StableDiffusion","extensions","models","extensions","/root/stable-diffusion-webui")

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

class Model(BaseModel):
    model_name: str
    model_id: Optional[int]
    sha256: str
    cache_path: Optional[str]
    file_path: list[str]
    download_url: Optional[str]

class Plugin(BaseModel):
    name: str
    remote_url: str
    commit_log: str
class PythonPackage(BaseModel):
    name: Optional[str]
    version: Optional[str]
    remote_url: Optional[str]
    type : Optional[str]
    full_text: Optional[str]

class PodConfig(BaseModel):
    app_dir: str
    app_type: str
    model_dir: str
    plugin_dir: str
    python: str
    python_version: str
    models: list[Model]
    plugins: list[Plugin]
    packages: list[PythonPackage]

