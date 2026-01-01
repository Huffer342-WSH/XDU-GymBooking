import yaml
import os


def load_config():
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base_dir, "config", "config.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    except Exception as e:
        print(f"[!] 配置文件加载失败: {e}")
        return None
