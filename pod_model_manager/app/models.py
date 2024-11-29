from fsspec.registry import default

from . import db

"""
模型目录结构
chenyudata
----models
--------civiai
------------{model_id}/{model_name}
--------huggingface
------------{repo}
----------------{path}/{model_name}
--------other
------------{sha256}
----------------{model_name}
"""

class Model(db.Model):
    name = db.Column(db.String(256), nullable=False)              # 模型名称 huggingface: repoid  civiai: sha256  other: modelname
    model_type = db.Column(db.String(32), nullable=False)         # -1: 其他 0: C站模型 1: Huggingface模型
    sha256 = db.Column(db.String(128), primary_key=True)          # 模型SHA256
    cache_path = db.Column(db.String(256), nullable=True)         # 缓存路径
    download_url = db.Column(db.String(1024), nullable=True)      # 下载URL
    status = db.Column(db.String(32), nullable=True,default=0)    # 模型状态 0: 未下载 1: 已下载 2: 下载中
    size = db.Column(db.Integer, nullable=True)                   # 模型大小
    true_file_name = db.Column(db.String(256), nullable=True)     # 真实文件名

    def __repr__(self):
        return f'<Model {self.name}>'

    def to_dict(self):
        return {
            'sha256': self.sha256,
            'name': self.name,
            'model_type': self.model_type,
            'cache_path': self.cache_path,
            'download_url': self.download_url,
            'status': self.status
        }
