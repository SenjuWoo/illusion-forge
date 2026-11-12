"""Apply a character spec to a loaded card.

The spec may only touch fields this module can see on that card. A missing
field is reported in ``skipped`` and left unchanged. Nothing here writes a file.
"""

from __future__ import annotations

from typing import Any

from illusionforge.logutil import debug


def clamp01(value: float) -> float:
    number = float(value)
    if number < 0.0:
        return 0.0
    if number > 1.0:
        return 1.0
    return number


def color4(value: Any) -> list[float]:
    """Accept [r,g,b], [r,g,b,a], or {r,g,b,a}. Channels above 1 are 0-255."""
    if isinstance(value, dict):
        channels = [value.get("r", 0), value.get("g", 0), value.get("b", 0), value.get("a", 1)]
    elif isinstance(value, (list, tuple)) and len(value) >= 3:
        channels = list(value[:4])
        if len(channels) == 3:
            channels.append(1.0)
    else:
        raise ValueError("color must be a 3 or 4 channel list or an r,g,b,a object")
    numbers = [float(channel) for channel in channels]
    if any(channel > 1.0 for channel in numbers):
        numbers = [channel / 255.0 for channel in numbers]
    return [clamp01(channel) for channel in numbers]


def _set_slider(seq: list[Any], index: int, value: float) -> None:
    if index < 0 or index >= len(seq):
        raise IndexError(f"slider {index} is outside 0..{len(seq) - 1}")
    seq[index] = clamp01(value)


def _assign_existing(data: dict[str, Any], key: str, value: Any) -> bool:
    if key not in data:
        return False
    current = data[key]
    if isinstance(current, bool):
        data[key] = bool(value)
    elif isinstance(current, int) and not isinstance(current, bool):
        data[key] = int(value)
    elif isinstance(current, float):
        data[key] = float(value)
    else:
        data[key] = value
    return True


def _paint(target: dict[str, Any], keys: tuple[str, ...], color: list[float]) -> list[str]:
    written: list[str] = []
    for key in keys:
        if key in target and isinstance(target[key], list):
            target[key] = list(color)
            written.append(key)
    return written


def _parts(container: dict[str, Any]) -> list[Any]:
    parts = container.get("parts")
    if isinstance(parts, list):
        return parts
    return []


