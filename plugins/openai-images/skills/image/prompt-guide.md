# GPT Image prompt guide

How to write prompts for OpenAI GPT Image (2.5 and 2.6) with this plugin. Tags: **[OAI]** OpenAI's own
guide or Cookbook, **[COMM]** community practice, **[OURS]** this plugin's convention.

## Rules

1. **Brief before prompt.** Find the deliverable and its use, the exact text, the size or ratio, and the
   role of each input image. Ask one question only if a missing fact blocks success; otherwise assume and
   say what you assumed. [OAI]
2. **How much to add.** If the user gave details, keep them and only restructure. If the idea is generic,
   add composition, polish level, layout and concrete scene detail. Never add characters, brands,
   slogans, palettes or story beats the user did not imply. [OAI]
3. **Structure.** Start with a verb and the deliverable and its use ("Create a printable poster for...").
   Then labeled lines: scene, subject, details, text, constraints. Put canvas and layout first when the
   structure matters (posters, infographics). [OAI + COMM]
4. **Be concrete.** Name materials, light source, palette, medium and framing. Replace praise words
   ("stunning, epic, masterpiece, 8K") with visible facts. Keep material, lighting and palette on
   separate lines. One camera or capture frame, not several. [OAI + COMM]
5. **Text.** Every string that must appear goes in "double quotes" with its position, typography
   (weight, style, color, rough size) and count ("exactly once"). Spell rare words letter by letter. Keep
   strings short. End with "No other text." Long copy belongs in HTML or a layout tool, not the image.
   [OAI + OURS]
6. **People and counts.** Give framing ("full body, feet visible"), gaze, and what the hands do. Write
   counts as digits and list the items ("exactly 3 balloons: red, blue, yellow"). Keep counts at 12 or
   fewer. [OAI + COMM]
7. **Negatives.** Describe the wanted state positively ("plain empty background"). Keep "No ..." for
   artifacts, in one short line: "No extra text, no watermark, no logos." [OAI + COMM]
8. **Photorealism.** Say "photorealistic" plus how the photo was taken (candid, 35mm, phone photo; eye
   level; 50mm), the light and real texture (pores, wear, grain). Add "No glamorization, no heavy
   retouching." Lens specs are hints for the look, not physics. [OAI]
9. **Edits.** `Change only:` one thing, then `Preserve exactly:` (identity, pose, geometry, layout,
   lighting, camera angle, existing text, background), then no new elements. Repeat the preserve list on
   every edit. Several fixes: batch them into one edit or edit from the original; long chains of edits
   drift. [OAI + COMM]
10. **References.** Number each input and give its role: "Image 1: edit target (the room). Image 2: style
    reference (palette and brushwork only)." Then say what moves where. A mask applies only to Image 1.
    [OAI]
11. **Transparent assets.** `background: "transparent"` with `png` or `webp`. In the prompt describe only
    the isolated subject. Any background described in the prompt wins over the parameter. [OAI]
12. **Parameters, not prose.** The ratio goes in `size` (and may also be named in the prompt). Never
    plan to crop or stretch afterwards. [OAI + COMM]

Not available in this plugin's tools: `complexity`, `markup`, `moderation`, `svg`/`gif` output. Don't
promise them.

## Generate template

```text
Create a <deliverable> for <use/audience>. <Canvas/format, e.g. "Vertical 2:3 poster">.
Scene: <environment, background, time of day>
Subject: <main subject; exact count; pose/action; gaze/hands>
Style: <medium + 2-3 concrete style facts>
Composition: <framing, viewpoint, placement, negative space>
Lighting & palette: <light source/quality>; <3-4 colors>
Details: <materials, textures, 5-10 concrete nouns>
Text (verbatim, each exactly once): "<STRING 1>" - <position, typography>; "<STRING 2>" - <...>
Constraints: <must keep / must include>. No other text, no watermark, no logos.
```

Drop lines that don't apply. A simple request can be two or three lines.

## Edit template

```text
Edit Image 1 (<what it is>). Change only: <one concrete change>.
Preserve exactly: <identity/face, pose, geometry, layout, lighting, camera angle, existing text, background>.
<Image 2: <role> - what to take from it.>
Do not add new objects, text, logos, or watermarks.
```

## Size and quality

