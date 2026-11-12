"""Turn a short English prompt into a character spec.

This is a fixed phrase table, not a model. Every number is a starting slider
position. It does not mean the finished character looks like the sentence.
Clothing words stay unmapped until a live catalog supplies a slot and an id.
"""

from __future__ import annotations

import re
from typing import Any

from illusionforge.spec.sliders import face_name_index


# Channels are 0-1. These are prompt colors, not samples taken from a card.
_COLORS: dict[str, list[float]] = {
    "black": [0.05, 0.05, 0.05, 1.0],
    "brown": [0.28, 0.14, 0.08, 1.0],
    "blonde": [0.86, 0.72, 0.35, 1.0],
    "blond": [0.86, 0.72, 0.35, 1.0],
    "red": [0.55, 0.08, 0.08, 1.0],
    "blue": [0.10, 0.20, 0.70, 1.0],
    "green": [0.10, 0.45, 0.20, 1.0],
    "pink": [0.85, 0.35, 0.55, 1.0],
    "white": [0.90, 0.90, 0.90, 1.0],
    "purple": [0.40, 0.15, 0.55, 1.0],
    "grey": [0.50, 0.50, 0.50, 1.0],
    "gray": [0.50, 0.50, 0.50, 1.0],
    "silver": [0.75, 0.75, 0.80, 1.0],
    "orange": [0.80, 0.35, 0.08, 1.0],
    "teal": [0.10, 0.50, 0.50, 1.0],
}

_SKIN: tuple[tuple[str, list[float]], ...] = (
    ("pale skin", [0.98, 0.90, 0.86, 1.0]),
    ("fair skin", [0.96, 0.84, 0.78, 1.0]),
    ("tan skin", [0.72, 0.52, 0.38, 1.0]),
    ("dark skin", [0.35, 0.24, 0.18, 1.0]),
)

# Face phrases start at 0.5 and add the delta. Honey Select 2 names only.
_FACE: tuple[tuple[tuple[str, ...], str, float], ...] = (
    (("wide face", "round face", "chubby face"), "face_width", 0.25),
    (("narrow face", "slim face", "small face"), "face_width", -0.25),
    (("big eyes", "large eyes", "huge eyes"), "eye_width_1", 0.20),
    (("small eyes",), "eye_width_1", -0.20),
    (("small nose",), "nose_width", -0.20),
    (("big nose", "large nose"), "nose_width", 0.20),
    (("big lips", "full lips", "large lips"), "lip_width", 0.20),
    (("small lips", "thin lips"), "lip_width", -0.20),
    (("long ears",), "ear_length", 0.20),
)

_CLOTHES = (
    "school uniform",
    "uniform",
    "dress",
    "swimsuit",
    "naked",
    "nude",
    "lingerie",
    "shirt",
    "skirt",
    "pants",
    "socks",
    "shoes",
)

_HEIGHT = (
    ("very short", 0.15),
    ("average height", 0.50),
    ("tall", 0.85),
    ("short", 0.25),
)

# The word after a height phrase. "short hair" is not a height.
_NOT_HEIGHT = {
    "hair", "hairs", "bangs", "fringe", "bob", "cut",
    "skirt", "dress", "sleeve", "sleeves", "nails", "nail",
    "socks", "pants", "shorts", "boots", "heels", "stockings",
    "top", "jacket", "coat", "gloves", "shirt",
}


def detect_game(prompt: str, explicit: str | None = None) -> str:
    """Use --game when it is present. Otherwise read the prompt. Do not guess."""
    if explicit:
        game = explicit.strip().lower()
        if game not in ("kk", "hs2", "koikatsu", "honeyselect2"):
            raise ValueError("game must be kk or hs2")
        return "kk" if game in ("kk", "koikatsu") else "hs2"
    text = prompt.lower()
    hs2 = bool(re.search(r"\b(hs2|honey\s*select\s*2|honeyselect2)\b", text))
    kk = bool(re.search(r"\b(koikatsu|koikatu)\b", text))
    if hs2 and kk:
        raise ValueError("the prompt names both games; pass --game kk or --game hs2")
    if hs2:
        return "hs2"
    if kk:
        return "kk"
    raise ValueError("pass --game kk or --game hs2; the prompt did not name a game")


def _has(text: str, phrase: str) -> bool:
    return re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text) is not None


def _next_word(text: str, end: int) -> str:
    rest = text[end:].lstrip()
    token = rest.split(" ", 1)[0] if rest else ""
    return token.strip(".,;:!?\"'-")


