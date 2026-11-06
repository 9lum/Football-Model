# NFL.com player statistics

Source: https://www.nfl.com/stats/player-stats/

Run `python nfl_stats.py --season 2026 --season-type REG --output data/nfl/2026/REG`.
Python standard library only; no API key or dependencies needed. Access may still fail if NFL.com blocks the host or changes markup.

The importer discovers category links from the passing table and follows each Next Page link. It preserves every displayed table column as a string, player profile URLs, source page URLs, season, season type, collection timestamps, row counts and page counts. JSON and CSV exports cover all discovered categories for the selected season/type, rather than only the first 25 rows. Missing tables, empty tables, repeated pages and schema mismatches fail explicitly. No success manifest is emitted until all categories have been retrieved. Use a fresh output directory for each manual run to avoid confusing older exports with new data.

Scope: all categories linked from the player-stats page, including passing, rushing, receiving, fumbles, tackles, interceptions, field goals, kickoffs, kickoff returns, punting and punt returns. This is not a pull of every historical season, weekly split, player profile or Next Gen Stats endpoint. Run additional years and REG/PRE/POST explicitly when needed.

## Automated exports
The GitHub Actions workflow runs on importer/workflow changes, hourly at minute 17, and manually from the repository Actions tab. Manual runs can select season and season type. Download the `nfl-player-statistics-<run_id>` artifact from a successful run. Artifacts expire after 30 days. GitHub scheduling may be delayed; disabled Actions or source access errors prevent refresh. A run's green status and manifest are required before claiming a complete pull.

The authoring environment's configured proxy could not be reached. Parser fixture tests passed, but full live retrieval has not been verified there. No downloaded player-stat dataset is bundled or claimed.

## Model integration limits
These are raw season aggregates, separate from the normalized projection-feed contract. The public receiving table provides receptions and targets but not route counts or aDOT. Do not fill those missing inputs with zero or reuse hypothetical defaults. Retain provider column labels verbatim: the displayed YAC heading alone is insufficient to assume whether a value is a total or per-reception rate. A separate validated mapping and advanced usage source are required before these exports can power the prop scanner. fetchedAt records retrieval time, not the time the NFL last updated a statistic. Hourly collection is not a guaranteed live play-by-play feed.