def apply_spec(card: Any, spec: dict[str, Any]) -> dict[str, Any]:
    """Mutate ``card`` from ``spec`` and return applied, skipped, and notes."""
    applied: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    notes: list[str] = []
    game = card.game

    face_sliders = spec.get("face_sliders") or {}
    if face_sliders:
        face = card.peek_face()
        shape = face.get("shapeValueFace") if isinstance(face, dict) else None
        if not isinstance(shape, list):
            skipped.append({"field": "face_sliders", "reason": "this card has no shapeValueFace list"})
        else:
            names = card.face_index_names()
            armed = False
            for key, raw in face_sliders.items():
                try:
                    if isinstance(key, int) or (isinstance(key, str) and key.lstrip("-").isdigit()):
                        index = int(key)
                    elif game == "hs2" and key in names:
                        index = names[key]
                    else:
                        skipped.append({
                            "field": f"face_sliders.{key}",
                            "reason": "Koikatsu face names are not verified; pass a numeric index inside this card's face length"
                            if game == "kk"
                            else "unknown Honey Select 2 face slider name",
                        })
                        continue
                    if index < 0 or index >= len(shape):
                        raise IndexError(f"slider {index} is outside 0..{len(shape) - 1}")
                    if not armed:
                        # Peeking must not rewrite the file. Dirty the block only once a write is real.
                        card.edit_face()
                        armed = True
                    _set_slider(shape, index, float(raw))
                    applied.append({"field": f"face[{index}]", "value": clamp01(float(raw))})
                except (TypeError, ValueError, IndexError) as exc:
                    skipped.append({"field": f"face_sliders.{key}", "reason": str(exc)})

    body_sliders = spec.get("body_sliders") or {}
    if body_sliders:
        body = card.peek_body()
        shape = body.get("shapeValueBody") if isinstance(body, dict) else None
        if not isinstance(shape, list):
            skipped.append({"field": "body_sliders", "reason": "this card has no shapeValueBody list"})
        else:
            armed = False
            for key, raw in body_sliders.items():
                try:
                    # "height" is the only named body slider, and only on Koikatsu.
                    # The numeric key "0" is an index on every game, including Honey Select 2.
                    if key == "height":
                        if game != "kk":
                            skipped.append({
                                "field": f"body_sliders.{key}",
                                "reason": "body height is shapeValueBody[0] on Koikatsu only",
                            })
                            continue
                        index = 0
                    elif isinstance(key, int) or (isinstance(key, str) and key.lstrip("-").isdigit()):
                        index = int(key)
                    else:
                        skipped.append({
                            "field": f"body_sliders.{key}",
                            "reason": "no verified body slider name for that key",
                        })
                        continue
                    if index < 0 or index >= len(shape):
                        raise IndexError(f"slider {index} is outside 0..{len(shape) - 1}")
                    if not armed:
                        card.edit_body()
                        armed = True
                    _set_slider(shape, index, float(raw))
                    applied.append({"field": f"body[{index}]", "value": clamp01(float(raw))})
                except (TypeError, ValueError, IndexError) as exc:
                    skipped.append({"field": f"body_sliders.{key}", "reason": str(exc)})

    hair_color = spec.get("hair_color")
    if hair_color is not None:
        color = color4(hair_color)
        hair = card.peek_hair()
        can_paint = any(
            isinstance(part, dict) and any(key in part and isinstance(part[key], list) for key in ("baseColor", "startColor", "endColor", "topColor", "underColor"))
            for part in _parts(hair)
        )
        if can_paint:
            written = []
            for index, part in enumerate(_parts(card.edit_hair())):
                if isinstance(part, dict):
                    for key in _paint(part, ("baseColor", "startColor", "endColor", "topColor", "underColor"), color):
                        written.append(f"hair.parts[{index}].{key}")
            applied.append({"field": "hair_color", "keys": written, "value": color})
            face = card.peek_face()
            if "eyebrow_color" not in spec and isinstance(face, dict) and isinstance(face.get("eyebrowColor"), list):
                card.edit_face()["eyebrowColor"] = list(color)
                notes.append("eyebrowColor was set from hair_color because the spec did not name an eyebrow color")
                applied.append({"field": "eyebrowColor", "value": color})
        else:
            skipped.append({"field": "hair_color", "reason": "no hair part color field was present"})

    if spec.get("eyebrow_color") is not None:
        color = color4(spec["eyebrow_color"])
        face = card.peek_face()
        if isinstance(face, dict) and isinstance(face.get("eyebrowColor"), list):
            card.edit_face()["eyebrowColor"] = list(color)
            applied.append({"field": "eyebrowColor", "value": color})
        else:
            skipped.append({"field": "eyebrow_color", "reason": "eyebrowColor is not on this card"})

    eye_color = spec.get("eye_color")
    if eye_color is not None:
        color = color4(eye_color)
        face = card.peek_face()
        pupil = face.get("pupil") if isinstance(face, dict) else None
        entries = pupil if isinstance(pupil, list) else ([pupil] if isinstance(pupil, dict) else [])
        if any(isinstance(entry, dict) and isinstance(entry.get("baseColor"), list) for entry in entries):
            written = []
            live = card.edit_face().get("pupil")
            live_entries = live if isinstance(live, list) else ([live] if isinstance(live, dict) else [])
            for index, entry in enumerate(live_entries):
                if isinstance(entry, dict) and isinstance(entry.get("baseColor"), list):
                    entry["baseColor"] = list(color)
                    written.append(f"pupil[{index}].baseColor")
            applied.append({"field": "eye_color", "keys": written, "value": color})
        else:
            skipped.append({"field": "eye_color", "reason": "pupil baseColor was not on this card"})

    skin_color = spec.get("skin_color")
    if skin_color is not None:
        color = color4(skin_color)
        body = card.peek_body()
        if isinstance(body, dict) and any(key in body and isinstance(body[key], list) for key in ("skinMainColor", "skinColor", "skinSubColor")):
            written = _paint(card.edit_body(), ("skinMainColor", "skinColor", "skinSubColor"), color)
            applied.append({"field": "skin_color", "keys": written, "value": color})
        else:
            skipped.append({"field": "skin_color", "reason": "no skin color field was present"})

    names = spec.get("name") or {}
    if isinstance(names, dict) and any(names.values()):
        param = card.peek_parameter()
        for key in ("lastname", "firstname", "nickname", "fullname"):
            if not names.get(key):
                continue
            if key not in param:
                skipped.append({"field": f"name.{key}", "reason": f"{key} is not a field on this card"})
                continue
            _assign_existing(card.edit_parameter(), key, str(names[key]))
            applied.append({"field": f"name.{key}", "value": str(names[key])})

    if spec.get("sex") is not None:
        param = card.peek_parameter()
        if "sex" in param:
            _assign_existing(card.edit_parameter(), "sex", int(spec["sex"]))
            applied.append({"field": "sex", "value": int(spec["sex"])})
            notes.append("sex 0 and sex 1 are the values stored on the indexed character cards")
        else:
            skipped.append({"field": "sex", "reason": "sex is not a field on this card"})

    clothes = spec.get("clothes") or []
    if clothes:
        if game != "kk":
            skipped.append({"field": "clothes", "reason": "Honey Select 2 coordinate blocks are passed through unread"})
        else:
            for item in clothes:
                if not isinstance(item, dict) or "slot" not in item or "id" not in item:
                    skipped.append({"field": "clothes", "reason": "a clothes entry needs an integer slot and id from a catalog dump"})
                    continue
                slot = int(item["slot"])
                cloth_id = int(item["id"])
                try:
                    card.set_kk_clothes_id(slot, cloth_id)
                    applied.append({"field": f"clothes[{slot}].id", "value": cloth_id})
                except (IndexError, KeyError, TypeError, ValueError) as exc:
                    skipped.append({"field": f"clothes[{slot}]", "reason": str(exc)})

    for item in spec.get("unmapped") or []:
        if isinstance(item, dict):
            skipped.append({"field": "prompt", "reason": item.get("reason", ""), "text": item.get("text", "")})

    debug(f"edit game={game} applied={len(applied)} skipped={len(skipped)}")
    return {
        "game": game,
        "applied": applied,
        "skipped": skipped,
        "notes": notes,
        "visual_checked": False,
    }
