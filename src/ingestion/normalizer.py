"""
Text normalization and cleaning utility for extracted document content.
"""
import re
import unicodedata
from typing import Optional


class ContentNormalizer:
    """Normalizes raw extracted text to ensure consistent formatting, clean whitespace, and remove encoding artifacts."""
    
    # Non-printable characters (excluding newlines and tabs)
    _NON_PRINTABLE_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]")
    # Excessive consecutive whitespaces
    _MULTI_WHITESPACE_RE = re.compile(r"[ \t]+")
    # Excessive consecutive newlines (3 or more -> 2)
    _MULTI_NEWLINE_RE = re.compile(r"\n{3,}")
    # Hyphenated line breaks (e.g. "contin-\nuation" -> "continuation")
    _HYPHEN_LINEBREAK_RE = re.compile(r"(\w+)-\n(\w+)")
    # Unicode zero-width chars and invisible marks
    _ZERO_WIDTH_RE = re.compile(r"[\u200B\u200C\u200D\uFEFF\u00A0]")

    @classmethod
    def normalize(cls, text: Optional[str]) -> str:
        """
        Applies a multi-step cleaning pipeline to input text:
        1. Handle null / empty inputs
        2. Unicode normalization (NFKC)
        3. Replace zero-width / non-breaking spaces
        4. Remove non-printable control characters
        5. Rejoin hyphenated line wraps
        6. Collapse multiple spaces and excessive empty lines
        7. Strip leading/trailing whitespace
        """
        if not text:
            return ""

        # Step 1: Unicode NFKC normalization (standardizes accents, ligatures, special symbols)
        normalized = unicodedata.normalize("NFKC", text)

        # Step 2: Replace non-breaking & zero-width spaces with regular space
        normalized = cls._ZERO_WIDTH_RE.sub(" ", normalized)

        # Step 3: Strip non-printable ASCII control characters
        normalized = cls._NON_PRINTABLE_RE.sub("", normalized)

        # Step 4: Rejoin words split across linebreaks with hyphens
        normalized = cls._HYPHEN_LINEBREAK_RE.sub(r"\1\2", normalized)

        # Step 5: Normalize line endings to standard Unix newline '\n'
        normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")

        # Step 6: Clean line-by-line whitespace
        lines = [cls._MULTI_WHITESPACE_RE.sub(" ", line).strip() for line in normalized.split("\n")]
        normalized = "\n".join(lines)

        # Step 7: Collapse 3+ consecutive newlines to maximum 2 newlines (preserve paragraphs)
        normalized = cls._MULTI_NEWLINE_RE.sub("\n\n", normalized)

        return normalized.strip()

    @classmethod
    def clean_table_text(cls, text: str) -> str:
        """Specific helper to clean structured CSV or table cell text."""
        cleaned = cls.normalize(text)
        return cleaned.replace("\n", " ")
