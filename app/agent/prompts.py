import yaml
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YAML_PATH = os.path.join(BASE_DIR, "prompts.yaml")

with open(YAML_PATH, "r", encoding="utf-8") as file:
    _PROMPTS = yaml.safe_load(file)

def get_prompt(key: str) -> str:
    """
    Retrieves a prompt from the YAML dictionary configuration.
    Example: get_prompt("PLANNER_PROMPT")
    """
    try:
        return _PROMPTS[key]
    except KeyError:
        raise ValueError(f"Prompt key '{key}' not found in prompts.yaml")