def _is_height(text: str, phrase: str) -> bool:
    """True when any copy of the phrase is not naming hair or clothing.

    The first match is not enough: "short hair who is short" is still short.
    """
    pattern = r"(?<!\w)" + re.escape(phrase) + r"(?!\w)"
    for match in re.finditer(pattern, text):
        if _next_word(text, match.end()) not in _NOT_HEIGHT:
            return True
    return False


def _named(text: str) -> str | None:
    match = re.search(r'(?:\bnamed\b|\bcalled\b|\bname\b)\s+"([^"]+)"', text, flags=re.IGNORECASE)
    if not match:
        match = re.search(r"(?:\bnamed\b|\bcalled\b)\s+([A-Za-z][A-Za-z' \-]{0,48})", text, flags=re.IGNORECASE)
    if not match:
        return None
    return " ".join(match.group(1).split())


def _split_name(full: str) -> dict[str, str]:
    parts = full.split(" ")
    if len(parts) >= 2:
        return {
            "firstname": " ".join(parts[:-1]),
            "lastname": parts[-1],
            "nickname": "",
            "fullname": full,
        }
    return {"firstname": full, "lastname": "", "nickname": "", "fullname": full}


def compile_prompt(prompt: str, game: str | None = None) -> dict[str, Any]:
    """Build a spec. Unmapped phrases are listed instead of being invented as ids."""
    chosen = detect_game(prompt, game)
    text = " ".join(prompt.lower().split())
    face: dict[str, float] = {}
    unmapped: list[dict[str, str]] = []
    notes = [
        "Slider numbers are a deterministic starting point from a phrase table.",
        "They are not a claim that the character looks like the prompt.",
        "sex 1 and sex 0 are the only sex bytes in the indexed character cards.",
    ]

    deltas: dict[str, float] = {}
    for phrases, slider, delta in _FACE:
        if any(_has(text, phrase) for phrase in phrases):
            if chosen != "hs2":
                unmapped.append({
                    "text": phrases[0],
                    "reason": "that face phrase uses the Honey Select 2 name map, which is not verified on Koikatsu",
                })
                continue
            deltas[slider] = deltas.get(slider, 0.0) + delta
    if chosen == "hs2":
        names = face_name_index()
        for slider, delta in deltas.items():
            if slider not in names:
                unmapped.append({"text": slider, "reason": "slider name is not in the Honey Select 2 table"})
                continue
            face[slider] = max(0.0, min(1.0, 0.5 + delta))

    body: dict[str, float] = {}
    for phrase, value in _HEIGHT:
        if _is_height(text, phrase):
            if chosen == "kk":
                body["height"] = value
            else:
                unmapped.append({
                    "text": phrase,
                    "reason": "body height is shapeValueBody index 0 on Koikatsu only",
                })
            break

    hair = None
    eyes = None
    for name, color in _COLORS.items():
        if hair is None and (_has(text, f"{name} hair") or _has(text, f"hair is {name}")):
            hair = list(color)
        if eyes is None and (_has(text, f"{name} eyes") or _has(text, f"eyes are {name}")):
            eyes = list(color)

    skin = None
    for phrase, color in _SKIN:
        if _has(text, phrase):
            skin = list(color)
            break

    name = {"firstname": "", "lastname": "", "nickname": "", "fullname": ""}
    found = _named(prompt)
    if found:
        name = _split_name(found)

    sex = None
    if _has(text, "female") or _has(text, "woman"):
        sex = 1
    elif _has(text, "male") or _has(text, "man"):
        sex = 0
    if _has(text, "girl") or _has(text, "boy") or _has(text, "loli") or _has(text, "child"):
        unmapped.append({
            "text": "age-ambiguous word",
            "reason": "sex was not inferred from girl, boy, loli, or child",
        })

    covered: list[tuple[int, int]] = []
    for phrase in sorted(_CLOTHES, key=len, reverse=True):
        # One entry per phrase. A later "uniform" still counts after "school uniform".
        found = False
        for match in re.finditer(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text):
            span = match.span()
            if any(span[0] >= start and span[1] <= end for start, end in covered):
                continue
            covered.append(span)
            found = True
        if found:
            unmapped.append({
                "text": phrase,
                "reason": "no installed catalog; clothing ids are not guessed",
            })

    return {
        "game": chosen,
        "face_sliders": face,
        "body_sliders": body,
        "hair_color": hair,
        "eye_color": eyes,
        "skin_color": skin,
        "name": name,
        "sex": sex,
        "clothes": [],
        "unmapped": unmapped,
        "notes": notes,
    }