Sizes must be `WxH` with both sides multiples of 16, ratio between 1:3 and 3:1, no edge above 3840, and
655,360 to 8,294,400 pixels in total (so `512x512` is too small). Above 2560x1440 is experimental on 2.5.

| Use | Size | Cost at medium, 2.5 Sunburst |
|---|---|---|
| Icon, logo, sticker, square post | `1024x1024` | ~0.013 USD |
| Poster, flyer, phone wallpaper | `1024x1536` | ~0.010 USD |
| Banner, product shot, landscape diagram | `1536x1024` | ~0.010 USD |
| Slide, video thumbnail (16:9) | `1536x864` | ~0.008 USD |
| Large print (ask first: more pixels cost more) | `2048x2048` | ~0.027 USD |

Quality: `low` (~0.006 USD at 1024x1024) for drafts and options, `medium` (default) for finals, `high`
(~0.053 USD, ask first) only when small or dense text fails at medium. `xhigh` and `max` almost never.
Each edit input image and mask adds a 0.05 USD allowance to the estimate.

## Checklist and critique

1. Before the call, list what must be true: each quoted string (spelling, casing, once), counts, required
   elements, placement, style, exclusions, transparency.
2. Open the saved file. Read small text closely. Mark each item PASS or FAIL. Text and required elements
   are hard gates; don't average them away.
3. Also look for: invented text, logos or numbers; extra or missing objects; broken hands, faces or
   objects; changes outside the edit area; mood drift (often darker than asked).
4. Fix only what failed: **edit** when the composition is right and the error is local; **regenerate**
   with only the failing line changed when the layout or concept is wrong.
5. Stop after 2 fix attempts and show the best image with what is still wrong.

## Failure modes and fixes

| Failure | Fix |
|---|---|
| Misspelled, duplicated or extra text | Quote it, shorten it, "exactly once", spell rare words letter by letter, "No other text". One wrong word in a good image: edit "change only the word X to Y". Still wrong: offer `high`. |
| Invented numbers, labels, logos | Give all data and labels in the prompt; "only these labels; no other text, no logos". For exact charts, suggest making the chart in code. |
| Layout or placement off | Put canvas and layout first ("top third: title; center: ..."); regenerate. |
| Wrong count | Digits plus a list of items; edit "remove one balloon; keep everything else". |
| Bad hands or fingers | Describe the exact hand action; avoid interlocked fingers; fix with a local edit. |
| Background ignores `transparent` | Remove every background word from the prompt; describe only the isolated subject. |
| Drift over several edits | Repeat the preserve list; edit from the original; batch changes into one edit. |
| Too much "AI polish" on photos | "photorealistic, candid, 35mm"; real texture; "no glamorization, no heavy retouching". |
| `moderation_blocked`, input stage | Remove real names, brands, franchise names and loaded words; describe what is visible. |
| `moderation_blocked`, output stage (often photoreal people) | Add modest, specific clothing and a benign context, or, if the user agrees, an illustrated medium. After 2 tries, explain. |
| Real person or franchise likeness | Ask for an "original, non-infringing" design; describe style properties, not the name. |

## Recipes

Every recipe uses the default model and `output_format: "png"` unless it says otherwise. Fill the
example with the user's own content.

### Poster or flyer
`size: "1024x1536"`, `background: "opaque"`, quality `medium` (offer `high` if small text fails)

```text
Create a printable vertical 2:3 birthday party poster for a 6-year-old.
Layout: top third headline; center hero illustration; bottom band with party details.
Subject: a friendly cartoon dinosaur in a party hat, holding exactly 6 balloons (red, yellow, blue, green, orange, purple).
Style: flat vector children's illustration, rounded shapes, thick soft outlines.
Palette: sunny yellow background, teal, coral, white accents.
Text (verbatim, each exactly once): "MIA IS 6!" - top, large bold rounded sans-serif, white with coral outline;
"Saturday, May 9 · 3 PM" and "12 Oak Street" - bottom band, medium clean sans-serif, dark teal.
Constraints: high contrast, legible from a distance. No other text, no watermark, no logos.
```

