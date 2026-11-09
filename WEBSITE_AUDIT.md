# Website audit — November 8, 2026 (America/Toronto)

## Changes

- One shared weekly display rule now controls Dashboard, Matchup Lab, Prop Explorer, Touchdown Lab, game-odds views, team upcoming fixtures and stadium matchups.
- Next week stays hidden until every known scheduled fixture in the current week has a confirmed final result. Monday kickoff alone cannot unlock next week. Postponed games and missing final confirmations hold the current week.
- A partial scoreboard response cannot override a known unfinished fixture. Initial page loading waits for schedule, forecast history, touchdown report and scoreboard inputs before showing matchups.
- Server polling continues checking unfinished prior weeks even after an upcoming-only feed advances.
- Original touchdown snapshots are retained across weekly report rollover; historical results remain accessible.
- Matchup venue/rest context now follows the chosen game instead of an unrelated selected player.
- Existing compact spacing, typography, zoom controls, themes and responsive layouts are preserved. The weekly display notice uses the same compact bordered treatment.

## Verification

- Frontend checks: 95 passed in the full run, plus the additional partial-scoreboard regression passed afterward (96 checks in total).
- Model tests: 50 passed.
- Pipeline tests: 38 passed.
- Production static build passed after the layout/context changes; publication CI checks the final source.
- Public data: all 23 requested JSON datasets loaded.
- Live-source data audit: 575 players, 313 forecasts, 1,266 market distributions and 490 matched current-week prop quotes. No invalid count samples/probabilities, mismatched means, incorrect team/opponent orientation, conflicting defensive inputs, or post-kickoff record issue times were found in those checks. Yardage distributions may correctly include negative outcomes.
- Published assets: all 10 referenced JS/CSS assets returned HTTP 200.
- Team logos: all 32 returned HTTP 200.
- Rollover regressions cover Sunday completion, Monday kickoff, confirmed Monday final, missing finals, delayed games, incomplete provider coverage, legacy snapshots, archived touchdown picks and next-week odds filtering.

## Coverage and limits

These checks verify the tested data and behavior; they do not establish betting profitability or guarantee every provider statistic is correct. Licensed/unpublished inputs remain explicitly unavailable rather than invented.

Provider metadata currently reports Xweather authentication rejected and BALLDONTLIE partial coverage. The public Open-Meteo weather fallback remains labeled. Credentials were not exposed or altered during this audit.

Interactive browser/screenshot QA was unavailable. No NodeREPL/browser-control tool or `cua_repl.js` entrypoint was exposed. The [Sites skill](skill://plugin_connector_1p_689987207de08191979cf68eca2941c6/sites/SKILL.md) explicitly says: “If `cua_repl.js` is unavailable, skip browser QA: do not start a preview server, install a browser, or improvise another browser-control path.” Consequently, visual spacing was reviewed through source/layout rules and static output, not a rendered browser session. This remains the principal verification limit.
