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

## Auditable weekly forecast outcomes

`edge.audit` reads a clean, tracked previous model bundle before it is replaced. The publication time is derived from `git log` for that exact file, rather than the model run-start time. A source commit must exist and precede kickoff. For each game/player/market, the first archived projected mean and range are retained unchanged in a per-season ledger. All archived projections are retained, including research markets, to avoid selecting only favorable results.

Outcome joins use game ID, GSIS player ID and the market’s stat target. Published numeric zeroes are valid results; absent player outcomes are not converted into zero. DNP and sportsbook settlement rules require separate review. Current public stat corrections can update actuals, while original projected values and provenance stay fixed.

The Results page separates these committed pregame forecasts from reconstructed historical walk-forward tests. It reports projected values, actuals, actual-minus-projected errors and mean absolute error by selected market/week. It does not reinterpret closeness to a continuous point estimate as a betting win rate.

## Defensive feature candidates and injury scenarios

Defensive context is derived from nflverse play-by-play; historical participation/charting adds coverage, pressure and rusher-count labels when supplied. Valid dropbacks exclude no-play penalties. Rushing context excludes kneels. Opponent last-six-game aggregates are joined strictly before target kickoff. Contact rate combines sacks and QB hits and is deliberately not called pressure rate.

Coverage priors for a season use only the previous season’s completed charting. Receiver yards per target versus man/zone are shrunk toward that prior season’s league rate using 30 prior targets. Current Sharp Football man/zone percentages are timestamped and applied only to upcoming forecasts, never to earlier current-season test games. Unclassified coverage is retained as a residual rather than renormalizing percentages or inventing zeroes. Fresh-current coverage substitutions are forward inputs, not a separately established betting edge.

Each family compares the basic and enriched defensive feature sets using the previous season as development data, with training limited to still earlier seasons. Enrichment is selected only for at least a 1% improvement in average normalized point error there. Current-season outcomes and its final-week holdout are not used for that feature choice. A feature’s availability alone does not establish predictive value. The chosen family and development scores are recorded in the evaluation.

Current depth and public trades remap upcoming team assignments without changing past player histories. A fresh conflicting roster suppresses an old-team projection. Unlikely backups are hidden, while meaningful rotation usage and expected replacements remain available. Depth listings are not asserted to be final gameday lineups.

The separate public availability snapshot retains official/secondary source distinctions, applicable season/week, practice status, game status and observed timestamps. Official source conflicts stop automatic ruled-out inference. Absence from an injury list never confirms active status. Statuses from the wrong week cannot rule out a later game.

QB replacements use recorded regular-season starting IDs from public schedules, with recent production from 2021 onward. Historical QB-change cohorts are fit only on earlier seasons; experience counts can include completed current-season games. Observational experience groups require at least 15 examples before a group ratio is used. A backup with its own start history is partially pooled toward its own recent production rather than assigned a universal discount. The team yardage scenario is explicitly unvalidated; non-yardage outcomes are not mechanically scaled. Conditional alternatives are offered for uncertain starters without making up participation probabilities.

Numeric model fair odds are recomputed from the current scenario’s win/push probabilities at a supplied line. They are estimates and never overwrite a sportsbook quote. Confirmed game absences suppress prop evaluation rather than becoming zero-stat winning unders. Injury-adjusted scenarios are excluded from validated-candidate and weekly-shortlist qualification; original baseline forecast audits remain separate.

The professional platform adds a **70% estimated unconditional win-probability selection threshold** to candidate labels. Forecast accuracy and probability calibration remain separately measured; this is not a guarantee or a relaxed validation gate. Rolling windows include 3/5/6/8/12 games. Public game-week NGS is joined by GSIS ID/season/week and shifted before use; week-zero season aggregates are excluded. RMSE, fixed-threshold log loss and ≥70% pooled cohort diagnostics supplement MAE/CRPS/Brier. LightGBM/XGBoost challengers remain research until their distributions and calibration are independently validated.

### Opponent and position adjustment (v0.4)
Every player outcome family now receives opponent allowances specifically against
that player's QB/RB/WR/TE position. Features cover targets, receptions, receiving
yards/TDs, carries, rushing yards/TDs, pass attempts/completions, passing yards/TDs
and interceptions. They include the preceding 3/6 games, the current season,
three-game league shrinkage, matched-sample efficiency and an allowance residual
relative to each previously faced offense-position group's preceding six games.
Only games strictly before the prediction's kickoff enter these features.
Published games with no opportunities for a position remain genuine zeroes;
unpublished games are not filled in. Positional allowances are totals for that
position group in a game, not a suggested projection for one player.

