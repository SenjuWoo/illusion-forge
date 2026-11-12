# Illusion Forge

Illusion Forge edits Koikatsu and Honey Select 2 character cards from a short prompt. It picks the closest card already installed with the game, applies only the differences the prompt names, and can send that result to the in-game character maker.

The compiler is a fixed phrase table. It does not call a model. A compiled spec is a starting point, not a claim that the character looks like the sentence.

## Requirements

- Python 3.10 or newer
- A local install of Koikatsu, Honey Select 2, or both, when you want to index or edit real cards
- .NET SDK 10, plus BepInEx in the game, when you want to build the maker plugin
- Windows for the plugin. Card reading, writing, and the prompt compiler run on any system Python supports

The forge does not ship game files.

## Install

```text
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e .
illusionforge doctor
```

From a checkout without installing the console script, `python forge.py` is the same command. `pip install -r requirements.txt` with `PYTHONPATH=src` also works.

Point the forge at each game with one of these, in this order:

1. `ILLUSION_KK_ROOT` or `ILLUSION_HS2_ROOT`
2. `illusionforge.local.json` next to the checkout (see `illusionforge.local.example.json`)
3. A Steam library whose `steamapps/common` folder contains `Koikatu.exe` or `HoneySelect2.exe`

## Quick start

```text
illusionforge doctor
illusionforge index
illusionforge match "koikatsu gyaru"
illusionforge make "honey select 2 named \"Aoi Tanaka\" with blue eyes"
illusionforge compile "koikatsu tall woman with black hair"
```

`illusionforge make` writes the card under `out/cards`. It refuses a destination inside a game install unless you pass `--approve-gamedir`.

`illusionforge index` reads `UserData/chara` and caches the search index under `local/indexes`. Re-running it reuses cards whose size and modification time did not change.

## Maker plugin

`illusionforge build-bridge` compiles `plugins/MakerBridge` against each installed game and runs the JSON self-test. The DLL is written to `build/bridge/kk` or `build/bridge/hs2`. It is not copied into the game.

`illusionforge install-bridge --game kk --approve` copies it to `BepInEx\plugins\IllusionForge`. Without `--approve` the command refuses.

With the game open in the character maker, `illusionforge bridge ping` talks to `127.0.0.1:47331`. The plugin does not listen on any other address.

## What it does

- Identifies a card from the marker after the PNG `IEND` chunk
- Reads Koikatsu cards with [kkloader](https://pypi.org/project/kkloader/) and Honey Select 2 cards with the header described in `docs/CARD-FORMAT.md`
- Searches installed character cards by file name, character name, and stock personality
- Applies face phrases as deltas on the chosen card, and keeps that card's outfit
- Speaks MCP on stdin/stdout (`illusionforge mcp`)
- Builds a BepInEx plugin that applies a spec by reflection while the maker is open

## What it does not do

- It does not launch the game
- It does not install the plugin unless you pass `--approve`
- It does not click maker sliders
- It does not turn clothing words into item ids
- Honey Select 2 outfit blocks are copied unchanged
- Named face sliders are Honey Select 2 only. Koikatsu face edits use a numeric index inside that card's face length
- The only named body slider is Koikatsu height, `shapeValueBody` index 0
- Material Editor, ABMX, and overlay textures are not applied
- No maker screenshot has been reviewed. Responses keep `visual_checked` false

## Development

```text
python -m unittest discover -s tests -q
dotnet run --project plugins/JsonMini.Tests -c Release
```

Set `PYTHONPATH=src`. Card round-trips run only when a game install is configured. A checkout without one skips those tests.

Set `ILLUSIONFORGE_DEBUG=1` to append `local/logs/illusionforge.log`.

## Layout

`src/illusionforge` is the Python package. `plugins/MakerBridge` is the BepInEx plugin. `docs/` describes the card format, the prompt table, and the bridge. `skills/illusion-forge` is a short agent skill for this checkout.

## License

MIT. See `LICENSE`. kkloader is a separate dependency. Honey Select 2 face slider names follow the field order in [Facial Data Extractor](https://github.com/ChasonJiang/Facial-Data-Extractor/blob/main/src/face_data_utils.py). Game data stays in the game install.
