# First verified public-data evaluation

[Successful GitHub run](https://github.com/9lum/Football-Model/actions/runs/42154889123) · [Detailed evaluation](data/validation.json) · [Auditable out-of-sample predictions](data/oos-predictions.json)

Model generated November 5, 2026 at 10:10 p.m. Toronto time; run completed at approximately 10:13 p.m. It trained using public data from 2021 onward and evaluated each observed 2026 week with that whole week excluded from training. No current-season route aggregates were used in historical folds.

**2,513 player-game observations across weeks 1–8.** These are correlated observations, not 2,513 independent NFL games.

| Market | Model MAE | Six-game baseline MAE | Nominal 80% interval coverage |
|---|---:|---:|---:|
| Receiving yards | 15.524 | 15.813 | 85.87% |
| Receptions | 1.2265 | 1.2297 | 91.17% |

Lower MAE is better. The gains are small: approximately 1.82% for yards and 0.26% for receptions. Overcoverage suggests conservative/wide predictive intervals, especially for discrete receptions. No statistical significance or betting ROI is claimed.

## Separate final holdout: week 8

304 tested player-game observations, trained on 29,348 earlier observations.

| Market | Model MAE | Six-game baseline MAE |
|---|---:|---:|
| Receiving yards | 15.122 | 15.183 |
| Receptions | 1.1822 | 1.1759 |

The model was slightly better for yards and slightly worse for receptions in this final week. Hyperparameters were not selected using week 8. All configured forecast-quality gates passed, but these heuristic gates do not prove a betting advantage.

## Data and upcoming forecasts

- 386 upcoming projections; 221 had fresh, uniquely matched route scenarios.
- SumerSports WR/TE pages reported November 5 at 7:14 p.m. Toronto time.
- Latest observed player statistics covered week 8.
- Snap data added 4,318 active zero-target rows across the training/evaluation period; 57 skill-position snap rows could not be mapped by player ID.
- No completed schedule games lacked player rows in this run.
- Availability is unconfirmed by default. A recent appearance is not proof that a player remains active or on the same roster.

The outputs are now published in `data/`. Future successful refreshes replace the current reports; this document describes the first run only. There are no historical sportsbook prices in this evaluation, so ROI, CLV and profitable unseen edges remain unverified.
