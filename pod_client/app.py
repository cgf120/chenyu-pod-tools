import json
import os.path
import subprocess
import threading
import tkinter as tk
import zipfile
from tkinter.filedialog import askdirectory, askopenfilename
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap import Style
from const.app_config import get_app_type, Plugin, PythonPackage, Model, PodConfig
from utils.util import get_git_repo_info, parse_python_packages, calculate_sha256, get_os, civitai_query_model, \
    query_cache_path, open_file_or_directory, add_models


class App:
    def __init__(self, master):

        self.choice_app_btn = None
        self.choice_python_btn = None
        self.detail_btn = None

        self.log_text = None
        self.style = Style()
        self.master = master
        self.master.title("晨羽POD提取工具")
        self.master.geometry("1200x600")  # 设置初始窗口大小

        # 应用信息
        self.app_dir = ttk.StringVar()
        self.app_type = ttk.StringVar()
        self.model_dir = ttk.StringVar()
        self.plugin_dir = ttk.StringVar()
        self.python = ttk.StringVar()
        self.python_version = ttk.StringVar()
        # 模型
        self.models = {}
        self.plugins = []
        self.packages = []

        self.create_steps()
        self.create_tabs()

    def create_steps(self):
        # 选择应用目录
        button_frame = ttk.Frame(self.master)
        button_frame.pack(pady=10)

        self.choice_app_btn = ttk.Button(button_frame, text="选择应用目录", style="info.TButton",
                                         command=self.load_app_info)
        self.choice_app_btn.grid(row=0, column=0)

        arrow1 = ttk.Label(button_frame, text="→")
        arrow1.grid(row=0, column=1)

        self.choice_python_btn = ttk.Button(button_frame, text="选择python目录", style="info.TButton",
                                            command=self.load_python_info)
        self.choice_python_btn.grid(row=0, column=2)

        arrow2 = ttk.Label(button_frame, text="→")
        arrow2.grid(row=0, column=3)

        self.detail_btn = ttk.Button(button_frame, text="开始处理", style="secondary.TButton", command=self.process)
        self.detail_btn.grid(row=0, column=4)

    def create_tabs(self):
        # 第二行布局
        main_frame = ttk.Frame(self.master)
        main_frame.pack(expand=True, fill=BOTH)
        # 右侧区域
        right_frame = ttk.Frame(main_frame, relief=SUNKEN, borderwidth=1)
        right_frame.pack(fill=Y, expand=False, padx=5, pady=5)

        self.log_text = tk.Text(right_frame, wrap="word", height=30)
        self.log_text.pack(fill=BOTH, expand=True)

    # 加载app信息
    def load_app_info(self):
        app_dir = askdirectory(title="选择应用目录")
        if app_dir is None or app_dir == "":
            self.log_text.insert("1.0", "【警告】未选择应用目录\n")
            return
        self.log_text.insert("1.0", f"【提示】选择应用目录：{app_dir}\n")
        self.app_dir.set(app_dir)
        app_config = get_app_type(app_dir)
        if app_config is None:
            self.log_text.insert("1.0", "【警告】未找到应用类型\n")
            return
        self.log_text.insert("1.0", f"【提示】应用类型：{app_config.name}\n")
        self.app_type.set(app_config.name)
        self.model_dir.set(os.path.join(app_dir, app_config.model_dir))
        self.log_text.insert("1.0", f"【提示】模型目录：{self.model_dir.get()}\n")
        self.plugin_dir.set(os.path.join(app_dir, app_config.plugin_dir))
        self.log_text.insert("1.0", f"【提示】插件目录：{self.plugin_dir.get()}\n")
        self.change_btn_state()

    def load_python_info(self):
        # 打开目录选择对话框
        filename = askopenfilename()
        if filename == '':
            return
        """执行python --version 获取python版本"""
        python_version = subprocess.run([filename, '--version'], stdout=subprocess.PIPE, text=True).stdout.strip()
        if python_version is None:
            self.log_text.insert("1.0", "【提示】Python版本获取失败 \n")
            return
        self.log_text.insert("1.0", f"【提示】Python版本：{python_version}\n")
        self.python.set(filename)
        self.python_version.set(python_version)
        self.change_btn_state()

    def process(self):
        self.choice_app_btn.config(state="disabled")
        self.choice_python_btn.config(state="disabled")
        self.detail_btn.config(state="disabled")
        self.log_text.insert("1.0", "【提示】开始处理,可能耗时很久，请耐心等待～\n")
        threading.Thread(target=self.calc_data).start()

    def calc_data(self):
        self.load_plugins()
        self.load_packages()
        self.load_models()
        self.pack_files()
        self.log_text.insert("1.0", "【提示】处理完成\n")
        self.choice_app_btn.config(state="normal")
        self.choice_python_btn.config(state="normal")
        self.detail_btn.config(state="normal")

    def load_plugins(self):
        self.log_text.insert("1.0", f"【提示】开始处理插件\n")
        items = os.listdir(self.plugin_dir.get())
        repo_dirs = [d for d in items if os.path.isdir(os.path.join(self.plugin_dir.get(), d))]
        self.log_text.insert("1.0", f"【提示】插件目录：{self.plugin_dir.get()},共需要处理插件{len(repo_dirs)}个\n")
        for index, repo_dir in enumerate(repo_dirs):
            repo_path = os.path.join(self.plugin_dir.get(), repo_dir)
            self.log_text.insert("1.0", f"【提示】处理插件[{index + 1}/{len(repo_dirs)}]：{repo_path}\n")
            name, remote_url, commit_log = get_git_repo_info(repo_path)
            plugin = Plugin(name=name, remote_url=remote_url, commit_log=commit_log)
            self.plugins.append(plugin)
            self.log_text.insert("1.0", f"【提示】插件信息[{index + 1}/{len(repo_dirs)}]：{plugin}\n")
        self.log_text.insert("1.0", f"【提示】插件处理完成\n")

    def load_packages(self):
        if get_os() == "Windows":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        else:
            startupinfo = None

        self.log_text.insert("1.0", f"【提示】Python版本：{self.python_version.get()},python执行程序:{self.python}\n")
        result = subprocess.check_output([self.python.get(), "-m", "pip", "freeze"], text=True,
                                         startupinfo=startupinfo).strip()
        packages = result.strip().split("\n")
        self.log_text.insert("1.0", f"【提示】Python包数量：{len(packages)}\n")
        for index, line in enumerate(packages):
            self.log_text.insert("1.0", f"【提示】Python包[{index + 1}/{len(packages)}]：{line}\n")
            name, version, remote_url, package_type, err = parse_python_packages(line)
            if err is not None:
                self.log_text.insert("1.0", f"【警告】Python包解析失败：{err},忽略\n")
                continue
            package = PythonPackage(name=name, version=version, remote_url=remote_url, type=package_type,full_text=line)
            self.log_text.insert("1.0",
                                 f"【提示】Python包信息[{index + 1}/{len(packages)}]：{package}\n")
            self.packages.append(package)
        self.log_text.insert("1.0", f"【提示】Python包处理完成\n")




    def load_models(self):
        self.log_text.insert("1.0", f"【提示】开始处理模型\n")
        file_list = []
        for root_dir, dirs, files in os.walk(self.model_dir.get()):
            for file in files:

                file_list.append(os.path.join(root_dir, file))
        self.log_text.insert("1.0", f"【提示】模型目录：{self.model_dir.get()},共需要处理模型{len(file_list)}个\n")
        for index, model_path in enumerate(file_list):
            model_name = os.path.basename(model_path)
            self.log_text.insert("1.0", f"【提示】处理模型[{index + 1}/{len(file_list)}]：{model_path}\n")
            sha256 = calculate_sha256(model_path)
            model_id, download_url = civitai_query_model(sha256)
            cache_path = query_cache_path(sha256)
            if cache_path is None and download_url is not None:
                # 云端不存在，C站存在，添加到云端
                add_models(sha256)
            model_relpath = os.path.relpath(model_path, self.model_dir.get())
            if sha256 not in self.models:
                self.models[sha256] = Model(model_name=model_name, model_id=model_id, sha256=sha256, cache_path=cache_path, file_path = [model_relpath], download_url= download_url)
            else:
                self.log_text.insert("1.0", f"【警告】重复模型：{model_name}，只记录路径，后续做映射\n")
                self.models[sha256].file_path.append(model_relpath)
            self.log_text.insert("1.0", f"【提示】模型信息[{index + 1}/{len(file_list)}]：{self.models.get(sha256)}\n")
        self.log_text.insert("1.0", f"【提示】模型处理完成\n")

    def pack_files(self):
        self.log_text.insert("1.0",
                             f"【提示】开始打包,只打包配置文件和模型\n 模型包括只打包C站不存在并且云端也不存在的模型，会放到poddata下\n")

        out_dir = os.path.join(self.app_dir.get(),"pod")

        if not os.path.exists(out_dir):
            os.mkdir(out_dir)

        pod_zip_file = os.path.join(out_dir, "pod.zip")
        self.log_text.insert("1.0", f"【提示】打包后压缩文件位置:{pod_zip_file}\n")
        pod_config_file = os.path.join(out_dir, "pod_config.json")
        self.log_text.insert("1.0", f"【提示】配置文件位置:{pod_config_file}\n")

        with zipfile.ZipFile(pod_zip_file, "w") as z:
            self.log_text.insert("1.0", f"【提示】开始打包配置文件\n")
            with open(pod_config_file, "w") as f:
                pod_config = PodConfig(app_dir=self.app_dir.get(), app_type=self.app_type.get(), model_dir=self.model_dir.get(),
                                       plugin_dir=self.plugin_dir.get(), python=self.python.get(),python_version=self.python_version.get(), models = [model for model in self.models.values()], plugins= self.plugins, packages= self.packages)
                json.dump(pod_config.model_dump(), f, indent=4)  # indent=4 使输出格式化便于阅读

            z.write(pod_config_file, "pod_config.json")
            self.log_text.insert("1.0", f"【提示】配置文件打包完成\n")
            self.log_text.insert("1.0", f"【提示】开始打包模型，路径存储基于模型路径的相对路径\n")

            for model in self.models.values():
                if model.cache_path is not None:
                    self.log_text.insert("1.0", f"【提示】模型{model.model_name}云端已存在，忽略打包\n")
                elif model.download_url is not None:
                    self.log_text.insert("1.0", f"【警告】模型{model.model_name}C站已存在，忽略打包\n")
                else:
                    file_path = os.path.join(self.model_dir.get(), model.file_path[0])
                    # 获取file_path 相对于model_dir的相对路径
                    relative_path = os.path.relpath(file_path, self.model_dir.get())
                    z.write(file_path, f"models/{relative_path}")
                    self.log_text.insert("1.0", f"【提示】模型{model.model_name}打包完成\n")
        self.log_text.insert("1.0", f"【提示】打包完成\n")
        open_file_or_directory(out_dir)

    def change_btn_state(self):
        ready = True
        if self.check_app_info():
            self.choice_app_btn.config(style="success.TButton")
        else:
            ready = False
        if self.check_python_info():
            self.choice_python_btn.config(style="success.TButton")
        else:
            ready = False
        if ready:
            self.detail_btn.config(style="primary.TButton")

    def check_app_info(self):
        if self.app_dir.get() is None or self.app_dir.get() == "":
            return False
        if self.app_type.get() is None or self.app_type.get() == "":
            return False
        if self.model_dir.get() is None or self.model_dir.get() == "":
            return False
        return True

    def check_python_info(self):
        if self.python.get() is None or self.python.get() == "":
            return False
        if self.python_version.get() is None or self.python_version.get() == "":
            return False
        return True
