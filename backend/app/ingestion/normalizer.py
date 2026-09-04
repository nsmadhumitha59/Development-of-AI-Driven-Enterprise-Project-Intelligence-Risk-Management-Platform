import re

def normalize_text(raw_text: str) -> str:
    """
    Normalizes extracted document text for high-quality RAG chunking and vector indexing.
    - Strips unprintable control characters.
    - Normalizes non-breaking spaces and unicode whitespace.
    - Converts CRLF to LF.
    - Trims line-level trailing/leading spaces.
    - Collapses 3+ consecutive newlines to maximum 2 newlines.
    """
    if not raw_text:
        return ""

    # Replace carriage returns & carriage return + line feeds
    text = raw_text.replace("\r\n", "\n").replace("\r", "\n")

    # Replace non-breaking spaces & tabs with standard space
    text = text.replace("\xa0", " ").replace("\t", " ")

    # Strip unprintable control characters (except newline \n)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)

    # Trim spaces at beginning and end of each line
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    # Replace multiple spaces with a single space (within a line)
    text = re.sub(r' {2,}', ' ', text)

    # Collapse 3 or more consecutive newlines into 2
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()