Points allowed uses actual opponent team scores. Direct positional touchdown
points count six times rushing plus receiving touchdowns; passing TDs remain a
separate QB outcome and are not double-counted as points scored by the QB.
Final/current-game scores never enter that game's predictor row. Game-score
models also retain their existing opponent points-against and defensive EPA
inputs. Historical descriptive statistics remain actual results.

These features enter fitted outcome distributions, not a hand-picked percentage
boost. Current-season walk-forward error, interval coverage and all existing
bet-qualification gates are recomputed on refresh. Extra context does not ensure
better accuracy or a profitable bet. Public historical files include corrections,
so the tests still do not reconstruct archived pregame data vintages.

### Weekly Anytime Touchdown Lab
`edge.touchdowns` analyzes every game in the current regular-season week, using
four prior published team games for opportunity and six prior games for defense.
Rushes and targets are mapped by GSIS ID; goal-line/red-zone shares, actual RZ
touches, expected TDs and direct positional scoring remain distinct. QB passing
TDs never count as an Anytime TD outcome. Return and fumble-recovery scores are
outside this offensive model; sportsbook settlement rules still matter.

Distance/type/position xTD conversion is fitted on seasons before the current
season with 30-opportunity smoothing. A regularized logistic player-game model
uses lagged opportunity, shares, scoring and defense, evaluated on expanding
whole weeks of the current season. Brier/log loss and calibration are published;
this is not a historical betting ROI test. PFF grades, ESPN win rates, adjusted
line yards and current slot/perimeter charting are explicitly unavailable rather
than approximated or invented. Team implied points are snapshot context, not a
points/7 touchdown projection. Potential game-script shifts are conditional.

`.github/workflows/touchdowns.yml` refreshes analysis every six hours and after a
successful main-model refresh, automatically selects the current week, and saves
JSON plus a readable Markdown report. The Odds API collector requests the real
`player_anytime_td` Yes/No market with repository secret `ODDS_API_KEY`; its
initial all-game collection and later rotation respect the shared free quota.
Optional repository variable `ATTD_REFRESH_CREDIT_BUDGET` overrides each run's
credit budget. Existing timestamps are retained and stale prices never qualify.
The user's >=70% win rule and all quality, availability and sensitivity checks
remain required. 'Core' is a relative research ranking, never a guarantee.

### Final pregame refresh policy
`Final pregame stats and touchdown markets` checks the schedule every five
minutes without paid odds calls when no game is within 45 minutes. A worker
prepares public-data analysis about 26 minutes before kickoff, rechecks scoped
injuries/depth and current-season stat/PBP/trade source hashes at T−9, and targets
a final six-market US-region odds request at T−6m30s. The publication deadline is
T−5 minutes. ATTD, first TD (`player_1st_td`), last TD, moneyline, spread and total
share this request. First/last TD are prices only, not modeled scoring-order
probabilities. Routine collectors protect an allowance for six markets per game
through the remaining calendar month; insufficient quota is explicitly reported.

The worker records actual Git push completion, individual source update times,
missing markets, source-change checks and deadline success in
`data/kickoff-refresh.json`. Retained markets keep their old timestamps even if
another market from the same book is newer. A statistics revision or failed source
check withholds qualification rather than silently passing an old prediction as
fresh. Public sources may not have published new stats or confirmed inactives;
missing premium/charting data does not become available through extra polling.

This is a best-effort scheduled target, not a five-minute SLA: GitHub Actions can
start late, providers can time out or withhold timestamps, and shared API usage
can exhaust quota. The UI marks late, partial or unconfirmed refreshes and polls
the small audit snapshot every 15 seconds around kickoff, loading larger odds
files after publication changes. An always-on externally hosted scheduler with
adequate API allowance would be required for tighter timing guarantees.

### First/last touchdown model fair odds
`edge.td_order` trains separate regularized scorer-order classifiers on the actual
first and last touchdown scorer in each game. Defensive and return scores are
included when identifying scoring order, so the next offensive scorer is never
misclassified as first. Lagged opportunity features and prior first/last rates
are shifted before kickoff. Each market is evaluated using complete-week
current-season holdouts against a position-frequency baseline. First/last player
probabilities are capped by ATTD probability and a training-derived game mass
budget, retaining residual mass for unmodeled scorers and no-touchdown games.
These are distinct estimated probabilities, not a reuse of the ATTD probability.

`allPlayerOdds` indexes every database/depth-chart player. Upcoming, eligible
players receive model fair odds for all three TD markets. Missing current games,
sparse histories and ruled-out players are labeled unavailable; probabilities
are never fabricated to fill the grid. The UI matches the exact player/game,
uses the same font and size for each model/book pair, and distinguishes them
by weight. First/last remain visually secondary to ATTD and are research-only
until separate pricing, availability and qualification requirements are met.
