import re


_AI_HUB_FILLER_WHITELIST = [
    "\uc544",
    "\uc5b4",
    "\uc74c",
    "\uadf8",
    "\ubb50",
    "\uc800",
    "\ub9c9",
    "\uc880",
]
_AI_HUB_FILLER_PATTERN = re.compile(
    r"(?<!\S)(?:[a-z]|" + "|".join(_AI_HUB_FILLER_WHITELIST) + r")/"
)
_DUAL_TOKEN_PATTERN = re.compile(r"(\d[\w-]*)/([^()\s]+)")
_CONSECUTIVE_DUAL_PATTERN = re.compile(
    r"(?:(?:\d[\w-]*)/[^()\s]+\s*){2,}"
)


def merge_consecutive_dual_notation(text: str) -> str:
    def merge_group(match: re.Match[str]) -> str:
        numbers = _DUAL_TOKEN_PATTERN.findall(match.group(0))
        return "".join(number for number, _ in numbers)

    return _CONSECUTIVE_DUAL_PATTERN.sub(merge_group, text)


def normalize_dual_notation(text: str) -> str:
    return _DUAL_TOKEN_PATTERN.sub(r"\1", text)


def merge_spaced_digits(text: str) -> str:
    return re.sub(r"(?:\d\s){4,}\d", lambda match: match.group(0).replace(" ", ""), text)


def remove_correction_marker(text: str) -> str:
    return text.replace("+", " ")


def remove_noise_markup(text: str) -> str:
    return re.sub(r"\([^)]*\)", " ", text)


def remove_aihub_filler_markup(text: str) -> str:
    return _AI_HUB_FILLER_PATTERN.sub(" ", text)


def remove_masking_marker(text: str) -> str:
    return re.sub(r"\uc3d0-?", " ", text)


def strip_speaker_label(text: str) -> str:
    return re.sub(r"(?:\ud53c\ud574\uc790|\uc0ac\uae30\ubc94)\s*:\s*", " ", text)


def clean_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_finance_text(text: str) -> str:
    text = merge_consecutive_dual_notation(text)
    text = normalize_dual_notation(text)
    text = merge_spaced_digits(text)
    text = remove_correction_marker(text)
    text = remove_noise_markup(text)
    text = remove_aihub_filler_markup(text)
    text = remove_masking_marker(text)
    text = strip_speaker_label(text)
    return clean_whitespace(text)
