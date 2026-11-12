"""Pick the installed card whose name or type is closest to a prompt.

A filename hit or a character-name hit outranks hair color. Color and height
only break ties, or choose a card when the prompt names neither a person nor
a type. Nothing here writes a file.
"""

from __future__ import annotations

from typing import Any

from illusionforge.library.index import tokens
from illusionforge.spec.compile import _COLORS, compile_prompt

# Search words only. gyaru and gal are the same request because the Koikatsu
# stock file is Gyaru and a Honey Select 2 card in this library is named Gal.
_ALIASES = {
    "gyaru": "gal",
    "gal": "gyaru",
    "ojousama": "ojou",
    "ojou": "ojousama",
}

_FACE_ADJECTIVES = {
    "wide", "round", "chubby", "narrow", "slim", "small", "big", "large",
    "huge", "thin", "full", "long",
}
_FACE_NOUNS = {"face", "eyes", "eye", "nose", "lips", "ears", "ear"}

_STOP = {
    "koikatsu", "koikatu", "honey", "select", "hs2", "honeyselect2",
    "female", "woman", "male", "man",
    "with", "and", "the", "a", "an", "her", "his", "from", "into", "who",
    "named", "called", "name",
    "hair", "eyes", "eye", "skin",
    "is", "are", "has", "have", "very",
}

# Dropped from the name search only after the compiler accepted them as height.
_HEIGHT_WORDS = {"short", "tall", "average", "height"}
_HEIGHT_PHRASE = _HEIGHT_WORDS | {"very"}

_STOCK_PARENTS = {"female", "male"}
_NAMED = ("filename", "card name", "name tokens", "personality")
_LabelSets = dict[tuple[str, str], list[tuple[str, set[str]]]]


def prompt_tokens(prompt: str) -> list[str]:
    """Words that should hit a card name. Game, sex, and 'black hair' drop out."""
    raw = tokens(prompt)
    kept: list[str] = []
    index = 0
    while index < len(raw):
        word = raw[index]
        nxt = raw[index + 1] if index + 1 < len(raw) else ""
        if word in _COLORS and nxt in {"hair", "eyes", "eye", "skin"}:
            index += 2
            continue
        if word in _FACE_ADJECTIVES and nxt in _FACE_NOUNS:
            index += 2
            continue
        # "honey select 2" must not search for a card named 2.
        if word.isdigit() or word in _STOP:
            index += 1
            continue
        kept.append(word)
        index += 1
    expanded: list[str] = []
    for word in kept:
        expanded.append(word)
        alias = _ALIASES.get(word)
        if alias and alias not in expanded:
            expanded.append(alias)
    return expanded


def _boundary(char: str) -> bool:
    """Same edges as a Unicode word boundary. An empty neighbor is an edge."""
    return not char or not (char.isalnum() or char == "_")


def _whole_phrase(phrase: str, text: str) -> bool:
    """True when phrase is a whole word or phrase in text. Digit-only phrases are not names."""
    if not phrase or phrase.isdigit() or phrase not in text:
        return False
    start = 0
    while True:
        at = text.find(phrase, start)
        if at < 0:
            return False
        before = text[at - 1] if at else ""
        after_at = at + len(phrase)
        after = text[after_at] if after_at < len(text) else ""
        if _boundary(before) and _boundary(after):
            return True
        start = at + 1


def _matched_words(words: list[str], token_set: set[str]) -> list[str]:
    """Exact token, or a longer card token that starts with a word of 5+ letters.

    "school" then finds a card named schoolgirl. Short words stay exact so
    "gal" does not match inside an unrelated name.
    """
    if not words or not token_set:
        return []
    hit: list[str] = []
    for word in words:
        if word in token_set or (
            len(word) >= 5 and any(token.startswith(word) for token in token_set)
        ):
            if word not in hit:
                hit.append(word)
    return hit


def _named_hit(reasons: list[str]) -> bool:
    return any(reason.startswith(_NAMED) for reason in reasons)


def _is_height_phrase(phrase: str) -> bool:
    """True when every word is a height phrase. "short hair" is not."""
    parts = [part for part in phrase.split() if part]
    return bool(parts) and all(part in _HEIGHT_PHRASE for part in parts)


def _parent_name(path: str) -> str:
    normalized = path.replace("/", "\\")
    if "\\" not in normalized:
        return ""
    parent = normalized.rsplit("\\", 1)[0]
    return parent.rsplit("\\", 1)[-1].casefold()


def _is_old_copy(path: str) -> bool:
    return "\\old\\" in path.replace("/", "\\").casefold()


def _prepare_labels(labels: dict[str, Any] | None) -> _LabelSets:
    """Tokenize personality labels once per search, not once per card."""
    prepared: _LabelSets = {}
    if not isinstance(labels, dict):
        return prepared
    for game, mapping in labels.items():
        if not isinstance(mapping, dict):
            continue
        for personality, raw in mapping.items():
            items = raw if isinstance(raw, list) else [raw]
            bucket: list[tuple[str, set[str]]] = []
            for label in items:
                if not label:
                    continue
                text = str(label)
                bucket.append((text, set(tokens(text))))
            if bucket:
                prepared[(str(game), str(personality))] = bucket
    return prepared


