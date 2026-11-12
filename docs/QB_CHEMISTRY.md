# Quarterback chemistry research policy

Current ESPN/nflverse depth charts and the public trade ledger determine roster placement. Depth rows whose names disagree with the nflverse GSIS identity registry are rejected. Provider aliases are consolidated by player ID or ESPN ID, never by name alone.

The availability job refreshes the chemistry context every 15 minutes using the latest public weekly player statistics from 2021 onward. A qualifying QB-linked game requires a scheduled starting QB with at least 15 attempts and 80% of team attempts. These are starter-linked game splits, not exact passer-to-receiver target charting. At least three shared starts, twelve shared targets and three comparison starts are required.

Target share, catch rate and yards per catch are compared with the player's other quarterbacks. Observations have a two-year recency half-life; shared and comparison samples shrink toward no change with eight- and five-game priors. Recent same-QB usage discounts the incremental effect already present in the base model. Receiving changes are capped at 15%; target allocation is conserved across adjusted players within a team. Sparse TD splits are not independently fitted: the receiving-opportunity change carries through to receiving TD samples. QB passing totals reflect aggregate receiver changes, capped at 10%; QB rushing is unchanged. Anytime, first and last TD model prices are recomputed while retaining scorer-competition constraints.

The browser applies this policy only to future games with fresh, matching-model availability snapshots. Saved historical forecasts and sportsbook prices remain unchanged. Adjusted markets are research and fail the betting validation gate until an out-of-sample evaluation supports promotion. Historical splits do not prove a causal effect or improved prediction accuracy.

A fresh expected starter without a full model forecast receives a labeled research forecast based on his own starting history and the existing experience-matched QB-change cohort. Without sufficient team history, no forecast is invented. This covers trades that remove a veteran from the prior team's upcoming model row. The current depth listing is an expected lineup, not confirmation of game-day activation.

Matchup Lab defaults to the active NFL week. The week selector exposes available current and archived weeks; choosing a game retains the selected week in its URL. Future weeks stay hidden under the existing Monday-completion/Tuesday-rollover policy.
