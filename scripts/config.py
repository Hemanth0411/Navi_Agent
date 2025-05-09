import os
import yaml

def load_config(config_path="./config.yaml"):
    # Load config from environment variables
    configs = dict(os.environ)
    # Load config from yaml file
    with open(config_path, "r") as f:
        yaml_configs = yaml.safe_load(f)
    # Merge configs, environment variables have higher priority
    configs.update(yaml_configs)
    return configs 