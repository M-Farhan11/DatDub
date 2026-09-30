# Frontend Test 4: Landing redesign + studio layout from the Excalidraw sketch

- **Date:** 2026-09-30
- **Author:** H area, made in Farhan's session with Haider's agreement
- **Branch:** `F/phasef9`
- **What was built:** a new landing page (a large floating "DatDub" wordmark over an animated
  cell background, one **Launch studio** button, a How-it-works walkthrough that moves on its own,
  Core features, a security section that shows what goes where, FAQ). The closing card, the
  product preview and the comparison table were removed. In the studio: no sidebar on the
  source page, sources come before "or Describe your system", the generating screen is
  centered with 4 steps, and the export page has the ZIP on top.

> **Tip for the tester:** paste this file into any AI assistant and ask
> "explain this and help me run it step by step".

## Setup

Follow Part A of `Manual Testing/frontendtest1.md`, then in `frontend/` run:

```powershell
npm install
npm run dev
```

`npm install` is needed once because a new package (`motion`, the animation library) was added.
Open http://localhost:5173. The backend can run with `AI_PROVIDER=mock`.

---

## Tests

### Test 1: Hero
- **Purpose:** the first screen shows the brand and one clear action.
- **Steps:** open http://localhost:5173 on a desktop-width window.
- **Expected:** a very large "DatDub" ("Dat" dark, "Dub" blue) fills the middle. On load the
  letters drop into place, then the word slowly floats up and down. Behind it, a grid of soft blue,
  cyan and a few coral tiles fades in and out. One sentence and one blue **Launch studio** button
  sit below the word.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 2: Header and footer alignment
- **Purpose:** check the header and footer layout from the sketch.
- **Steps:** look at the top bar, then scroll to the bottom of the page.
- **Expected:** header: the logo is on the far left, the 4 links (How it works, Core features,
  Privacy, FAQ) are in the exact center, and **Launch studio** is on the far right. Footer: the
  logo and © line are on the left and the links are on the right. On a phone-width window (≈390px),
  the header shows the logo and button only, and the footer never stacks centered.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 3: Header links scroll to sections
- **Purpose:** the anchors work.
- **Steps:** click each header link in turn.
- **Expected:** the page scrolls to "How it works", "Core features", "How we keep you secure"
  and "Questions teams ask first". The section heading is not hidden under the header.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 4: How it works walkthrough
- **Purpose:** the moving cards work and can be controlled.
- **Steps:** scroll to How it works and wait 15 seconds. Then hover the cards. Then click
  **Pause the walkthrough**. Then click the card for Step 3.
- **Expected:** a blue outline moves from Step 1 → 2 → 3 → 4 → 1, about every 3.5 s, with a blue
  bar filling along the bottom of the active card. While the mouse is over the cards it stops.
  After Pause, the button reads **Play the walkthrough** and nothing moves. Clicking a card
  highlights it right away.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 5: Removed sections
- **Purpose:** check that the sketch's removals are done.
- **Steps:** scroll through the whole landing page.
- **Expected:** there is **no** "Build your first test environment in minutes" card above the
  footer, **no** schema diagram preview under the hero, and **no** "Why not just fake data?" table.
  The FAQ is still there and its questions open and close.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 6: Security section
- **Purpose:** the security section explains the data flow.
- **Steps:** scroll to "How we keep you secure".
- **Expected:** three boxes joined by arrows: Your source → DatDub engine → AI model (the last one
  tinted blue, listing "Never a single row"). Below them are 4 cards (AI never sees rows, read-only,
  personal data replaced, deleted after 60 minutes).
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 7: Source page layout
- **Purpose:** the source page matches the sketch.
- **Steps:** click **Launch studio**.
- **Expected:** there is **no left sidebar**. The DatDub logo sits top-left in the header, with the
  5-step stepper in the middle. The page shows 3 cards in a row (Upload CSV files, Connect a
  database, Use a template), then an "or" divider, then the "Describe your system" box, then the
  finance example banner at the bottom. Clicking the header logo returns to the landing page.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 8: Sidebar returns on the schema page
- **Purpose:** the sidebar only shows once there is a schema.
- **Steps:** click **Load finance example**.
- **Expected:** the Schema step opens and the narrow left sidebar (table, graph and document icons)
  is visible again.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 9: Configure + centered generating screen
- **Purpose:** check the configure layout and the generating screen.
- **Steps:** continue to Configure. On a wide window, click **Suggest** so the edge-case list gets
  long, then scroll. Then click **Generate data**.
- **Expected:** the "Size and settings" card stays in view while you scroll. The empty edge-case
  field shows the hint "For example: late payments and duplicate customers". After Generate, a
  card appears in the **middle of the screen** (both directions), with a progress bar and 4 steps:
  Creating tables and links, Filling rows, Adding edge cases, Checking every rule. The steps tick
  off with a small pop.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test 10: Export layout
- **Purpose:** the ZIP is the main download.
- **Steps:** Results → **Continue to export**.
- **Expected:** a centered title "Your dataset is ready", then the "Everything in one file" (ZIP)
  card centered on its own row. Below it, side by side: "Tables one by one" (CSV buttons) on the
  left and "To recreate this dataset" on the right. On a narrow window they stack.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

---

## Negative tests

### Test N1: Reduced motion
- **Purpose:** people who turn animations off are respected.
- **Steps:** Windows Settings → Accessibility → Visual effects → **Animation effects: Off**.
  Reload the landing page.
- **Expected:** the wordmark does not float, the letters do not drop in, the tiles stay still,
  and How it works shows no Pause button and does not move by itself (cards can still be clicked).
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test N2: Keyboard only
- **Purpose:** the new controls work without a mouse.
- **Steps:** on the landing page press Tab repeatedly.
- **Expected:** every link, **Launch studio**, the Pause button and each How-it-works card get a
  visible blue focus ring. While a card has focus the walkthrough stops moving. Enter on a card
  highlights it.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

### Test N3: Example fails without a backend
- **Purpose:** the error is still clean after the layout change.
- **Steps:** stop the backend, then click **Launch studio** → **Load finance example**.
- **Expected:** a red box above the example banner: "The finance example could not be loaded ·
  Could not reach the DatDub service…". The page stays usable.
- `Result: [ ] PASS [ ] FAIL  Notes: ____`

---

## Known limitations

- The landing page no longer has a "Try the finance example" button. The example now lives only
  at the bottom of the source page, as the sketch asks.
- The generating steps are timed for show. The last step waits for the real server response.
- `npm run build` warns that the main JS chunk is over 500 KB (the animation library added about
  40 KB gzipped). This is a warning, not an error.
