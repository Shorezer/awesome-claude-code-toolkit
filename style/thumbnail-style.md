# Thumbnail Style

## Rules

- **High contrast.** Dark background + bright subject, or inverse. No mid-tone soup.
- **Single focal point.** One face OR one object. Never both.
- **Max 4 words of text.** Hard limit. If you can't say it in 4 words, the title isn't ready.
- **Sans-serif bold.** Inter Black, Bebas Neue, Anton, Impact. Never script, serif, or thin weights.
- **Text contrasts the background.** Never on busy pixels. Stroke or solid background block if needed.
- **Source 16:9 / 1792×1024, export 1280×720.**

## Prompt formula

The thumbnail-designer agent emits one prompt following this shape:

```
<focal subject>, <emotion/state>, <bg style>, dark teal/orange palette, hard rim light, photographic, 4 words of text "<TEXT>" in bold sans-serif, 16:9, YouTube thumbnail
```

Example for a TTS-comparison video:

```
A studio microphone with a glowing waveform behind it, slight tilt, deep navy background with orange neon accents, dark teal/orange palette, hard rim light, photographic, 4 words of text "ONE SOUNDS REAL" in bold sans-serif, 16:9, YouTube thumbnail
```

## Avoid

- Stock-photo people staring at the camera. Use a specific emotion that fits the story.
- Word salad: `"AI Tools 2026 — Best Voice Generator Compared!!!"`
- Centered text dead-center. Off-center or third-rule.
- More than 2 emoji.
- Named brand logos or copyrighted UI screenshots.
- Faces of real people the channel doesn't control.

## Palette defaults

- Dark teal (#0a2233) backgrounds with orange (#ff6b1a) accents read well in dark and light YouTube themes.
- Avoid pure white (#ffffff) backgrounds — they get lost in YouTube's UI.
