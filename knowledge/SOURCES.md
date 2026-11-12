# Sources

Facts below were checked while building 1.0.0. A later card can differ. Read the card before writing a number into a spec.

- kkloader 0.1.24 reads and writes Koikatsu character data. It has no Honey Select 2 class. Custom face, body, and hair are int32-length MessagePack fields. Parameter is one MessagePack object.
- Facial Data Extractor field order, used only as the Honey Select 2 face name table: https://github.com/ChasonJiang/Facial-Data-Extractor/blob/main/src/face_data_utils.py
  The local copy is `src/illusionforge/data/hs2_face_sliders.json`. Indexes 0..58 are the shape names. The author's writer assigns the first 54. Color fields in that project are separate and are not shape slots.
- A local Honey Select 2 female card had 59 face floats and 33 body floats, marker `【AIS_Chara】`, product 100, version `1.0.0`, sex 1, and a fullname. Its coordinate block did not parse as a Koikatsu outfit.
- A local Koikatsu female card had 52 face floats, 44 body floats, sex 1, and height at body index 0. That index is also what the original Koikatu character loader writes for height.
- Character cards indexed from a full install stored sex 0 or sex 1 and no other value. Stock Koikatsu personality files exist under both an English name and a Japanese name.
- Both games' `Assembly-CSharp.dll` contain the ASCII names `UpdateShapeFaceValueFromCustom`, `UpdateShapeBodyValueFromCustom`, `ChangeSettingHair`, `shapeValueFace`, `shapeValueBody`, `fileFace`, `fileBody`, and `fileHair`. Koikatsu has `skinMainColor`. Honey Select 2 has `skinColor`. Signatures were not decompiled.
- Both API DLLs contain `MakerAPI` and the namespace `KKAPI.Maker`, plus `GetCharacterControl` and `InsideMaker`. The plugin searches loaded types for that name and namespace rather than calling a compiled reference.
- Nothing public turns a text prompt into a Honey Select 2 or Koikatsu card through the in-game maker. Image-to-slider projects that exist are a different input and, for the one cited above, are not a perfect replica.

DeathWeasel's random character generator is the pattern for writing `ChaFile` fields from category lists inside the maker. This version does not copy that generator. The catalog command is a capped reflection probe and can fail closed.
