# config_loader.py
import yaml  # YAMLファイルを読み込むためのライブラリ

def load_config(config_path):
    """
    指定されたYAML設定ファイルを読み込み、辞書として返します。
    
    引数:
        config_path: 設定ファイルのパス
    戻り値:
        設定内容の辞書
    """
    with open(config_path, 'r', encoding='utf-8') as file:
        config = yaml.safe_load(file)
    return config 