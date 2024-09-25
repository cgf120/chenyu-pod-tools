import huggingface_hub
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from huggingface_hub import whoami, login
from huggingface_hub.errors import RepositoryNotFoundError

from const.app_config import HUGGINGFACE_TOKEN
from pod_model_manager.app.config import SQLALCHEMY_DATABASE_URI

# 初始化数据库
db = SQLAlchemy()

def check_login_and_login():
    try:
        # 尝试检查是否已登录
        user_info = whoami()
        print(f"Already logged in as: {user_info['name']}")
    except RepositoryNotFoundError:
        # 如果没有登录，执行登录操作
        login(token=HUGGINGFACE_TOKEN)
        print("Login successful.")

def create_app():
    app = Flask(__name__)

    app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


    # 初始化数据库
    db.init_app(app)

    # 导入路由
    from .routes import api_bp
    app.register_blueprint(api_bp)

    # 启动定时任务
    from .scheduler import start_scheduler
    start_scheduler(app)

    check_login_and_login()

    return app