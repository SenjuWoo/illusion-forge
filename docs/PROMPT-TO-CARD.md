# Prompt to card

`forge compile` reads the sentence and fills a spec. Pass `--game kk` or `--game hs2` when the sentence does not name the game. If it names both, compilation stops.

Face phrases start at 0.5 and add a fixed delta, then clamp to 0..1. They are applied only for Honey Select 2:

| Phrase | Slider | Delta |
| --- | --- | --- |
| wide face, round face, chubby face | face_width | +0.25 |
| narrow face, slim face, small face | face_width | -0.25 |
| big eyes, large eyes, huge eyes | eye_width_1 | +0.20 |
| small eyes | eye_width_1 | -0.20 |
| small nose | nose_width | -0.20 |
| big nose, large nose | nose_width | +0.20 |
| big lips, full lips, large lips | lip_width | +0.20 |
| small lips, thin lips | lip_width | -0.20 |
| long ears | ear_length | +0.20 |

Koikatsu height phrases set `body_sliders.height` to an absolute value: very short 0.15, short 0.25, average height 0.50, tall 0.85. The same phrases are unmapped for Honey Select 2. A height phrase is skipped when the next word is a hair or clothing noun, including a comma stuck to that word. A later height phrase in the same sentence still counts, so "short hair who is short" is height 0.25.

Hair and eye colors are matched from phrases such as "black hair" and "blue eyes". Skin phrases are pale, fair, tan, and dark. The color numbers are table values, not samples from a card.

`named "First Last"` splits on the last word into firstname and lastname, and sets fullname to the whole string. A card that lacks one of those fields skips it.

"female" and "woman" set sex 1. "male" and "man" set sex 0. "girl", "boy", "loli", and "child" do not set sex.

Clothing words are listed once in `unmapped` with the reason that no catalog was installed. They do not become item ids. A longer phrase wins its own span, so "school uniform" is not also "uniform", and a later separate "uniform" is still listed.

`forge index` reads the character cards already in each game's `UserData/chara` folder. `forge match` lists the closest cards. `forge make` copies the closest one and then applies the prompt.

The copy keeps that card's face, body, and outfit. A Honey Select 2 face phrase is added to the card's current slider. It is not a reset to 0.5. A Koikatsu height phrase is still an absolute value. Hair, eye, and skin colors replace the card's colors when the prompt names them. A name in the prompt replaces the card's name. Clothing words select a card whose file or character name contains them. They do not become item ids.

Search aliases, used only for matching: gyaru/gal and ojousama/ojou. A word of five letters or more also matches a longer card word that starts with it, so "school" finds a card named schoolgirl. The "2" in "honey select 2" is not used as a name. A longer stored name beats a shorter one that is only part of it, so Tina Armstrong beats a card named Tina. A match is confident only when a filename, a character name, or a stock personality label hit. Color and sex alone are reported as not confident. If no card name contains the clothing words, `match` returns nothing rather than inventing an outfit.

When the prompt names nobody, a card that sits directly in the `female` or `male` folder is preferred, and color still beats that preference. A folder named `Old` ranks below the current copy of the same character. Equal name scores prefer the newer file. A height phrase is not also a character name, so "short woman" does not search for someone named Short, while "short hair" still can. A name that is not in the library returns no card.

Write the result with:

```text
forge apply --source template.png --dest out\card.png --prompt "..." --game hs2
```

Or pass `--spec spec.json` produced by a model that already built the spec. The apply step still refuses unknown slider names and missing fields.
