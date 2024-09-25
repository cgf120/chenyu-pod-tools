import os

import json


def init_data(app):
    directory_path = "./json"
    # 遍历目录下的所有文件
    for filename in os.listdir(directory_path):
        # 检查文件是否为 JSON 文件
        if filename.endswith('.json'):
            file_path = os.path.join(directory_path, filename)
            try:
                # 打开并读取 JSON 文件
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for cache_path,sha256 in data.items():
                        print(cache_path,sha256)
            except json.JSONDecodeError as e:
                print(f"文件 {filename} 不是有效的 JSON: {e}")
            except Exception as e:
                print(f"读取文件 {filename} 时发生错误: {e}")


if __name__ == '__main__':
    init_data(None)