def _color_bonus(spec_color: Any, card_color: Any, weight: float) -> float:
    if not isinstance(spec_color, list) or not isinstance(card_color, list):
        return 0.0
    if len(spec_color) < 3 or len(card_color) < 3:
        return 0.0
    distance = sum(abs(float(spec_color[i]) - float(card_color[i])) for i in range(3))
    return max(0.0, weight - distance * (weight * 0.7))


def _hit(card: dict[str, Any], score: float, reasons: list[str]) -> dict[str, Any]:
    return {
        "path": card.get("path"),
        "score": round(score, 2),
        "reasons": reasons,
        "fullname": card.get("fullname") or "",
        "sex": card.get("sex"),
        "personality": card.get("personality"),
        "game": card.get("game"),
        "mtime": int(card.get("mtime") or 0),
    }


def score_card(
    card: dict[str, Any],
    words: list[str],
    prompt_cf: str,
    spec: dict[str, Any],
    label_sets: _LabelSets,
) -> tuple[float, list[str]]:
    """Score one cached card. Higher is closer to the prompt."""
    reasons: list[str] = []
    identity = 0.0
    height_set = (spec.get("body_sliders") or {}).get("height") is not None
    stem = str(card.get("stem") or "")
    stem_is_height = height_set and _is_height_phrase(stem)
    if stem and not stem_is_height and _whole_phrase(stem, prompt_cf):
        identity += 120
        reasons.append("filename")
    else:
        hit = _matched_words(words, set(card.get("file_tokens") or []))
        if hit:
            identity += 40 * len(hit)
            reasons.append("filename tokens " + " ".join(hit))
    full = str(card.get("fullname") or "").casefold()
    if full and not (height_set and _is_height_phrase(full)) and _whole_phrase(full, prompt_cf):
        identity += 90 + 60 * max(0, len(full.split()) - 1)
        reasons.append("card name")
    else:
        hit = _matched_words(words, set(card.get("name_tokens") or []))
        if hit:
            identity += 35 * len(hit)
            reasons.append("name tokens " + " ".join(hit))
    if words:
        for label, label_tokens in label_sets.get((str(card.get("game")), str(card.get("personality"))), ()):
            if _matched_words(words, label_tokens):
                identity += 20
                reasons.append("personality " + label)
                break
    # A name that is not in the library must not fall through to a color neighbor.
    if words and identity <= 0:
        return 0.0, []
    score = identity
    hair_bonus = _color_bonus(spec.get("hair_color"), card.get("hair"), 18)
    eye_bonus = _color_bonus(spec.get("eye_color"), card.get("eye"), 12)
    skin_bonus = _color_bonus(spec.get("skin_color"), card.get("skin"), 12)
    if hair_bonus:
        score += hair_bonus
        reasons.append("hair color")
    if eye_bonus:
        score += eye_bonus
        reasons.append("eye color")
    if skin_bonus:
        score += skin_bonus
        reasons.append("skin color")
    height = (spec.get("body_sliders") or {}).get("height")
    if height is not None and card.get("game") == "kk" and card.get("height") is not None:
        bonus = max(0.0, 10 - abs(float(height) - float(card["height"])) * 10)
        if bonus:
            score += bonus
            reasons.append("height")
    path = str(card.get("path") or "")
    # Stock matters only when the prompt named nobody. Otherwise every vanilla
    # file would outrank a community card that actually matched the name.
    if not words and _parent_name(path) in _STOCK_PARENTS:
        score += 6
        reasons.append("stock card")
    if _is_old_copy(path):
        score -= 25
        reasons.append("older copy")
    return score, reasons


def rank(
    prompt: str,
    cards: list[dict[str, Any]],
    labels: dict[str, Any] | None = None,
    game: str | None = None,
    limit: int = 8,
) -> dict[str, Any]:
    """Return the closest cards. confident is true only for a name or type hit."""
    spec = compile_prompt(prompt, game)
    label_sets = _prepare_labels(labels)
    words = prompt_tokens(prompt)
    if (spec.get("body_sliders") or {}).get("height") is not None:
        words = [word for word in words if word not in _HEIGHT_WORDS]
    prompt_cf = " ".join(prompt.casefold().split())
    pool = [card for card in cards if card.get("game") == spec["game"]]
    if spec.get("sex") is not None:
        pool = [card for card in pool if card.get("sex") == spec["sex"]]
    scored: list[dict[str, Any]] = []
    for card in pool:
        value, reasons = score_card(card, words, prompt_cf, spec, label_sets)
        if value <= 0:
            continue
        scored.append(_hit(card, value, reasons))
    # "koikatsu male" names nobody. Hand back a few cards of that sex.
    # "koikatsu male xyzzy" named someone who is not installed: return nothing.
    if not scored and not words and spec.get("sex") is not None:
        ordered = sorted(pool, key=lambda card: (-int(card.get("mtime") or 0), str(card.get("path"))))
        for card in ordered[: max(1, limit)]:
            scored.append(_hit(card, 0.0, ["sex filter only"]))
    scored.sort(key=lambda item: (-float(item["score"]), -int(item.get("mtime") or 0), str(item["path"])))
    cap = max(1, limit)
    hits = scored[:cap]
    confident = bool(hits) and _named_hit(hits[0]["reasons"])
    return {
        "game": spec["game"],
        "sex": spec.get("sex"),
        "query": words,
        "searched": len(pool),
        "confident": confident,
        "hits": hits,
        "spec": spec,
    }
