from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler

# 初始化数据库
db = SQLAlchemy()

def create_app():
    app = Flask(__name__)

    # 从配置文件加载配置
    app.config.from_pyfile('./config.py')

    # 初始化数据库
    db.init_app(app)

    # 导入路由
    from .routes import api_bp
    app.register_blueprint(api_bp)

    # 启动定时任务
    from .scheduler import start_scheduler
    start_scheduler(app)

    return app