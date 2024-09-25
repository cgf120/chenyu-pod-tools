import os

# 数据库配置
SQLALCHEMY_DATABASE_URI = 'sqlite:///../pod.db'
SQLALCHEMY_TRACK_MODIFICATIONS = False
MODEL_BASE_DIR = "/root/aigc-models/pod-models"



# 其他配置可以在这里添加，例如：
# SECRET_KEY = os.getenv('SECRET_KEY', 'supersecretkey')