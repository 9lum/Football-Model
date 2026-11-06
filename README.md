# Route Edge — NFL receiving research baseline

Implemented: a private-dashboard Worker, receiving yards / receptions simulation, exact-line over/under comparisons, no-vig probabilities, pushes, estimated EV, snapshot imports, and configured feed polling every 60 seconds while the tab is open. Integer yards and receptions retain push probability. No current player statistics or odds are fabricated.

## Connect data
Set server runtime secrets ODDS_API_KEY (The Odds API), STATS_FEED_URL (a licensed normalized statistics endpoint) and optional STATS_FEED_TOKEN. Redeploy after configuration. Do not put credentials into HTML or source. The Data connections page downloads the required JSON format. Bookmaker coverage depends on the subscription, event, market and jurisdiction; the API cannot guarantee all major books.

https://the-odds-api.com/liveapi/guides/v4/
https://the-odds-api.com/sports-odds-data/update-intervals.html
https://nflreadr.nflverse.com/articles/nflverse_data_schedule.html
https://sumersports.com/football-analytics-definitions/

nflverse participation from 2023 onward is provided after the postseason, so it is unsuitable for live route counts. License an in-season route provider and normalize it to the documented contract. Real-time means provider-limited polling here, not a tick-by-tick streaming guarantee.

## Continuous collection
Run `python collector.py` on an always-on host with the same environment variables. Python standard library only. It polls upcoming events within LOOKAHEAD_HOURS (default 48), stores timestamped raw odds and normalized statistics in SQLite, and backs off on errors. POLL_SECONDS defaults to 60; EDGE_DB sets the local database path. It consumes API quota per event, market and region; choose the cadence and window for your subscription. This process has not been started and does not run merely because the dashboard is deployed. Use a process manager with restart and disk monitoring for production. SQLite is local, so use durable disk and backups. Respect feed licenses.

The collector archives movement; the dashboard currently shows changes seen within the current tab. Connecting historical movement charts to that archive is future work. No automated bets, alerts, or background service have been activated.

## Model limits
This is an untrained, pregame research baseline, not a validated profitable model. Priors, variance and shrinkage strengths are heuristic. aDOT + YAC is an approximation for completion yards, which requires fitted completion-depth distributions for production. No opponent, weather, injury, coverage, rushing, passing, touchdown or game-level model is implemented. Use the method tab's walk-forward validation plan before relying on projected EV. No verified unseen edges or backtest returns are claimed.

## Verify and deploy
`node --test tests.mjs` checks odds conversion, probabilities, pushes, opportunity monotonicity and API failure behavior. `python -m py_compile collector.py` checks collector syntax. Feed integration tests require real credentials. Browser QA was unavailable in the authoring environment.

Worker entry: worker/index.js. Build artifact: dist/server/index.js and dist/.openai/hosting.json. The private Sites identity is excluded from this public repository. Configure a fresh hosting manifest when deploying to Sites, or point your Worker hosting platform at worker/index.js. Source push/publication was blocked by an unreachable configured proxy during authoring; no successful deployment is claimed.
