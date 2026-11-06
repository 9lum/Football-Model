# Projections n Shit

A public NFL player-prop research platform with position-specific forecasts, compact sportsbook comparisons, player histories, matchup context, kickoff weather and visible model validation.

**[Open the dashboard](https://9lum.github.io/Football-Model/platform/).** The old `site-preview.html` URL redirects to the corresponding new section. Its redundant dashboard markup has been removed, while shared model/pricing modules and original pregame forecast archives remain intact.

## What is available

- Homepage and Matchup Lab: real moneylines, spreads and game totals, plus model score/market projections, cover probabilities, fair odds and source timestamps. Public game listings are checked about every 15 minutes; multi-book API updates remain quota-aware.
- Nine views: Dashboard, Prop Explorer, Player Research, Matchup Lab, Odds Monitor, Simulation Lab, Backtesting, Model Health and Data Sources.
- Up to 16 weekly featured yardage projections in All, or eight for QB/RB/WR/TE, subject to usable history and availability. Research estimates are labeled when quality gates fail.
- A player's name appears once, with a model projection per market and compact sportsbook rows pairing over/under odds at the same line. Different lines are never merged.
- Automatic The Odds API snapshots with original timestamps, manual price entry and optional JSON imports. Imports/manual prices remain unverified.
- Public injuries, starters first, trade reconciliation and explicitly conditional backup-QB scenarios. Questionable/Doubtful are never treated as automatically out.
- 21 documented nflreadpy datasets, Parquet/DuckDB artifacts, supplemental BALLDONTLIE endpoint checks and Xweather/Open-Meteo kickoff forecasts.
- Chronological validation with MAE, RMSE, CRPS, Brier/log loss, 80% intervals and calibration diagnostics. The first pregame forecast and subsequent actuals remain separate from reconstructed historical tests.
- LightGBM/XGBoost research challengers, selected on earlier-season development and evaluated on untouched current-season outcomes. They are not automatically promoted.
- A 10,000-draw bootstrap simulation lab, explicitly labeled as resampling the stored empirical distribution rather than creating new evidence.

Qualifying bets require **at least 70% estimated unconditional win probability plus all existing accuracy, availability, freshness and value gates**. This is not a proven 70% hit rate, a relaxed validation rule or a guaranteed win. An average above a betting line alone does not establish an edge. Historical ROI/closing-line value remain unavailable until genuine archived prices and valid settlements support them.

## Credentials and automation

Add repository Actions secrets `ODDS_API_KEY`, `BALLDLIE_API_KEY` (or `BALLDONTLIE_API_KEY`), `XWEATHER_API_KEY`, and `XWEATHER_CLIENT_ID`. `DATABASE_URL` is optional. nflreadpy/nflverse needs no API key. No secret belongs in frontend code.

The main model, odds and supplemental provider workflows run approximately every six hours. The page checks published odds/injuries every five minutes. GitHub schedules may be delayed. The odds collector spreads reported remaining credits over future runs and may limit games, markets and regions; it is a scheduled snapshot feed, not continuous live pricing. Provider HTTP 401/403/429 responses are exposed as unavailable/access/rate-limit states rather than fabricated data.

## Development

See **[PLATFORM.md](PLATFORM.md)** for Next.js, FastAPI, Docker, PostgreSQL, source coverage, optional licensed feeds, hosting details and limitations.

```sh
pip install -r intelligence/requirements.txt
python -m unittest discover -s tests -v
python -m unittest discover -s intelligence -p 'test_*.py' -v
node --test tests.mjs tests/*.test.mjs web/*.test.mjs scripts/navigation.test.mjs
python -m intelligence.ingest
python -m edge.pipeline --season 2026 --start-season 2021 --output data
```

Frontend: `cd platform/frontend && npm ci && npm run dev`. Production build: `npm run build -- --webpack`. The dashboard workflow publishes the static export to GitHub Pages. The Docker stack additionally supplies a persistent API/database when deployed on a suitable host; GitHub Pages itself does not run Python or PostgreSQL.

Browser visual QA was unavailable in the authoring environment. Production compilation, route/market tests, real-data checks and published asset verification are performed. No subscriptions or paid infrastructure are purchased automatically.
