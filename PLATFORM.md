# Projections n Shit — professional research platform

The former research desk URL `site-preview.html` now redirects to the matching new view. Its redundant embedded dashboard has been removed. The Next.js/React/TypeScript dashboard is exported at `/platform/` and the root redirects there. Its research sections use real published JSON snapshots, ECharts, TanStack Table, Tailwind CSS and Radix primitives following shadcn conventions. No paid template or stock dashboard data is included.

## Running and deployment

The `Build professional NFL dashboard` workflow installs the locked frontend dependencies, checks the existing market/navigation tests, builds a Next.js static export and commits the export under `platform/`. Existing GitHub Pages branch publishing deploys that commit; `.nojekyll` preserves Next.js assets. The dashboard reads public GitHub data, so a private backend is not required for the hosted read-only site. Browser visual QA is unavailable in this execution environment; compilation, route logic, real-data matching and served asset checks are used.

Local frontend: `cd platform/frontend && npm ci && npm run dev`. Set `NEXT_PUBLIC_BASE_PATH=` for a local root deployment. The default production base path is `/Football-Model/platform`. `NEXT_PUBLIC_DATA_BASE` can point to a public snapshot directory or to `http://localhost:8000/api/snapshots`.

Full local stack: copy `.env.example` to ignored `.env`, populate only the credentials you have, then run `docker compose up --build`. The frontend is at http://localhost:3000 and FastAPI at http://localhost:8000/docs. PostgreSQL is internal to Compose; set a nondefault password for any nonlocal deployment. Run `docker compose --profile workers up --build` to enable the scheduled ingestion worker. Docker configuration is provided; a persistent cloud API/database is not implicitly deployed by GitHub Pages.

Python service: `pip install -r intelligence/requirements.txt`, then `uvicorn intelligence.api:app`. Set `API_AUTH_TOKEN` to require bearer authentication. Public snapshots contain no credentials. Optional `DATABASE_URL` enables the normalized migration and snapshot sync (`python -m intelligence.database`). Without it, JSON artifacts and the Parquet/DuckDB lake remain usable. The database schema covers players, teams, games, stats, injuries, weather, prices, feature snapshots, model versions, predictions, simulations and settlements; tables without validated observations remain empty.

## Provider credentials

Store these as repository Actions secrets, never in client code:

