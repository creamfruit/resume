# Re:Connect Avatar Team Split

## Scope
Use this split to build the first full pack in parallel with no filename conflicts.

## Assignment Option A (3 people)
1. `Member A` (Animals + Fur)
- `animals/*.svg` (5)
- `fur/*.svg` (13)

2. `Member B` (Face Layers)
- `eyes/*.svg` (5)
- `mouth/*.svg` (5)
- `effects/*.svg` (3)

3. `Member C` (Style Layers)
- `outfits/*.svg` (6)
- `accessories/*.svg` (8)
- `bg/*.svg` (6)

## Integration Rules
- Keep every SVG at `viewBox="0 0 256 256"`.
- Do not rename files after commit.
- Keep transparent background unless asset is in `bg/`.
- Run visual check at 64px and 128px before merge.

## Done Checklist
- [ ] All listed files replaced with final art (no placeholder comment).
- [ ] Stroke weight is between `3px` and `4px`.
- [ ] No gradients except optional `bg_gradientsoft.svg`.
- [ ] Layer order works with manifest: `bg -> animals -> fur -> eyes -> mouth -> outfits -> accessories -> effects`.
