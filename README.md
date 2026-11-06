# Route Edge — public-data NFL receiving research

A receiving-yards and receptions model with public weekly statistics, chronological current-season testing, current route scenarios, and sportsbook price comparison. No profitable edge or backtest return is assumed.

## View your dashboard

**Download [site-preview.html](site-preview.html) using GitHub's Download raw file button, then open it in your browser.** It loads the latest successful model results from this repository. You can also import `latest.json` from a workflow artifact. It shows no fabricated predictions if results are unavailable.

## Automatic weekly statistics

The model uses **nflverse weekly player-game statistics**, normally refreshed nightly after game days. GitHub Actions checks every six hours, trains the model and evaluates the current season using earlier weeks only. The workflow also attempts optional public SumerSports WR/TE route tables; missing route data does not silently become zero.

Open **Actions → Public-data model and current-season tests → Run workflow** to request a fresh run. Select an NFL season or leave it blank for the current season. Successful runs publish `data/latest.json`, `data/validation.json` and `data/oos-predictions.json`. Source manifests and dated route snapshots are available in workflow artifacts.

## Run locally

```sh
pip install -r requirements.txt
python -m unittest discover -s tests -v
node --test tests.mjs tests/market.test.mjs
python -m edge.pipeline --season 2026 --start-season 2021 --output data
```

See [MODEL.md](MODEL.md) for sources, model design, feature timing, quality gates and limitations. See [NFL_DATA.md](NFL_DATA.md) for the separate NFL.com raw-table exporter.

## Scope and verification

The engine tests receiving yards and receptions; rushing, passing and touchdown models are not implemented. Current-season evaluation reports forecast error and distribution calibration. It does not establish ROI or unseen betting edges without point-in-time odds. Current route totals are excluded from historical folds.

The first full public-data run succeeded on GitHub on November 5, 2026 (Toronto time). It evaluated 2,513 player-game observations from 2026 weeks 1–8 and published 386 forecasts, including 221 with current route scenarios. See [RESULTS.md](RESULTS.md) for measured results and the successful run. Local software checks also passed; browser visual QA remains unverified. Check the latest workflow status and source timestamps before relying on a projection.

The legacy `worker/index.js` is the earlier server-based model lab and odds adapter. It requires deployment and server secrets for live odds. No credentials, private hosting identifiers or raw bulk datasets are included in this public repository.
