# Seminar presentation

Self-contained reveal.js deck for the Survey Item Generator project.

## Present

Open `slides/index.html` in any modern browser (Chrome/Firefox/Edge). Works **offline** — reveal.js and all figures are bundled locally, no internet needed.

- **Navigate:** arrow keys / space
- **Fullscreen:** `F`
- **Overview (grid of all slides):** `Esc` or `O`
- **Speaker view (notes + timer):** `S` (opens a second window; allow pop-ups)
- **Black out screen:** `B`

Every slide has speaker notes embedded (visible in speaker view).

## Export to PDF

In Chrome, open the deck with `?print-pdf` appended to the URL:

```
file:///.../slides/index.html?print-pdf
```

then File → Print → Save as PDF (Layout: Landscape, Margins: None, Background graphics: ON).

## Edit

- Content/text: edit `index.html` directly (one `<section>` = one slide).
- Title-slide presenter names: first `<section>`.
- Figures live in `slides/figures/` (copied from `docs/figures/`). Regenerate the source figures with `python scripts/generate_figures.py`, then re-copy.

## Contents

| Folder | What |
|--------|------|
| `index.html` | The deck (27 slides incl. Run 4 judge findings + appendix) |
| `reveal/` | Vendored reveal.js 5.1.0 + notes plugin |
| `figures/` | PNG figures from the baseline evaluation |
