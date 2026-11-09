# Performance Lab

This replaces the former three-market Model Record interface. The original source records remain available as research inputs; they are not discarded or rewritten to manufacture a better record.

## Coverage

The scorecard lists 23 modeled or derived outputs:

- Twelve player projections: targets, receiving yards, receptions, receiving touchdowns, rushing yards, rush attempts, rushing touchdowns, passing yards, pass attempts, completions, passing touchdowns and interceptions.
- Three combined expectations: rushing + receiving yards, rushing + receiving touchdowns, and passing + rushing yards. Components must belong to the same player/game/issue time. Means and observed values may be summed; uncertainty intervals are not added.
- Home points, away points, game total and home winning margin.
- Home-win moneyline probability, Anytime TD, first TD and last TD.

Advanced inputs such as aDOT, yards per route run, coverage, defensive matchup statistics and injury reports remain model inputs. They are not assigned invented accuracy records when the model does not predict them as outputs.

## Two evidence cohorts

**Archived pregame forecasts:** Player-stat records retain the first published projection, actual public Git commit and publication time. Older game/TD records preserve original model-issue snapshots and are identified as snapshot research rather than independently verified wager logs. Forecast values do not change as official outcomes arrive. Original published player forecasts must precede kickoff.

**Walk-forward research:** Chronological whole-week tests use final-corrected public data. These are reconstructed research experiments, not previously published forecasts or bets. The exporter includes its actual rolling baseline and forecast quantiles instead of recreating a baseline from later games.

The evidence selector keeps these cohorts separate. No combined MAE is computed across yards, attempts, touchdowns and probabilities.

## Metrics

- MAE: mean absolute difference between projection and actual, in the statistic's native units.
- RMSE: square root of mean squared error.
- Bias: projected minus actual. Positive values indicate overprojection.
- Baseline skill: `1 − paired model MAE / paired baseline MAE`. Only identical rows with a recorded baseline enter this comparison.
- 80% range coverage: fraction of explicit observed results inside an archived 10th–90th percentile interval. This is not a betting win rate.
- Probability markets: Brier score, log loss, average predicted probability, observed event rate and 10-point calibration bins. The ≥70% cohort includes only positive-event probabilities at or above 70%; missing outcomes never become losses.
- Forecast counts and distinct game counts are both shown because player outcomes within a game are correlated.

## Actual results

Official nflverse weekly player statistics are preferred. Unresolved player outcomes may use explicitly listed final ESPN box-score values. Combined passing completions/attempts are parsed into separate fields. Absent statistics are not zero-filled.

Anytime TD means a player's own rushing/receiving touchdown; QB passing touchdowns do not count. A zero event requires confirmed scoring coverage and participation evidence. First/last touchdown order is graded only when every scoring touchdown can be resolved to a scorer. Unknown defensive/return scorer identities leave order markets unresolved. Final game scores require the provider's explicit completion flag. Tied games are excluded from binary moneyline grading, and moneyline probability conditions on no tie.

## Sportsbook comparisons

This view is independent of forecast-error evidence. It retains clearly labeled fixed-rule historical cohorts and adds player-prop comparisons when a single unambiguous line is captured before kickoff. The first recorded benchmark stays frozen. DraftKings is preferred, then FanDuel, then another deterministically selected book. Alternate-line ambiguity prevents capture.

No actual wager placement, ROI, verified closing-line value or proven profitability is implied. Missing lines or unresolved participation remain ungraded.

## Persistence and study

The public index is `data/model-performance.json`. Detailed records are split by season and evidence cohort under `data/performance/`. The interface requests relevant shards on demand and provides CSV export for a selected stat. Existing seasons remain in the archive as the live feeds move forward. Results refresh after the scheduled public scoreboard checks and after new weekly model/stat outputs are published.

## Homepage

The homepage uses responsive containers, consistent spacing and distinct projection/book sections. Every matchup in the current display week remains available. When current feeds omit a game, the board can reconstruct its last genuine quotes from `game-market-movement.json`, preserving original provider/observation timestamps. Recorded prices are never relabeled as streaming live odds. Missing quotes remain unavailable; model lines do not replace them.

An additional seed restores first/last TD forecasts for 14 games and 322 players from the genuine public pregame commit `8e5f2cc2804c6d2ae71929f0dc6a325de78b7c03` (November 6, 2026, 23:53:40 UTC). Its publication time, original probabilities and source commit are retained. Selection does not depend on which players later scored.
