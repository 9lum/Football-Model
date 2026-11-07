# Weather Lab

Open `/Football-Model/platform/#weather`. The independent tab works even if the player model feed is unavailable.

`scripts/refresh_stadium_weather.py` downloads the current nflverse season schedule, resolves domestic and named neutral venues, and collects Open-Meteo best-match hourly forecasts. Hourly rows cover two hours before through four hours after kickoff. Missing fields remain null. Future weeks remain visible outside the approximately 16-day forecast horizon. Started games retain a previous forecast when available, clearly marked archived; forecasts are never labeled as observed weather.

`.github/workflows/stadium-weather.yml` refreshes hourly (Actions timing is best effort). Each refresh requests one forecast per distinct stadium coordinate inside the horizon, typically about 30 requests. No sportsbook quota or API secrets are consumed. The public Open-Meteo endpoint has usage terms and noncommercial limits; use its commercial service if operating commercially.

`scripts/refresh_stadium_media.py` caches ESPN venue images from the scheduled game's venue record, with source attribution and a credited Wikimedia Commons fallback for Madrid. A photo failure uses the illustrated background. The rotatable CSS stadium is an illustration, not an exact architectural render or measured field orientation.

Research labels screen wind, gusts, hourly precipitation, snowfall, temperature, thunderstorms and visibility. Wind direction is meteorological. Fixed indoor venues suppress outdoor exposure; retractable roofs have an explicitly hypothetical closed-roof switch. SoFi remains open-sided. Team commentary uses actual season pass attempts and carries where a same-season profile exists. It does not alter validated model samples, invent yardage adjustments or claim proven weather-based betting value. Forecast uncertainty increases with lead time; retrieval timestamps are not model issuance timestamps.

Verification: `python -m unittest tests.test_stadium_weather -v`, `node --test web/weather-research.test.mjs`, and the normal frontend build/test suite.
