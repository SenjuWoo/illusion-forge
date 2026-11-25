<div align="center">

![Illusion Forge: a pink-to-violet tile with two character cards, the front one showing a bust, and a white spark, next to the tagline 'Edit Koikatsu and Honey Select 2 character cards from a short prompt, then hand them to the maker.'](docs/presentation/hero.png)

[![CI](https://github.com/SenjuWoo/illusion-forge/actions/workflows/ci.yml/badge.svg)](https://github.com/SenjuWoo/illusion-forge/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/SenjuWoo/illusion-forge?color=ff6fae)](https://github.com/SenjuWoo/illusion-forge/releases)
[![Python](https://img.shields.io/badge/python-3.10%2B-c9a7ff)](pyproject.toml)
[![Dependencies](https://img.shields.io/badge/runtime%20deps-kkloader%20%C2%B7%20Pillow-a88fa0)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-ff9fca)](LICENSE)

**[Install](#install)** · **[Tour](#a-short-tour)** · **[Commands](#commands)** · **[Maker plugin](#maker-plugin)** · **[How it works](#how-it-works)** · **[Changelog](CHANGELOG.md)**

</div>

Illusion Forge edits **Koikatsu** and **Honey Select 2** character cards from a
short prompt. It picks the closest card already installed with the game,
applies only the differences the prompt names, writes the result as a new card
outside the game, and can send the same changes to the in-game character maker
through a small BepInEx plugin.

The compiler is a fixed phrase table. It does not call a model. A compiled spec
is a starting point, not a claim that the character looks like the sentence,
and every response keeps `visual_checked` false until a person has looked at a
maker screenshot. The forge does not ship game files.

## What you get

- **Cards read and written safely.** A card is identified from the marker after the PNG `IEND` chunk. Koikatsu cards go through [kkloader](https://pypi.org/project/kkloader/); Honey Select 2 cards through the header described in [docs/CARD-FORMAT.md](docs/CARD-FORMAT.md). Edits are written to a temp file and swapped in, and a load that changes nothing writes the original bytes.
- **Your own library as the base.** `index` reads every card under the games' `UserData/chara`, and `match` and `make` search it by file name, character name, stock personality, and hair, eye and skin color. A name that is not installed returns no card instead of a random neighbour.
- **Edits, not resets.** Face phrases are deltas on the chosen card's sliders. Its outfit is kept. Hair, eye, eyebrow and skin colors, Koikatsu height, name and sex are written only when the card has that field.
- **Game folders stay read-only.** `make` always refuses a destination inside a game install, and `apply` refuses one unless you pass `--approve-gamedir`. The MCP `illusion_apply` tool cannot set that override at all.
- **A live maker bridge.** The plugin listens on `127.0.0.1:47331` and applies a spec by reflection while the character maker is open. It is installed only with `install-bridge --approve`.
- **JSON and MCP.** Every command prints JSON, and `illusionforge mcp` speaks MCP on stdin/stdout with the same operations.

![Terminal: illusionforge doctor finds Koikatsu and Honey Select 2 with their plugin API, BepInEx and UnityEngine present and no missing games; illusionforge match "koikatsu gyaru" searches 1405 Koikatsu cards and returns the stock Gyaru card (Maiko Yamamoto) with score 140 for its filename and Gyaru personality, marked confident](docs/presentation/screenshot-doctor-match.png)

## Install

Requirements:

- Python 3.10 or newer
- A local install of Koikatsu, Honey Select 2, or both, to index or edit real cards
- .NET SDK 10 and BepInEx in the game, to build the maker plugin
- Windows for the plugin. Card reading and writing and the prompt compiler run on any system Python supports

```text
git clone https://github.com/SenjuWoo/illusion-forge
cd illusion-forge
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e .
.venv\Scripts\illusionforge.exe doctor
```

On Windows, `forge.cmd <command>` runs the same CLI from that `.venv`, and
`START-HERE.bat` runs `doctor`. From a checkout without installing the console
script, `python forge.py <command>` is the same command; `pip install -r
requirements.txt` with `PYTHONPATH=src` also works. Release wheels are on the
[releases page](https://github.com/SenjuWoo/illusion-forge/releases).

Point the forge at each game with one of these, in this order:

1. `ILLUSION_KK_ROOT` or `ILLUSION_HS2_ROOT`
2. `illusionforge.local.json` next to the checkout (see `illusionforge.local.example.json`)
3. A Steam library whose `steamapps/common` folder contains `Koikatu.exe` or `HoneySelect2.exe`

No install path is built into the package.

## A short tour

```text
illusionforge doctor
illusionforge index                         # once, and after adding cards
illusionforge match "koikatsu gyaru"
illusionforge make "honey select 2 named \"Aoi Tanaka\" with blue eyes"
illusionforge compile "koikatsu tall woman with black hair"
illusionforge apply --source card.png --dest out\card.png --spec spec.json
```

`make` writes the card under `out/cards` unless you pass `--dest`. `index`
caches the search index under `local/indexes` and reuses cards whose size and
modification time did not change.

![Terminal: illusionforge make "honey select 2 woman with blue eyes" picks the stock Honey Select 2 card Tsubomi out of 994 by eye color, writes pupil[0].pupilColor and pupil[1].pupilColor to tsubomi.png with visual_checked false; illusionforge inspect tsubomi.png reads it back as a Honey Select 2 card named Tsubomi with 59 face and 33 body sliders](docs/presentation/screenshot-make.png)

The cards `make` wrote in those two runs, as they show in a card browser. The
picture on a card is the base card's own preview; `make` changes the character
data behind it and does not re-render the picture:

![Two character cards written by illusionforge make: on the left the stock Koikatsu Gyaru card, a tanned blonde girl in a light blue shirt, red tie and red plaid skirt, picked for "koikatsu gyaru with pink hair"; on the right the stock Honey Select 2 card Tsubomi, a short-haired woman in a white camisole, picked for "honey select 2 woman with blue eyes"](docs/presentation/card-preview.png)

## Commands

| Command | Does |
|---|---|
| `doctor` | Finds the games, their BepInEx and plugin API, and nearby card tools |
| `capabilities` | What this version will and will not change |
| `sniff CARD` | Names the game from the marker after `IEND` |
| `inspect CARD` | Summarizes a card: name, sex, personality, slider counts, colors, blocks |
| `sliders` | Prints the Honey Select 2 face slider names and indexes |
| `index [--game kk\|hs2]` | Reads installed cards into the local search cache |
| `match PROMPT [--game] [--limit N]` | Closest installed cards, with the reasons for each score |
| `make PROMPT [--game] [--dest PATH]` | Copies the closest card and applies the prompt on top |
| `compile PROMPT [--game]` | Turns a prompt into a spec without calling a model |
| `apply --source CARD --dest PATH [--spec F \| --prompt P] [--approve-gamedir]` | Writes a changed card, outside the game unless approved |
| `bridge ping\|status\|apply\|dump_catalog\|screenshot [--payload F]` | Sends one command to the maker plugin on localhost |
| `build-bridge` | Compiles the plugin against each installed game and runs the JSON self-test |
| `install-bridge --game kk\|hs2 --approve` | Copies the plugin into the game; refuses without `--approve` |
| `mcp` | MCP server on stdin/stdout |

![Terminal: illusionforge compile "koikatsu tall woman with black hair" returns a Koikatsu spec with height 0.85, hair color 0.05 and sex 1, noting it is not a claim the character looks like the prompt; illusionforge capabilities reports version 1.0.2, lists Material Editor, ABMX bone sliders, overlay textures, modded clothing ids and appearance claims as not in this version, and visual_checked false](docs/presentation/screenshot-compile.png)

### What it does not do

- It does not launch the game
- It does not install the plugin unless you pass `--approve`
- It does not click maker sliders
- It does not turn clothing words into item ids
- Honey Select 2 outfit blocks are copied unchanged
- Named face sliders are Honey Select 2 only. Koikatsu face edits use a numeric index inside that card's face length
- The only named body slider is Koikatsu height, `shapeValueBody` index 0
- Material Editor, ABMX, and overlay textures are not applied
- No maker screenshot has been reviewed. Responses keep `visual_checked` false

## Maker plugin

`illusionforge build-bridge` compiles `plugins/MakerBridge` against each
installed game and runs the JSON self-test. The DLL is written to
`build/bridge/kk` or `build/bridge/hs2`. It is not copied into the game.
A release that changes the plugin also carries a prebuilt `IllusionForge-<version>-maker-bridge.zip`.

`illusionforge install-bridge --game kk --approve` copies it to
`BepInEx\plugins\IllusionForge`. Without `--approve` the command refuses.

With the game open in the character maker, `illusionforge bridge ping` talks to
`127.0.0.1:47331`. The plugin does not listen on any other address. Details are
in [docs/MAKER-BRIDGE.md](docs/MAKER-BRIDGE.md).

## How it works

- `src/illusionforge/cards` reads, sniffs and writes cards. Only the Custom and Parameter blocks are reserialized; every other block keeps the bytes it was loaded with.
- `src/illusionforge/spec` is the phrase table ([docs/PROMPT-TO-CARD.md](docs/PROMPT-TO-CARD.md)) and the Honey Select 2 slider names, which follow the field order in [Facial Data Extractor](https://github.com/ChasonJiang/Facial-Data-Extractor/blob/main/src/face_data_utils.py).
- `src/illusionforge/library` builds the index and ranks cards: a file or character name beats a personality, which beats color and height.
- `src/illusionforge/bridge` is the localhost client; `plugins/MakerBridge` is the BepInEx plugin, which drives `KKAPI.Maker.MakerAPI` and the live character by reflection.
- `src/illusionforge/mcp` is the stdio MCP server. `skills/illusion-forge` is a short agent skill for this checkout.
- Design decisions are in [DECISIONS.md](DECISIONS.md), what is and is not checked in [VALIDATION.md](VALIDATION.md), and the tool search in [docs/TOOLS.md](docs/TOOLS.md).

## Development

```text
set PYTHONPATH=src
python -m unittest discover -s tests -q
dotnet run --project plugins/JsonMini.Tests -c Release
```

`Run-Tests.bat` runs the Python suite from the `.venv`. Card round-trips run
only when a game install is configured; a checkout without one skips those
tests. CI runs the Python suite on Ubuntu and Windows and the JSON self-test on
Ubuntu.

Set `ILLUSIONFORGE_DEBUG=1` to append to `local/logs/illusionforge.log`.

## License

MIT. See [LICENSE](LICENSE). kkloader is a separate dependency. Game data
stays in the game install.
