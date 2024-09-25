"""
功能：
1.根据sha256查询缓存路径
2.添加模型（C站/Huggingface）
3.定时任务下载未缓存模型
"""
from pod_model_manager.app import create_app, db

app = create_app()

if __name__ == "__main__":
    app.run(debug=True,port=5001,host="0.0.0.0")