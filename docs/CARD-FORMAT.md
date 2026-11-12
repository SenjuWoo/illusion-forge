# Card format

Both games store a PNG and then a binary tail after `IEND`.

## Koikatsu

Marker `【KoiKatuChara】`, product 100, version `0.0.0` on the card that was read. kkloader owns this layout: a face-image blob, then lstInfo, then blocks. The local female card's blocks were Custom, Coordinate, Parameter, and Status.

Measured on that card:

- `shapeValueFace` length 52
- `shapeValueBody` length 44
- body index 0 is height
- `sex` was 1
- colors are four floats in 0..1: skin `skinMainColor`, hair part `baseColor` (also `startColor` and `endColor` when present), eyes `pupil[].baseColor`, eyebrows `eyebrowColor`
- clothes part 0 has an integer `id`

Named Honey Select 2 face sliders are not written onto this 52-float list.

## Honey Select 2

Marker `【AIS_Chara】`, product 100, version `1.0.0` on the card that was read. After the version string: language int32, a 7-bit user id, a 7-bit data id, then lstInfo.

Measured on that card:

- face length 59, which matches the name table
- body length 33
- no verified body name, including height
- `sex` was 1
- `fullname` was present; `nickname` was not
- skin color field is `skinColor`
- hair part colors include `baseColor`, `topColor`, and `underColor`
- blocks: KKEx, Custom, Coordinate, Parameter, GameInfo, Status, Parameter2, GameInfo2
- Coordinate's version string is `0.0.0`, and the Koikatsu outfit parser raises `UnicodeDecodeError` on those bytes. The block is copied through.

An edit reserializes only Custom and Parameter. The other block payloads stay the bytes they were loaded with. A load that changes nothing writes the original file bytes.

## Sex

Cards read while writing this tool stored `sex` as 1 or 0 and no other value. The compiler emits 1 for "female" or "woman" and 0 for "male" or "man". "girl", "boy", "loli", and "child" do not set the byte.
