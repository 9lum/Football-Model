# Public-data receiving model v0.2

## What is implemented

The Python engine downloads public nflverse weekly player statistics, PFR offensive snap counts through nflverse, a player-ID crosswalk and schedules. The optional SumerSports public WR/TE tables supply current route scenarios. No private endpoint, API credential or paywall bypass is used for statistics. Odds access remains separate: import current quotes or use the existing server adapter with your own supported odds subscription.

The statistical feed is weekly at the player-game level and normally refreshed nightly after game days, rather than once a week. The GitHub workflow checks every six hours. Retrieval timing, Last-Modified/ETag when supplied, and raw-file hashes are recorded. Those timestamps do not prove that every game has been published; inspect the evaluated weeks and latest source observations.

Public sources:
- https://github.com/nflverse/nflverse-data/releases/tag/stats_player
- https://github.com/nflverse/nflverse-data/releases/tag/snap_counts
- https://github.com/nflverse/nflverse-data/releases/tag/players
- https://github.com/nflverse/nflverse-data/releases/tag/schedules
- https://sumersports.com/players/wide-receiver/
- https://sumersports.com/players/tight-end/
- https://nflreadr.nflverse.com/articles/nflverse_data_schedule.html

Attribute nflverse and the upstream sources listed in each release. Public accessibility does not establish unrestricted redistribution/commercial-use rights; consult each dataset's license and provider terms for your intended use. This repository publishes derived research outputs; large raw datasets stay outside Git.

## Run

Python 3.11+ recommended; Node 20+ for browser-code checks.

```sh
pip install -r requirements.txt
python -m unittest discover -s tests -v
node --test tests.mjs tests/market.test.mjs
python -m edge.pipeline --season 2026 --start-season 2021 --output data
```

Use the actual NFL season year, not the calendar year for January/February games. A missing current-season feed fails explicitly. There is no silent fallback to old statistics. The existing NFL.com scraper remains optional and is not the primary modeling feed.

Outputs:
- `data/latest.json`: forecast distributions, feature values, sources and current-season evaluation.
- `data/validation.json`: weekly evaluation and latest fully completed week holdout.
- `data/oos-predictions.json`: per-player/game out-of-sample point predictions and actual outcomes for auditing.
- `data/snapshots/sources.json`: raw source hashes and retrieval metadata.
- `data/snapshots/sumer-<timestamp>.json`: dated route-table snapshots, including explicit source failures.

The GitHub workflow **Public-data model and current-season tests** downloads, trains, tests and publishes these outputs every six hours, on engine changes, or manually. A failed run does not replace the previous successful model. Reports remain date-stamped; stale projections cannot qualify as candidates. Workflow commits require the repository's Actions write permission. If repository policy blocks publication, download the workflow artifact and import `latest.json` into the page. Never add a personal token to HTML or source.

## Model and current-season testing

A 96-tree conditional-outcome forest learns the joint distribution of receiving yards and receptions. It samples observed outcomes from training-tree leaves rather than pretending that variation between tree means captures all game uncertainty. Multi-output samples retain yards/receptions dependence for each player, but do not model dependencies between players or games.

Inputs use earlier games only: 3/6/12-game targets, catches, yards, air yards, YAC, offensive snaps and snap share; lagged aDOT, catch rate, YAC per catch, target share, usage and snap trends; prior opponent yards/targets allowed; home/away, week, days since appearance and prior team change. Snapshot dates and final scores are not predictors. Missing-feature imputation is fitted on training data only. Missing route counts are not replaced with snaps or invented values.

Offensive snap rows add active zero-target games using an unambiguous PFR-to-GSIS ID crosswalk. No-snap/DNP rows are not assumed to be zero receiving games. Unmapped offensive snap rows are reported. Forecasts are conditional on participation, which requires current availability review. Cold starts with fewer than three prior observed games are excluded; new signings, trades after the last appearance and inactive players can require manual corrections.

For each observed week of the requested current season, fit on earlier seasons plus earlier weeks, excluding the whole tested week. Report the latest fully completed week separately; identify partial weeks explicitly. Hyperparameters are fixed in source and not selected using that final week. Refit on completed games for upcoming forecasts after evaluation.

Report MAE versus a six-game rolling baseline, CRPS, 80% interval coverage/width, and Brier/reliability at fixed prop-like thresholds. Fixed thresholds are not historical sportsbook lines. Historical source files have final stat corrections, so this is a reconstructed chronological evaluation, not proof of point-in-time tradability. No current-season result is claimed until an actual public-data workflow succeeds.

The forecast quality gate requires at least 500 test observations for each market, lower MAE than the rolling baseline, and 70–95% coverage for nominal 80% intervals. These are heuristic research gates, not statistical proof of profitability. There is no guarantee the model passes them.

## Advanced route scenario

