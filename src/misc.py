import string
import re

def string_normalizer(string: str) -> str:
    string = (string
        .replace("\\", "\\\\")
        .replace("\a", "\\a")
        .replace("\b", "\\b")
        .replace("\f", "\\f")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
        .replace("\v", "\\v")
        .replace("'", "'\"'\"'")
    )
    return string

def re_normalizer(string: str) -> bytes:
    string = ''.join('\r\n' if char in {'\r', '\n'} else char for char in string)
    return re.escape(string.encode())

ALPHABET = string.digits + string.ascii_lowercase
def base36encode(number: int):
    sign = '-' if number < 0 else ''
    number = abs(number)
    base36 = ""
    while number:
        number, remainder = divmod(number, 36)
        base36 = ALPHABET[remainder] + base36
    return sign + (base36 or "0")
