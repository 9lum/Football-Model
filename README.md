# Projections n Shit — NFL player stats and price comparisons

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

The first receiving-only v0.2 run succeeded and is documented in [RESULTS.md](RESULTS.md). The v0.3 refresh also completed successfully: it published 316 eligible upcoming player projections and evaluated all 11 market types. Nine markets passed the configured accuracy gates; rushing touchdowns and passing interceptions did not. See the v0.3 section in [RESULTS.md](RESULTS.md). Its populations differ from v0.2, so the earlier results cannot be presented as its performance.

Expected value uses win, loss and push probabilities. Reasoning describes observed signals and model-price differences, not causal feature attribution. It explicitly reports negative value or disagreement. Manual prices are unverified. Historical price backtesting, verified profit, optimality and guaranteed edges are not claimed. Forecasts assume participation; check current availability, trades and sportsbook rules.

No new hosted deployment is implied. `site-preview.html` is the redesigned interface. The legacy `worker/index.js` remains a separate server-backed scenario lab/odds adapter. No credentials or private Site identity are included here. Browser visual QA was unavailable in the authoring environment; software and end-to-end fixture checks are provided.

## Weekly shortlist and projections vs. actuals

The front page now shows one primary yardage projection per position in a concise weekly shortlist. It requires at least four current-season out-of-sample tests for each player, a passed market gate, fresh forecasts and a future game in the nearest forecast week. Ranking combines player-level past error and relative forecast uncertainty within each position. It is not a guaranteed pick or a claimed win probability, and it does not require sportsbook prices.

Open **Results** for per-player projected values, actual statistics and signed errors. The dataset selector separates **Published before kickoff** from **Historical walk-forward tests**. Latest results are selected by default; position, team, opponent and week filters also apply.

The refresh workflow freezes the first archived forecast from the previous committed model bundle, using the file’s Git publication timestamp and commit SHA. A projection published after kickoff is never retroactively recorded as a pregame call. Archived values are never overwritten by later model updates. Once public actual statistics arrive, results update automatically. Missing player outcomes remain pending rather than being assumed zero.

The first archived forecasts may still be awaiting their games. The existing historical tests are available immediately in the other dataset. Forecast ledgers are saved by season in `data/forecast-ledger-<season>.json`; `data/projection-results.json` contains their current outcome status. The 80% range is an uncertainty interval, not a claim of 80% accuracy. No new accuracy target was imposed.

## Current injuries, starters, roster moves and matchup context

The site is named **Projections n Shit**. Teams are selected from an always-visible list in the Teams view. Starting and expected replacement players lead each position. Unlikely backups and inactive players are hidden by default; the + panel can reveal them for research. All shows up to 16 featured primary-yardage projections, while a position filter shows up to eight. Fewer appear if injury, roster, testing or freshness checks leave fewer eligible choices. These are model-ranked projections, not guaranteed wins or measured public betting popularity.

The availability workflow reads official NFL injury reports, public club injury-report pages and ESPN’s public injury endpoint when accessible. It preserves sources and retrieval times, distinguishes practice participation from game status, displays Questionable/Doubtful, and rules players out automatically only when an applicable official designation supports it. Conflicting, stale or unconfirmed news requires review. A DNP practice report is not treated as a game absence or an automatic winning under.

Depth charts come from ESPN via nflverse. Public nflverse trade records are cross-checked with depth information; draft-pick assets are not mistaken for player trades. Current roster moves affect upcoming team assignments only, never historical test rows. Old-team projections are suppressed when a fresh roster contradicts them.

If a starting QB is officially out, a separate replacement scenario blends the backup’s recorded starting-game production with an experience-matched historical QB-change cohort. Questionable/Doubtful QBs offer an explicit “if backup starts” preview. Experienced former starters do not receive the same blanket assumption as inexperienced backups. These observational scenarios adjust passing/receiving yardage distributions and model fair odds at a quoted line; they are not a calibrated injury model and cannot qualify as validated picks. No arbitrary probability of playing is inferred from a designation.

Availability refreshes hourly, plus every 15 minutes during the configured Sunday window. GitHub schedules can be delayed. The page checks published availability every five minutes while open. Actual sportsbook prices remain supplied by your odds feed/import and are not rewritten. `data/availability-history.json` records recent status and QB-scenario changes. Archived Results continue to track the original baseline forecasts, separately from subsequent injury scenarios.

The model now evaluates defensive passing/rushing EPA and success allowed, sack/contact rates, explosive-play allowance and labeled pressure/rusher counts where available. It uses prior-season charted man/zone rates and receiver coverage splits for historical tests. Fresh public Sharp Football coverage mixes may update upcoming-game inputs only. Missing charting stays missing; QB contact is not mislabeled as full pressure. See MODEL for selection and timing limits. These details remain off the front page.

## Automatic sportsbook snapshots

The `Refresh sportsbook odds` Actions workflow uses the repository secret `ODDS_API_KEY`. The published site automatically loads `data/odds.json`; Compare shows connection status, coverage and collection time. No key is sent to the browser. Provider response data is published to this public repository. Manual imports still work.

Collection runs on initial workflow changes, manually, and approximately every six hours (GitHub schedules may be delayed). It requests pregame NFL props up to eight days ahead, prioritizing modeled events least recently collected. The budget defaults to 80% of reported remaining credits spread over 120 refreshes, capped at 120 credits per run. Small budgets request only US primary-yardage markets (or one rotating yardage market); larger budgets request 11 modeled markets in US and US2. At most eight events are requested per run; books and props appear only when returned by the provider. Set the repository Actions variable `ODDS_REFRESH_CREDIT_BUDGET` to a per-run credit cap to override automatic allocation, still capped at 120 and available credits. Raising it consumes the subscription faster.

A bounded `data/odds-history.json` retains the latest 28 successful collection batches for future movement analysis. Older quotes keep their original provider timestamps; the scanner's three-minute stale-price gate remains in effect. This is scheduled snapshot collection, not continuous live odds. Public snapshots require a plan permitting your use/display of the data; see https://the-odds-api.com/liveapi/guides/v4/.
