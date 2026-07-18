# Re:Connect Animal Avatar Style Guide

## 1. Art Direction
- Flat design only (no gradients, no textures).
- Thick outline only when needed: `3px` to `4px`.
- Cute proportions: big head, tiny body (or head-only).
- Eye style limited to dots and simple curves.
- Use pastel-friendly colors and high contrast for accessibility.
- Keep silhouettes simple and readable at small sizes.

## 2. Color System
### Fur Colors
- `cat`: `#F4A261`, `#2A2A2A`, `#F6F1E9`
- `panda`: `#FFFFFF`, `#2A2A2A`
- `otter`: `#C68642`, `#A47148`
- `rabbit`: `#EADBC8`, `#D8C4B6`
- `bear`: `#8B5E3C`, `#5C3A21`

### Outfit Colors
- `orange`: `#F97316`
- `teal`: `#14B8A6`
- `blue`: `#60A5FA`
- `yellow`: `#FACC15`
- `green`: `#4ADE80`

## 3. Eye/Expression Set (Shared Across Animals)
- `dot` (neutral)
- `curve` (friendly)
- `closed_smile` (happy)
- `star` (excited)
- `glasses_overlay` (elder style)

## 4. Outfit Set (Shared Torso Overlay)
### Youth
- `hoodie`
- `tshirt`
- `varsity`

### Elder
- `cardigan`
- `polo`
- `batik`

## 5. Accessories (Shared Library)
- `round_glasses`
- `half_rim_glasses`
- `cap`
- `beanie`
- `flower_pin`
- `headphones`
- `scarf`

## 6. Layer Stack
Render order:
1. `background`
2. `animal_base`
3. `fur`
4. `eyes`
5. `mouth`
6. `outfit`
7. `accessory`
8. `effects`

## 7. File Layout
```
app/static/avatars/
  animals/
  fur/
  eyes/
  mouth/
  outfits/
  accessories/
  bg/
  effects/
```

## 8. Exact Starter Asset List
### animals (5)
- `cat_base.svg`
- `panda_base.svg`
- `otter_base.svg`
- `rabbit_base.svg`
- `bear_base.svg`

### fur (13)
- `cat_fur_01.svg`, `cat_fur_02.svg`, `cat_fur_03.svg`
- `panda_fur_01.svg`
- `otter_fur_01.svg`, `otter_fur_02.svg`, `otter_fur_03.svg`
- `rabbit_fur_01.svg`, `rabbit_fur_02.svg`, `rabbit_fur_03.svg`
- `bear_fur_01.svg`, `bear_fur_02.svg`, `bear_fur_03.svg`

### eyes (5)
- `eyes_dot.svg`
- `eyes_curve.svg`
- `eyes_closed.svg`
- `eyes_sparkle.svg`
- `eyes_sleepy.svg`

### mouth (5)
- `mouth_smile.svg`
- `mouth_bigsmile.svg`
- `mouth_openlaugh.svg`
- `mouth_tiny.svg`
- `mouth_o.svg`

### outfits (6)
- `outfit_tshirt.svg`
- `outfit_hoodie.svg`
- `outfit_varsity.svg`
- `outfit_polo.svg`
- `outfit_cardigan.svg`
- `outfit_batik.svg`

### accessories (8)
- `acc_glasses_round.svg`
- `acc_glasses_halfrim.svg`
- `acc_hat_cap.svg`
- `acc_hat_beanie.svg`
- `acc_headphones.svg`
- `acc_scarf.svg`
- `acc_flowerpin.svg`
- `acc_hearingaid.svg`

### effects (3)
- `fx_blush.svg`
- `fx_stars.svg`
- `fx_heart.svg`

### bg (6)
- `bg_solid.svg`
- `bg_gradientsoft.svg`
- `bg_dots.svg`
- `bg_stripes.svg`
- `bg_check.svg`
- `bg_confetti.svg`

## 9. Personality Mapping
- `panda`: Friendly default
- `cat`: Youth / playful
- `otter`: Social connector
- `rabbit`: Gentle learner
- `bear`: Mentor / senior

## 10. Implementation Rules
- Store only IDs in DB, not full SVG content.
- Compose avatar at runtime by ID map.
- Keep naming stable: `category_variant.svg` (example: `eyes_dot.svg`).
- New assets must follow this guide before merge.