### App icon
`size: "1024x1024"`, `background: "opaque"`, quality `medium` [OURS: from OpenAI's logo rules]

```text
Create an app icon for a habit-tracking app called "Streak".
Subject: a single bold check mark merged with a rising flame, centered, filling about 70% of the square.
Style: modern flat icon, simple geometric shapes, subtle two-tone gradient, strong silhouette that reads at 32 px.
Background: solid deep indigo filling the whole square edge to edge (the OS applies the rounded mask).
Constraints: one symbol only, no text or letters, no border, no drop shadow outside the shape, no watermark.
```

### Logo
`size: "1024x1024"`, `background: "transparent"`, `output_format: "png"`, quality `medium`; for several
ideas, offer `n: 3` (ask first) [OAI]

```text
Create an original, non-infringing logo for "Field & Flour", a local bakery.
Feel: warm, simple, timeless. Mark: a wheat stalk forming the letter F beside the wordmark.
Style: clean vector-like shapes, strong silhouette, balanced negative space, flat colors (wheat gold, charcoal), minimal strokes, no gradients.
Text (verbatim, exactly once): "Field & Flour" in a friendly serif.
Fully transparent background: single centered logo, generous padding, clean alpha edges; no backdrop, scenery, checkerboard, shadow, or watermark.
```

### Product shot
`size: "1536x1024"`, `background: "opaque"`, quality `medium` [OAI]

```text
Create a photorealistic e-commerce hero photo of a matte sage-green ceramic coffee mug.
Scene: light oak table, plain warm off-white wall, empty right third for page copy.
Subject: one mug at a slight three-quarter angle, steam rising, a folded linen napkin beside it.
Lighting: soft window light from the left, gentle contact shadow, natural color balance.
Details: visible glaze speckles, fine ceramic texture, crisp rim highlight; eye level, 85mm look, shallow depth of field.
Constraints: no text, no logos, no watermark, no other props.
```

### Infographic or diagram
`size: "1536x1024"` (or `1024x1536` for a tall one), `background: "opaque"`, quality `medium` (offer
`high` if labels are small or many) [OAI]

```text
Create a clean educational infographic titled "How Rain Forms" for 10-year-olds.
Layout: title across the top; left-to-right flow of 4 numbered stages connected by arrows; white background.
Stages and labels (verbatim, each exactly once): "1 Evaporation", "2 Condensation", "3 Clouds", "4 Precipitation".
Style: flat vector icons, consistent stroke width, blue and teal palette with one warm accent, generous white space.
Constraints: labels large and readable; only the title and these labels; no extra text, no numbers or data not listed, no logos.
```

### Photo edit
`edit_image` with `images: ["<the photo>"]`; keep the photo's own ratio in `size` (e.g. `1536x1024` for
a 3:2 landscape) and `background: "opaque"`, quality `medium` [OAI]

```text
Edit Image 1 (the family photo). Change only: replace the overcast sky with a clear late-afternoon sky with a few soft clouds.
Preserve exactly: every person's face, identity, expression, pose and clothing; the house, trees and lawn; camera angle and framing.
Match the new light gently on the scene (warm, low sun from the left) without changing skin tones.
Do not add new objects, people, text, or watermarks.
```

For a local change, add a `mask` PNG (transparent where the change goes, same size as Image 1). The model
treats the mask as guidance, not an exact boundary.

### Illustration
`size: "1536x1024"` (or `1024x1024`), `background: "opaque"`, quality `medium` [OAI + COMM]

```text
Create a storybook illustration for a children's book page about a fox who loves reading.
Scene: a cozy burrow lit by a single candle, round wooden door, shelves of tiny books, evening.
Subject: one small red fox sitting on a cushion, holding an open book with both paws, looking down at the page.
Style: soft gouache painting, visible brush texture, gentle edges, warm and calm.
Composition: medium shot, fox slightly left of center, open space above for page text.
Lighting & palette: warm candlelight from the right; rust orange, cream, moss green, deep brown.
Constraints: no text, no letters on the books, no watermark.
```

### Transparent sticker
`size: "1024x1024"`, `background: "transparent"`, `output_format: "png"`, quality `medium` [OAI]

```text
Create a die-cut sticker design of a happy cartoon avocado half giving a thumbs up.
Style: bold flat colors, thick white outline around the whole shape, clean vector look, cute and simple.
Palette: avocado green, light yellow-green flesh, brown pit, white outline.
Fully transparent background: single centered sticker, generous padding, clean alpha edges; no backdrop, scenery, checkerboard, shadow, or watermark.
Constraints: no text.
```
