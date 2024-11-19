import PyInstaller.__main__
import os
import shutil

# 清理之前的构建文件
if os.path.exists("build"):
    shutil.rmtree("build")
if os.path.exists("dist"):
    shutil.rmtree("dist")

# 确保输出目录存在
if not os.path.exists("dist"):
    os.makedirs("dist")

# 打包命令行版本
PyInstaller.__main__.run([
    'pod_client_cmd.py',
    '--name=pod_client_cmd',
    '--onefile',
    '--console',
    '--clean',  # 清理临时文件
])

# 打包GUI版本
PyInstaller.__main__.run([
    'pod_client.py',
    '--name=pod_client_gui',
    '--onefile',
    '--noconsole',  # GUI版本不显示控制台
    '--windowed',
    '--clean',  # 清理临时文件
])