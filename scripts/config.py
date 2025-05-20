import os
import yaml

def load_config(config_path="./config.yaml"):
    # config_path="config.yaml" when run inside docker
    # config_path="./config.yaml" when run outside docker
    # Load config from environment variables
    configs = dict(os.environ)
    # Load config from yaml file
    with open(config_path, "r") as f:
        yaml_configs = yaml.safe_load(f)
    # Merge configs, environment variables have higher priority
    configs.update(yaml_configs)
    return configs 

# For Docker Use the below function
# def load_config(config_path="config.yaml"):
#     """
#     Loads configuration from a YAML file and allows overrides from environment variables.
#     Environment variables for specific keys (like API keys and MODEL) will take precedence.
#     """
#     if not os.path.isabs(config_path):
#         base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#         config_path = os.path.join(base_dir, config_path)

#     try:
#         with open(config_path, "r") as f:
#             configs = yaml.safe_load(f)
#             if configs is None:
#                 configs = {}
#     except FileNotFoundError:
#         print(f"Warning: Configuration file {config_path} not found. Relying solely on environment variables or defaults.")
#         configs = {}
#     except yaml.YAMLError as e:
#         print(f"Error parsing YAML file {config_path}: {e}")
#         configs = {}

#     # --- Environment Variable Overrides ---

#     # Override MODEL
#     model_env = os.getenv('MODEL')
#     if model_env:
#         configs['MODEL'] = model_env.strip() # .strip() to remove any leading/trailing whitespace

#     # Override API keys
#     openai_api_key_env = os.getenv('OPENAI_API_KEY')
#     if openai_api_key_env:
#         configs['OPENAI_API_KEY'] = openai_api_key_env.strip()

#     gemini_api_key_env = os.getenv('GEMINI_API_KEY')
#     if gemini_api_key_env:
#         configs['GEMINI_API_KEY'] = gemini_api_key_env.strip()

#     # Validate that critical keys are present after loading based on the selected MODEL
#     current_model = configs.get('MODEL', '').lower() # Get the effective model name

#     if not current_model:
#         print("Warning: MODEL is not set in config.yaml or via environment variable.")
#         # Depending on your app's logic, you might want to raise an error or have a default
#         # raise ValueError("MODEL is not set. Please specify a model.")

#     if current_model == 'openai':
#         if not configs.get('OPENAI_API_KEY') or "YOUR_OPENAI_API_KEY" in configs.get('OPENAI_API_KEY', ''):
#             print("Warning: MODEL is 'OpenAI' but OPENAI_API_KEY is not set or is a placeholder.")
#             # raise ValueError("OPENAI_API_KEY is required for MODEL 'OpenAI' but not found/set.")
#     elif current_model == 'gemini':
#         if not configs.get('GEMINI_API_KEY') or "YOUR_GEMINI_API_KEY" in configs.get('GEMINI_API_KEY', ''):
#             print("Warning: MODEL is 'Gemini' but GEMINI_API_KEY is not set or is a placeholder.")
#             # raise ValueError("GEMINI_API_KEY is required for MODEL 'Gemini' but not found/set.")
#     # Add more model checks as needed

#     return configs