SumerSports' current route aggregates are **never inserted into historical backtests**. Full-name profile slugs and team must uniquely match. Missing/old/future timestamps, unavailable table markup, mixed result coverage or inconsistent target/route rates disable the scenario. WR and TE are supported; the public RB table does not supply this route schema.

The scenario estimates route volume from season routes per observed game and recent snap-share changes. It combines observed targets per route, shrunk catch rate, game-level target dispersion, and a completion-depth estimate distinct from target aDOT, plus observed YAC per catch. This remains heuristic, with no claim of historical calibration. Different providers can disagree in attribution, which intentionally suppresses some matches. Scenario parameters have not been optimized on betting returns.

## Market comparison

The standalone page accepts The Odds API event JSON or manual prices. `edge.markets.scan` offers the equivalent Python scanner. Match exact event home/away teams, kickoff within one hour, exact full player name, market, line and side. No-vig estimates require both sides of the same line at the same book. Push probabilities remain separate at integer lines.

EV per unit = P(win) × (decimal odds − 1) − P(loss). Conservative EV additionally subtracts a sensitivity haircut based on observed out-of-sample calibration error and sampling uncertainty. This is not a valid guaranteed confidence bound. Candidate labels require the quality gate, odds age ≤180 seconds, model age ≤48 hours, future kickoff, current availability confirmation, positive route-scenario EV, and conservative EV ≥3%.

Manual prices have user-entered timestamps, not verified sportsbook provenance. Candidate labels on such quotes remain research outputs. No parlay probability multiplication, staking, automatic bets or guaranteed edge is provided. ROI, CLV, drawdown and profit confidence intervals require historical point-in-time odds and settlement data that are not bundled for free.

## Open the page

Download `site-preview.html` and open it in your browser. It loads the latest successful `data/latest.json` from this GitHub repository, or accepts a downloaded bundle. The same page includes current-season tests, upcoming forecasts, route scenarios and a price comparison tool. Build it after template changes with `node scripts/build-preview.mjs`.

`worker/index.js` remains the earlier server-backed scenario lab and odds adapter. It does not automatically serve the new Python model. The standalone page is the interface for this v0.2 engine. Neither page has been newly deployed to hosted Sites by this change.

## First verified run

[Run 42154889123](https://github.com/9lum/Football-Model/actions/runs/42154889123) completed successfully and published real current-season results. See [RESULTS.md](RESULTS.md). This verifies data retrieval, model fitting, evaluation and output publication; it does not establish profitable sportsbook edges or browser visual QA.

## v0.3: position models, statistics and history

The redesigned UI loads schema v3. `players` contains QB/RB/WR/TE basic season, per-game, last-five and last-game statistics plus actual current-season game histories. `forecasts` contains eligible upcoming players with `marketSamples` keyed by supported sportsbook identifiers. Legacy v2 bundles remain readable in the page, with fewer statistics.

Separate receiving (WR/TE/RB), rushing (RB/QB), and passing (QB) forests cover the 11 market types described in README. Each family includes position-relevant lagged opportunity and efficiency, offensive snap trends, and opponent/team context. EPA and CPOE are lagged when published. Targets are standardized for fitting so yardage does not overwhelm count outcomes in multi-output tree splits. Sampled outcomes remain in their original units.

Cohort rules are based entirely on prior usage: at least three previous observed games and a last-three-game average of at least one target for receiving, two carries for rushing, or ten attempts for passing. The rules and tested positions appear in each family report. Bench-player and DNP outcomes are not mislabeled as starting-player forecasts. Basic profiles still include players without eligible projections.

Each family is refitted and evaluated chronologically in the current season. Each market has an independent gate: at least 500 test observations (200 for passing markets), lower MAE than the six-game baseline, nominal 80% interval coverage between 70% and 95%, and complete current-season game coverage. Gates are heuristics, and some count markets can fail because discrete intervals overcover. A failing market remains visible as research and cannot qualify as a bet candidate.

The route-scenario agreement requirement applies to receiving yards and receptions. Other markets use their own learned distributions, calibration sensitivity checks and gates. No unsupported route-based touchdown distribution is invented. The official receiving-yards API key is `player_reception_yds`; the previous `player_receiving_yards` import alias is accepted for compatibility.

Historical charts show actual player results. Any current book line is explicitly a reference overlay, not an archived historical quote. The reasoning panel explains opportunity, efficiency, matchup context and the win probability needed at a specific price. It states when value is negative, disappears under sensitivity checks, or conflicts with the route scenario. These contextual signals are not a causal decomposition of a forest prediction.

Basic ratios are calculated from aggregate denominators (for example, season completions divided by season attempts), rather than averaging weekly percentages. Missing source fields remain null. Recorded stat games are not asserted to be the official games-played total. Weather, real-time injuries, coverage assignments and future game state are not fabricated. No claim of a globally optimal or profit-proven model is made.
