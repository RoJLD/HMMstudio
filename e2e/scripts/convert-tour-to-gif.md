# Converting the tour recording to GIF / MP4

After running:

```bash
npx playwright test tour-recording.spec.ts
```

A WebM video file is written to `e2e/test-results/<test-name>/<run-id>.webm`.

## Convert to GIF (for README / GitHub)

```bash
# 720p, 12 fps, smaller filesize
ffmpeg -i path/to/video.webm \
  -vf "fps=12,scale=720:-1:flags=lanczos,split[s0][s1];[s0]palettegen=stats_mode=diff[p];[s1][p]paletteuse=dither=bayer:bayer_scale=5" \
  -loop 0 \
  tour.gif

# 480p, smaller still
ffmpeg -i path/to/video.webm \
  -vf "fps=10,scale=480:-1:flags=lanczos,split[s0][s1];[s0]palettegen=stats_mode=diff[p];[s1][p]paletteuse=dither=bayer:bayer_scale=5" \
  -loop 0 \
  tour-small.gif
```

## Convert to MP4 (for embed in docs)

```bash
ffmpeg -i path/to/video.webm \
  -c:v libx264 -preset slow -crf 23 \
  -movflags +faststart \
  tour.mp4
```

## Linking from the README

GIF: drag the file into the GitHub README editor — it auto-uploads.
MP4: GitHub doesn't render `<video>` in markdown, but you can drag the
MP4 file into an issue / PR to get a hosted URL, then reference it.

For mkdocs (Documentation site), MP4 + a `<video>` tag works:

```html
<video controls width="720">
  <source src="../assets/tour.mp4" type="video/mp4">
  Your browser does not support the video tag.
</video>
```

Place `tour.mp4` under `docs/assets/`.

## Tips

- Keep the GIF under 10 MB — GitHub re-encodes anything larger.
- 12 fps is plenty for a UI walkthrough; 24 fps is overkill and doubles size.
- 720p is the sweet spot for GitHub README. Going wider (1080p) blurs at
  GitHub's typical render width.
- The first ~1-2 seconds of the WebM might be blank (browser startup).
  Trim with `-ss 1.5 -to 45` before the input filter:

  ```bash
  ffmpeg -ss 1.5 -i video.webm -to 43 ... rest of command ...
  ```
