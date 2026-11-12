# Agents

This directory is the Illusion Forge source. Game installs are read-only unless the operator passes `--approve-gamedir` or `install-bridge --approve`.

- Read `STATE.md` before changing behavior.
- Do not invent slider indexes, clothing ids, or ChaControl method signatures. Read the card, `illusionforge sliders`, or the live bridge, then use that.
- Named face sliders belong to Honey Select 2. Koikatsu face edits use a numeric index inside that card's face length.
- The only named body slider is Koikatsu `height` (`shapeValueBody` index 0).
- Honey Select 2 coordinate bytes are passed through. Do not parse them with the Koikatsu outfit reader.
- The MCP `illusion_apply` tool cannot write inside a game folder. That override is the CLI flag only.
- Do not launch the game and do not copy the DLL in as part of a test.
- `visual_checked` stays false until a person has looked at a maker screenshot from a run that this forge started.
- Debug: `ILLUSIONFORGE_DEBUG=1` appends to `local/logs/illusionforge.log`.
- Tests: `Run-Tests.bat` or `python -m unittest discover -s tests -v` with `PYTHONPATH=src`.
