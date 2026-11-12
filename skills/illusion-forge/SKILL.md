---
name: illusion-forge
description: Use when editing Honey Select 2 or Koikatsu character cards, compiling a character prompt into a spec, or talking to the Illusion Forge maker bridge. Loads the local illusionforge CLI and does not write into the game unless the operator passed the approve flag.
---

# Illusion Forge

The source root is the directory that contains this skill's parent `skills` folder when the skill is read from the forge checkout. Prefer `python forge.py doctor` and `python forge.py inspect` over remembered paths.

## Do this

1. `python forge.py doctor` and use the game ids it prints (`kk`, `hs2`).
2. `python forge.py inspect <card>` before choosing indexes. Use the face and body lengths from that output.
3. `python forge.py index` once, then `python forge.py match "<prompt>"` or `python forge.py make "<prompt>"`. `make` copies the closest installed card outside the game. Face phrases are deltas on that card. Its outfit stays. An unnamed prompt prefers a stock `female` or `male` card. A missing name returns no card.
4. `python forge.py compile "<prompt>" --game kk|hs2` for a first spec. Extend it only with names from `python forge.py sliders` or with numeric indexes inside the inspected length.
5. `python forge.py apply --source <card> --dest <outside the game> --spec <file>` when the source card is already chosen.
6. If the maker is open and the bridge was installed, `python forge.py bridge status`, then `python forge.py bridge apply --payload <json>`.

## Do not

- Do not write a destination under a game root. MCP apply cannot. The CLI needs `--approve-gamedir`, which the operator has to pass.
- Do not install the DLL without `install-bridge --approve`.
- Do not treat the phrase table as proof of appearance. `visual_checked` is false until a screenshot from a real maker session has been looked at.
- Do not assign Honey Select 2 face names to a Koikatsu card.
- Do not invent a bust index or a clothing id.
- Do not parse a Honey Select 2 coordinate block as a Koikatsu outfit.

## Fields that are verified

- Koikatsu height: body index 0.
- Honey Select 2 face names: `src/illusionforge/data/hs2_face_sliders.json`.
- Colors: four floats, 0..1. Values above 1 are treated as 0..255.
- The indexed cards stored sex 1 or sex 0 and no other value. `python forge.py make` is the prompt path. It does not write into the game.

Debug log: set `ILLUSIONFORGE_DEBUG=1`. The file is `local/logs/illusionforge.log`.
