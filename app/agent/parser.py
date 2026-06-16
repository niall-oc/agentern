import re

def extract_code_blocks(text: str) -> list[str]:
    # Regex to capture markdown code blocks
    pattern = r"```[a-z]*\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)
    return matches if matches else [text]
