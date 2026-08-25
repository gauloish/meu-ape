import re
import unicodedata


def normalize_text(text: str) -> str:
    """Normalize text removing ponctuation, traces, expanding
    contractions and removing duplicated blank spaces.

    Args:
        text (str): Text to be normalized.

    Returns:
        str: Normalized text.
    """
    if not text:
        return ""
    
    # 1. Remove acentos (Goiânia -> Goiania)
    text = unicodedata.normalize("NFKD", text).encode("ASCII", "ignore").decode("utf-8")
    
    # 2. Minúsculas e remoção de hifens (T-9 -> t 9)
    text = text.lower().replace("-", " ")

    text = text.replace("da", "")
    text = text.replace("do", "")
    text = text.replace("de", "")
    text = text.replace("das", "")
    text = text.replace("dos", "")
    
    # 3. Padronização de prefixos comuns
    text = re.sub(r"\br\.\s*", "rua ", text)
    text = re.sub(r"\bav\.\s*", "avenida ", text)
    text = re.sub(r"\bpq\.\s*", "parque ", text)
    text = re.sub(r"\bqd\.\s*", "quadra ", text)
    
    # 4. Remove espaços duplos
    text = re.sub(r"\s+", " ", text).strip()

    return text

def check_normalized_substring(string: str, other: str) -> bool:
    """Check if `other` string is substring of `string`, with
    normalized values.

    Args:
        string (str): Original string.
        other (str): Other string.

    Returns:
        bool: True if `other` is substring of `string`,
        with normalized values.
    """
    if normalize_text(other) in normalize_text(string):
        return True

    return False