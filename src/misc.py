import re

def string_normalizer(string: str) -> str:
    string = string.replace("\\", "\\\\")
    string = string.replace("\n", "\\n")
    string = string.replace("\r", "\\r")
    string = string.replace("\b", "\\b")
    string = string.replace("'", "'\"'\"'")
    return string

def re_normalizer(string: str) -> bytes:
    string = ''.join('\r\n' if char in {'\r', '\n'} else char for char in string)
    return re.escape(string.encode())
