# Route Edge — NFL player stats and price comparisons

A clean, standalone dashboard for QB, RB, WR and TE statistics, real game-history charts, position-specific projections and sportsbook comparisons.

## Open the redesigned site

**Download [site-preview.html](site-preview.html) using GitHub’s Download raw file button, then open it in your browser.** The page loads the latest published model bundle automatically. You can also import `latest.json` from a successful workflow artifact using the + button.

- Search player names, team names or opponents.
- Isolate QB, RB, WR or TE; combine team and opponent filters.
- Group players and bet comparisons by position or team.
- Explore season totals, per-game stats, last-five totals and last-game stat lines.
- View actual weekly history with the next projection and 80% predictive range.
- Import sportsbook odds, or enter a manual line and price; see the estimated value and the reasoning behind the comparison.
- Inspect market-specific current-season tests, including markets that fail to beat the baseline.

Basic statistics cover passing, rushing, receiving, touchdowns, turnovers, first downs, two-point conversions and efficiency rates where available. Missing fields are not fabricated. Snap share is not route participation.

## Models and weekly public data

Public nflverse weekly player statistics and offensive snap data are checked every six hours by GitHub Actions. SumerSports supplies optional current route scenarios. Separate conditional-outcome forests use position-relevant lagged usage, efficiency, EPA/CPOE where available, snap trends, team context and opponent results.

The v0.3 model covers 11 market types: passing yards, attempts, completions, touchdowns and interceptions; rushing yards, attempts and touchdowns; receiving yards, receptions and touchdowns. Each market has its own chronological evaluation and quality gate. A modeled market does not imply a verified betting advantage. See [MODEL.md](MODEL.md).

Run **Actions → Public-data model and current-season tests → Run workflow** for a fresh model bundle. The latest fully completed week is held out separately. No current-season route totals enter historical folds.

```sh
pip install -r requirements.txt
python -m unittest discover -s tests -v
node --test tests.mjs tests/*.test.mjs
node scripts/build-preview.mjs
python -m edge.pipeline --season 2026 --start-season 2021 --output data
```

## Results and limits

The first receiving-only v0.2 run succeeded and is documented in [RESULTS.md](RESULTS.md). The v0.3 extension must be assessed using its own freshly generated report; its populations and feature set differ, so the earlier results cannot be presented as its performance.

Expected value uses win, loss and push probabilities. Reasoning describes observed signals and model-price differences, not causal feature attribution. It explicitly reports negative value or disagreement. Manual prices are unverified. Historical price backtesting, verified profit, optimality and guaranteed edges are not claimed. Forecasts assume participation; check current availability, trades and sportsbook rules.

No new hosted deployment is implied. `site-preview.html` is the redesigned interface. The legacy `worker/index.js` remains a separate server-backed scenario lab/odds adapter. No credentials or private Site identity are included here. Browser visual QA was unavailable in the authoring environment; software and end-to-end fixture checks are provided.