- `ODDS_API_KEY`: The Odds API. The existing quota-aware collector requests modeled props and publishes original timestamps. The six-hour schedule and limited credits are not continuous live prices.
- `BALLDLIE_API_KEY`: BALLDONTLIE (the user's spelling); `BALLDONTLIE_API_KEY` is accepted too. Each documented endpoint is tested separately because 401 may indicate missing plan access. Limited pagination is explicitly labeled partial.
- `XWEATHER_API_KEY` plus `XWEATHER_CLIENT_ID`: Xweather client secret and client ID. Alternatively the key secret may be JSON containing `client_id` and `client_secret`. A 401/403 is reported as authentication rejected; after the first rejection the run stops repeating authenticated requests and uses the public Open-Meteo fallback, labeled per game. No credential is guessed or purchased.
- `DATABASE_URL`: optional PostgreSQL connection for persistence beyond published snapshots/artifact retention.

The provider workflow downloads 21 public nflreadpy datasets: player/team weekly stats, schedules, teams, players, annual/weekly rosters, snaps, depth charts, trades, injuries, FTN charting, prior-year participation, play-by-play, three Next Gen Stats types and four PFR advanced types. Historical stats/schedules/snaps begin in 2021. NGS modeling data is loaded through nflreadpy and shifted to earlier games; current season aggregate rows never backfill prior weeks. Full Parquet tables and a DuckDB catalog are retained in workflow artifacts for seven days. This does not require an nflverse API key.

Optional PFF, Sportradar, SportsDataIO and tracking adapters accept a licensed, documented normalized HTTPS JSON feed with `asOf` and `records`. No proprietary access is implied, and no undocumented native provider endpoints are invented. Mapping and licensing remain required before model use.

## Prediction and research policy

The deployed conditional-outcome forests remain the distributional engine. Rolling windows now include 3/5/6/8/12 games, with lagged NGS, opponent EPA/success/contact/explosive-play and available coverage features. Earlier-season development chooses defensive feature families; chronological current-season tests and a complete-week holdout remain separate. Current weather and supplemental provider snapshots are descriptive until their incremental model value is validated; no arbitrary weather yardage discount is applied.

LightGBM and XGBoost median-regression challengers are evaluated on earlier-season development and untouched current-season outcomes. They are not automatically promoted and do not supply a calibrated probability distribution. More features/models do not establish better accuracy or profitability.

Qualifying bets require **at least 70% estimated unconditional win probability**, in addition to every existing accuracy, availability, freshness, route and expected-value gate. This does not set an accuracy target, change 80% prediction intervals, or certify a 70% realized win rate. Fixed-threshold cohort diagnostics expose observed behavior. A high probability at a poor price can still have negative expected value.

Simulation Lab resamples the learned empirical distribution 10,000 times. It reports the source sample count and labels exploratory scaling as unvalidated. Additional bootstrap draws do not add independent evidence or calibrate the model. Anytime rushing/receiving TD events require a joint scoring model; marginal markets are not combined under an invented independence assumption.

The immutable pregame forecast ledger and weekly actuals remain separate from reconstructed historical tests. Historical ROI and CLV stay unavailable until real archived pregame prices can be matched to valid outcomes and closing prices. Settlement utilities preserve pushes, pending outcomes and DNP voids. No fake ROI, closing price, calibration guarantee or 80% accuracy claim is made.

## Cost and operational limits

No subscriptions, paid hosting or accounts are purchased. API plans determine access. Odds usage is quota-capped, data ingestion runs every six hours, and the dashboard checks prices/injuries every five minutes. GitHub schedules may be delayed. Account-level spending cannot be capped by application code; set provider billing limits to remain within the requested $0–$100/month budget. PostgreSQL and a continuously running API require a host if you choose to deploy the Docker stack.

## Current game markets

The homepage and Matchup Lab now use **actual The Odds API game prices**, not schedule-supplied estimates: moneylines (`h2h`), point spreads and full-game totals with both Over/Under prices. Each team/side retains its own line and American price; sportsbook source times are shown and older-than-three-minute quotes are flagged stale.

`Refresh NFL moneylines spreads and totals` checks every 15 minutes, but calls the provider only when its quota-aware `nextRefreshAt` is due. It requests the entire NFL slate in one game-market call. A low-credit key uses US books and a longer interval; enough credits allow US/US2 coverage and more frequent collection. The page reloads published game snapshots every minute. This is not a streaming live feed: GitHub schedules/publication can be delayed, and a low-credit plan cannot support continuous current pricing.

Set the repository Actions variable `GAME_ODDS_REFRESH_MINUTES` to an explicit interval (minimum 15 minutes) to override automatic allocation. This consumes credits faster and can exhaust a small allowance; no paid plan is purchased automatically. The workflow's manual **Run workflow** action forces a server collection. The website's **Refresh** button reloads published snapshots; it does not expose credentials or trigger provider calls. The Docker worker and FastAPI snapshot allowlist support the same game-market data. The last 96 collection batches are archived, capped at 8 MB.


### Public observations and game-outcome model

Verified public ESPN scoreboard listings supplement the quota-limited multi-book API. The workflow checks the schedule's upcoming NFL weeks approximately every 15 minutes, parses only explicitly returned moneylines/spreads/totals and labels the provider (currently DraftKings via ESPN). Public quote-update times are not supplied: `observed_at` records when the listing was read, while `last_update` stays null. A recent observation never becomes a fabricated provider-update timestamp. The pregame source field named `close` is not treated as proof of an actual historical closing price. Public endpoint availability and update latency are not guaranteed.

A separate conditional-outcome forest models joint home/away game scores using earlier scores, opponent scoring, team EPA/volume and rest with rolling 3/5/8-game features. No sportsbook market or target-game outcome enters its predictors. Expanding current-season tests hold out whole weeks, report score-margin/total MAE and home-win Brier against simple baselines, and retain the latest complete week separately. Current forecasts draw 10,000 joint score pairs per game, preserving empirical dependence. A model spread is the negative expected home margin; the projected total is a mean, while a book total is a wagering threshold.

Moneyline, spread-cover and over/under probabilities are evaluated directly against each returned book's actual price and handicap. Push-aware expected return and fair prices are shown under model details. Fair two-way moneylines assume a tie voids the wager; verify sportsbook rules. Game-market projections remain research: injury/weather effects are not independently calibrated, estimated ≥70% probability is not a validated hit rate, and passing one forecast gate is not approval of a bet. No game-market ROI or CLV is invented. The moneyline gate can fail independently of spread and total gates.


## Detail pages, logos and model-first presentation

Dashboard player names link to Player Research, matchup links open the exact Matchup Lab game, and NFL logos open Team Research. URLs carry encoded player/team/game/market parameters in the fragment so refreshes and new tabs resolve to the same detail view. Team Research includes current-season records, scoring/allowed trends, aggregated offense/defense rates, actual game results, upcoming matchups and skill-position player links. Statistics are collected from public nflreadpy schedules/team stats; current franchises take precedence over legacy relocated-team catalog entries.

Team logos use ESPN's public NFL image assets with text fallbacks and accessible labels. A displayed sportsbook favorite is derived from that specific book's moneylines (or matched primary spread sides), not from which team is home. Model favorites use the score model's win probabilities and remain separately labeled research.

The homepage leads with model-favorite player projections before bookmaker content. Larger model values, accent cards and clear projection headers provide visual priority; historical test error, predictive ranges, research labels and failed-gate warnings remain visible. Bookmaker lines stay available as secondary reference values, not as claimed sportsbook predicted averages.
