# Game market movement

Odds Monitor (`platform/#odds`) opens with game moneylines, spreads and total-points O/U prices for every collected book feed. Choose a matchup, book, market or recorded-change window. The existing player-prop movement tools remain below it.

`game-market-movement.json` stores real first observations and later price or point-line changes. It is seeded once from the existing native game-odds snapshots, then updated by native/public collectors and the final pregame collector. Identity includes both teams, exact kickoff, provider, book, market and outcome. Different providers are not joined into a fictitious movement series. Repeated identical quotes do not become new changes. Older provider timestamps cannot manufacture a reversal. The bounded public archive retains at most 45 days / 6,000 changed quotes.

Line deltas use points; price deltas use raw implied-probability percentage points to avoid misleading jumps across negative/positive American odds. They include bookmaker margin. When the line moves the contract changes; these deltas are not a model edge. History charts show posted price probability and point line separately. No claimed sportsbook opening or closing quote is backfilled.

The browser reloads current game odds every minute and loads/polls movement history only while Odds Monitor is open. Public ESPN observations run about every 15 minutes. Native sportsbook collection remains quota-aware, preserves kickoff reserves, and uses the existing repository secret. No browser API key is exposed. Provider update timestamps, listing observation timestamps and historical change times remain separate. Quote freshness uses a three-minute provider-time screen, or a twenty-minute public-listing observation screen; stale/unknown quotes remain visibly marked. These are snapshots, not a continuous streaming feed or guaranteed current executable prices.

Validation: `node --test web/game-odds-movement.test.mjs`; `python -m unittest scripts.test_game_market_history scripts.test_game_odds scripts.test_public_game_odds scripts.test_kickoff_refresh`.
