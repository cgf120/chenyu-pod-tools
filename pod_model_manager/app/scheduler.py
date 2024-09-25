import os.path
import shutil

import huggingface_hub
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

from huggingface_hub import hf_hub_download, repo_info

from const.app_config import CIVIAI_API_KEY, HUGGINGFACE_TOKEN
from utils.util import civitai_query_model, download_file, huggingface_query_lfs, remove_subdirectories
from . import db
from .config import MODEL_BASE_DIR
from .models import Model

huggingface_hub.login(token=HUGGINGFACE_TOKEN)

def scheduled_task(app):
    with app.app_context():
        print(f"开始执行任务： {datetime.now()}")
        need_down_model = Model.query.filter_by(status=0).first()
        if need_down_model:
            print(f"下载模型: {need_down_model.name}")
            need_down_model.status = 2
            db.session.commit()
            output_dir = f"{MODEL_BASE_DIR}/{need_down_model.model_type}"
            os.makedirs(output_dir, exist_ok=True)
            # C站模型处理
            if need_down_model.model_type == "0":
                # 查询模型ID和下载地址
                model_id,download_url = civitai_query_model(need_down_model.name)
                need_down_model.sha256 = need_down_model.name
                need_down_model.download_url = download_url
                # 下载到目录 {basedir}/0/{sha256}
                output_file = os.path.join(output_dir,need_down_model.sha256)
                err = download_file(download_url,output_file,CIVIAI_API_KEY)
                if err is not None:
                    need_down_model.status = 0
                    db.session.commit()
                    return
                need_down_model.cache_path = output_file
            elif need_down_model.model_type == "1":
                # 获取所有需要下载的大文件
                files = huggingface_query_lfs(need_down_model.name)
                mode_repo_info = huggingface_hub.repo_info(need_down_model.name)
                output_dir = f"{output_dir}/{mode_repo_info.sha}"
                need_down_model.cache_path = output_dir
                os.makedirs(output_dir, exist_ok=True)
                for sha256,file_path in files.items():
                    #判断文件是否存在
                    if Model.query.filter_by(sha256=sha256).first() is not None:
                        continue
                    sub_model = Model()
                    sub_model.name = need_down_model.name
                    sub_model.model_type = need_down_model.model_type
                    sub_model.cache_path = os.path.join(output_dir,sha256)
                    sub_model.sha256 = sha256
                    sub_model.status = 2
                    sub_model.download_url = file_path
                    db.session.add(sub_model)
                    db.session.commit()
                    local_file = hf_hub_download(repo_id=sub_model.name, filename=file_path, local_dir=output_dir)
                    shutil.move(local_file,sub_model.cache_path)
                    # 下载完成更新状态
                    sub_model.status = 1
                    db.session.commit()
                # 删除目录
                remove_subdirectories(output_dir)


            # 下载完成后修改状态
            need_down_model.status = 1
            db.session.commit()
            print(f"Model {need_down_model.name} downloaded")
        else:
            print("No model to download")

def start_scheduler(app):
    # 创建调度器并设置线程池执行器，最大并发任务数为 3
    scheduler = BackgroundScheduler(executors={'default': ThreadPoolExecutor(3)})

    # 添加任务，设置最大并发任务实例数为 3
    scheduler.add_job(func=scheduled_task, args=(app,), trigger="interval", seconds=10, max_instances=3)

    # 启动调度器
    scheduler.start()