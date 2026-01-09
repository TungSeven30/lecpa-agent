"""SSN and PII redaction utilities."""

import re


# SSN patterns to detect
SSN_PATTERNS = [
    # Standard format: 123-45-6789
    re.compile(r"\b(\d{3})-(\d{2})-(\d{4})\b"),
    # No dashes: 123456789
    re.compile(r"\b(\d{3})(\d{2})(\d{4})\b"),
    # Spaces: 123 45 6789
    re.compile(r"\b(\d{3})\s(\d{2})\s(\d{4})\b"),
]


def mask_ssn(ssn: str) -> str:
    """Mask an SSN, showing only the last 4 digits.

    Args:
        ssn: Social Security Number in any format

    Returns:
        Masked SSN showing only last 4 digits (e.g., "XXX-XX-1234")
    """
    # Remove all non-digit characters
    digits = re.sub(r"\D", "", ssn)

    if len(digits) != 9:
        # Not a valid SSN length, return as-is with generic mask
        return "XXX-XX-XXXX"

    last4 = digits[-4:]
    return f"XXX-XX-{last4}"


def extract_ssn_last4(ssn: str) -> str | None:
    """Extract the last 4 digits of an SSN.

    Args:
        ssn: Social Security Number in any format

    Returns:
        Last 4 digits or None if invalid
    """
    digits = re.sub(r"\D", "", ssn)

    if len(digits) != 9:
        return None

    return digits[-4:]


def redact_ssn_in_text(text: str, replacement: str = "XXX-XX-{last4}") -> str:
    """Redact all SSNs found in text, preserving last 4 digits.

    Args:
        text: Text that may contain SSNs
        replacement: Replacement pattern. Use {last4} for last 4 digits.

    Returns:
        Text with SSNs redacted
    """
    result = text

    for pattern in SSN_PATTERNS:
        matches = list(pattern.finditer(result))
        # Process matches in reverse to preserve positions
        for match in reversed(matches):
            full_match = match.group(0)
            digits = re.sub(r"\D", "", full_match)

            if len(digits) == 9:
                last4 = digits[-4:]
                redacted = replacement.format(last4=last4)
                result = result[: match.start()] + redacted + result[match.end() :]

    return result


def contains_ssn(text: str) -> bool:
    """Check if text contains what looks like an SSN.

    Args:
        text: Text to check

    Returns:
        True if SSN-like pattern found
    """
    for pattern in SSN_PATTERNS:
        match = pattern.search(text)
        if match:
            digits = re.sub(r"\D", "", match.group(0))
            if len(digits) == 9:
                return True
    return False


def redact_ein_in_text(text: str, replacement: str = "XX-XXX{last4}") -> str:
    """Redact EINs (Employer Identification Numbers) in text.

    Args:
        text: Text that may contain EINs
        replacement: Replacement pattern. Use {last4} for last 4 digits.

    Returns:
        Text with EINs redacted
    """
    # EIN format: 12-3456789
    ein_pattern = re.compile(r"\b(\d{2})-(\d{7})\b")

    result = text
    matches = list(ein_pattern.finditer(result))

    for match in reversed(matches):
        full_match = match.group(0)
        digits = re.sub(r"\D", "", full_match)
        last4 = digits[-4:]
        redacted = replacement.format(last4=last4)
        result = result[: match.start()] + redacted + result[match.end() :]

    return result
