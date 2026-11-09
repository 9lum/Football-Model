# Receiving route/depth matchup layer

This adds modeled Targets alongside Receptions and Receiving Yards. Targets are a projection-only output; no unsupported sportsbook API market is requested.

## What is measured

Public nflverse play-by-play provides air yards, receiver, left/middle/right location, receptions, yards and EPA on targeted passes. These produce nine measured target zones: short (<10 air yards), intermediate (10–19), and deep (20+), crossed with left/middle/right.

These are targeted-pass profiles, not a charted route tree. Route-run shares for slants, curls, posts, corners, outs and go routes are unavailable and are not inferred from target depth. The field's optional paths are explicitly illustrative, not tracking data. Published route totals and YPRR remain in the existing receiving statistics section with their own source/sample scope.

## Matchup adjustment

- Core baselines use the existing position/opponent outcome forest and recent usage/scoring context. The receiving forest now jointly predicts Targets, Receptions, Receiving Yards and Receiving TDs.
- Route context uses only targeted passes from games completed before each forecast's kickoff. Current-season validation uses a prior-season league reference. No future game or current-game outcome enters the profile.
- Player exposure is weighted across the nine zones. Player efficiency and opponent yards/EPA allowed in each zone are shrunk toward matched prior-season league zone values (20 and 30 pseudo-targets, respectively).
- Minimum exposure is 20 current-season, current-team player targets across three prior games and 100 opponent targets, with recent samples within 35 days. Missing or stale evidence holds the baseline.
- Existing man/zone tendency and receiver-scheme inputs remain part of the core feature assessment. The new layer does not apply a duplicate man/zone boost. Historical labeled efficiency is shown with its potentially prior-season scope.
- Eligible positive/negative signals use bounded 5%, 10% or 15% adjustments. A zero adjustment is also allowed. Targets/Receptions share a volume coefficient; Yards has a separate coefficient. Deterministic unbiased integer rounding preserves count support, and Receptions cannot exceed Targets.

## Learning from mistakes

For each historical whole-week holdout, coefficient selection sees only earlier fully completed weeks, limited to the prior eight weeks. At least 200 eligible forecasts across 30 games are needed to select a learned coefficient; otherwise a 5% research warm-up is used. A nonzero learned coefficient must improve normalized earlier-week error by at least 1%; otherwise the layer selects zero.

The actual adjusted sample distributions are evaluated out of time. Applying the layer does not automatically pass a betting quality gate: incremental validation needs at least 500 eligible forecasts, 40 games, and ≥1% error reduction relative to the unadjusted core for that target. All other price, availability and probability gates still apply.

A separate verified pregame route experiment ledger retains both the adjusted projection and its unadjusted core baseline. Performance Lab has a distinct **Route / coverage experiment** evidence cohort; it is not pooled with original first-published projections or retrospective research tests.

## Player Research

WR/TE/RB profiles receive an interactive field panel with 3/6/9 targeted-game and season samples, keyboard/tap-selectable zones, color-coded depth bands, zone EPA/target, catch rates, yards/target and average depth. All percentages describe located targets. Flat and subtle 3D-tilt views are supported; illustrative paths are off by default.

The local route adjustment disclosure shows baseline versus current Targets, Receptions and Receiving Yards and two rationale sentences. Separately applied teammate-return allocations are identified.

## Refresh and limitations

A dedicated receiving-profile workflow refreshes actual chart data every six hours independently of slower model fitting. Model fitting and coefficient selection refresh with the existing public-model pipeline. If a public source fails, available cached data may be retained with its actual through-game date; stale matchup evidence is suppressed.

The layer is a testable research policy, not a guarantee of higher accuracy or a promise of automatic profitability. Team implied totals are not fabricated or silently inserted into historical tests without point-in-time price provenance. Actual route concepts remain unavailable until credible charting is provided.

## Quarterback field profiles

Player Research uses the same selectable nine-zone field for QB thrown passes.
The public profile job refreshes QB samples alongside receiving profiles every six hours.
QB samples use the current season or the last 3, 6 or 9 completed games with QB plays.
Field shares include only throws with known air depth and left/middle/right location;
aggregate completion rate and yards per attempt use all non-spike thrown attempts.
Scramble rate is scrambles divided by dropbacks, including sacks. Designed carries
are play-by-play non-scramble QB rushes, excluding kneels and no-plays. Their share
uses non-kneel QB carries, a different denominator from scramble rate. Missing rush
classification stays unknown. These are observed classifications, not inferred
playbook intent, and the new display does not add an unvalidated projection multiplier.
Depth mode projects the field, zones, yard lines and stadium tiers through an elevated end-zone camera. Flat mode uses overhead coordinates. Text stays screen-aligned and unfiltered in both views, with larger mobile percentages and depth ranges in the legend.

## Behind the line of scrimmage

Display profiles version 2 have twelve zones: negative air yards, 0–9, 10–19,
and 20+, each split left/middle/right. Negative-air-yard throws are rendered on
the near side of the yellow LOS. Zone percentages use located throws/targets;
additional catches/completions and their share use located receptions as their
denominator. No behind-LOS zero is inferred when locations are missing. This
is a display split; the original core model's nine-region feature construction
remains unchanged. Both Player Research and Matchup Lab use the same component.

## Completed Matchup Lab research

Per-game archives retain the latest model file actually committed before kickoff,
including original distribution draws, defensive inputs, roster context, available
pregame weather and recorded book/TD prices. The source commit and publication time
are retained. A chronological Git history recovery job runs every half hour and after
model refreshes; future archives persist by game. It does not regenerate forecasts
from final outcomes. Missing historical snapshots remain unavailable. Later box scores
can update the actual-history chart without changing the frozen forecast. Historical
quotes are ineligible as live bets. The whole-week display advances at midnight Tuesday
America/New_York only after every known game, including delayed Monday games, is final.

## Replacement starters and public designations

Current-week explicit OUT/INACTIVE/IR/PUP/NFI/suspension designations from scoped
Sleeper or recent ESPN reports exclude the player from default projections, while
retaining source/observation dates and distinguishing provider reports from official
confirmation. Practice DNP, Questionable, and missing reports do not mean Out.
Doubtful can display a conditional backup, never a confirmed absence. The next
available current depth-chart player is promoted for QB/HB/WR/TE; unavailable backups
are skipped. Expected replacements lead the displayed depth order and remain research
estimates until their changed role is validated.

Missing QB projections use the replacement's recorded starting-game production plus
a historical experience-matched QB-change cohort. Attempts use own starts and team
volume; completions/TD/interception rates shrink toward prior-season QB rates. QB
rushing uses the replacement's own starts and is omitted without support, rather than
inheriting the injured QB's mobility. Missing skill-player forecasts require at least
two recorded same-team games and use their own outcomes, without assigning the entire
absent player's workload. Existing forecasts remain their own player estimates.
Original data and sportsbook prices are not mutated; unavailable players do not
become automatic unders. Legacy archived forecasts retain their original designation
semantics, rather than being retrospectively replaced by new rules.

Public availability refreshes every 15 minutes independently of the full model job.
Sleeper's player dictionary is cached for an hour with original retrieval timestamps;
ESPN is checked each refresh. Collection-time resolution runs after retrieval so valid
reports collected a few seconds after the job began are not incorrectly rejected.
