# Game market movement

Odds Monitor (`platform/#odds`) opens with game moneylines, spreads and total-points O/U prices for every collected book feed. Choose a matchup, book, market or recorded-change window. The existing player-prop movement tools remain below it.

`game-market-movement.json` stores real first observations and later price or point-line changes. It is seeded once from the existing native game-odds snapshots, then updated by native/public collectors and the final pregame collector. Identity includes both teams, exact kickoff, provider, book, market and outcome. Different providers are not joined into a fictitious movement series. Repeated identical quotes do not become new changes. Older provider timestamps cannot manufacture a reversal. The bounded public archive retains at most 45 days / 6,000 changed quotes.

Line deltas use points; price deltas use raw implied-probability percentage points to avoid misleading jumps across negative/positive American odds. They include bookmaker margin. When the line moves the contract changes; these deltas are not a model edge. History charts show posted price probability and point line separately. No claimed sportsbook opening or closing quote is backfilled.

The browser reloads current game odds every minute and loads/polls movement history only while Odds Monitor is open. Public ESPN observations run about every 15 minutes. Native sportsbook collection remains quota-aware, preserves kickoff reserves, and uses the existing repository secret. No browser API key is exposed. Provider update timestamps, listing observation timestamps and historical change times remain separate. Quote freshness uses a three-minute provider-time screen, or a twenty-minute public-listing observation screen; stale/unknown quotes remain visibly marked. These are snapshots, not a continuous streaming feed or guaranteed current executable prices.

Validation: `node --test web/game-odds-movement.test.mjs`; `python -m unittest scripts.test_game_market_history scripts.test_game_odds scripts.test_public_game_odds scripts.test_kickoff_refresh`.


## Monthly sportsbook-credit policy

The existing Odds API key stays in Actions secrets; it is not rotated or automatically upgraded. Each collector checks provider-reported credits before paid requests. Core pregame yardage and touchdown markets are prioritized across games remaining in the cycle. Routine previews use only a capped share of surplus; refresh-budget overrides cannot bypass that protection. Free public game lines remain independent.

If the billing date is unknown, the policy uses a conservative 31-day estimate, explicitly labelled as an estimate rather than the provider's renewal date. A reported balance replenishment restarts pacing automatically. An optional Actions variable `ODDS_API_RESET_AT` can supply the actual next renewal as an ISO timestamp with timezone. No credentials are written to public snapshots.

A 500-credit plan cannot support every market at every sportsbook continuously. Expect narrower paid coverage, prioritized near kickoff. Larger reported allowances permit broader coverage. Per-collector `data/odds-quota-*.json` files and snapshot `monthlyQuotaPolicy` fields record the allocation and balance observations.
