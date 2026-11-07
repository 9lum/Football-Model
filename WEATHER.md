# Weather Lab

Open `/Football-Model/platform/#weather`. The independent tab works even if the player model feed is unavailable.

`scripts/refresh_stadium_weather.py` downloads the current nflverse season schedule, resolves domestic and named neutral venues, and collects Open-Meteo best-match hourly forecasts. Hourly rows cover two hours before through four hours after kickoff. Missing fields remain null. Future weeks remain visible outside the approximately 16-day forecast horizon. Started games retain a previous forecast when available, clearly marked archived; forecasts are never labeled as observed weather.

`.github/workflows/stadium-weather.yml` refreshes hourly (Actions timing is best effort). Each refresh requests one forecast per distinct stadium coordinate inside the horizon, typically about 30 requests. No sportsbook quota or API secrets are consumed. The public Open-Meteo endpoint has usage terms and noncommercial limits; use its commercial service if operating commercially.

`scripts/refresh_stadium_media.py` caches ESPN venue images from the scheduled game's venue record, with source attribution and a credited Wikimedia Commons fallback for Madrid. A photo failure uses the illustrated background. The rotatable CSS stadium is an illustration, not an exact architectural render or measured field orientation.

Research labels screen wind, gusts, hourly precipitation, snowfall, temperature, thunderstorms and visibility. Wind direction is meteorological. Fixed indoor venues suppress outdoor exposure; retractable roofs have an explicitly hypothetical closed-roof switch. SoFi remains open-sided. Team commentary uses actual season pass attempts and carries where a same-season profile exists. It does not alter validated model samples, invent yardage adjustments or claim proven weather-based betting value. Forecast uncertainty increases with lead time; retrieval timestamps are not model issuance timestamps.

Verification: `python -m unittest tests.test_stadium_weather -v`, `node --test web/weather-research.test.mjs`, and the normal frontend build/test suite.

## Interactive stadium and future seasons

The expanded scene now uses a lazy-loaded Three.js WebGL stadium. Horizontal drag or the orbit slider rotates through 360 degrees; vertical drag and the tilt slider change elevation. End-zone picking or explicit buttons select the kicking direction. Forecast-hour changes update wind, clouds, daylight, precipitation and the qualitative kicking arc. Scene pause and the site's global animation switch stop the animation. Devices without WebGL retain the weather readouts.

Wind is converted from meteorological FROM direction to a TO vector, then projected onto the assumed field axis. The compass bearing is explicitly unverified and adjustable; no measured field-level flow or surveyed stadium geometry is claimed. Headwind/tailwind reverse when changing ends; crosswind magnitude remains the same. The ball arc is illustrative, not a calibrated flight or kick-success model. Closed roofs suppress on-field wind and precipitation.

Header photos have been replaced by generated architectural illustrations delivered as seven lossless WebP atlases through SVG tile viewports. The 42 tiles include indoor/outdoor generic fallbacks. All stadiums in the current schedule have a matching render, with additional named international venues. Artwork is static and does not imply forecast weather or an officially confirmed roof state. The delivery encoding was verified pixel-for-pixel against the generated originals. Render assets load on approach to the viewport.

Game-plan and player explanations are visible beneath each stadium. Named players come only from eligible forecasts for that exact game and team. Future weeks without eligible player forecasts show role-based context and explain that names are pending.

Season selection follows the earliest future season in the public NFL schedule, including scheduled games with kickoff times still TBD. Offseason feeds explicitly wait for the next public schedule. `data/stadium-venues.json` caches known venue coordinates; new venue names use a rate-limited, unique-stadium lookup through OpenStreetMap/Nominatim. Ambiguous locations remain unavailable instead of using a home-city substitute. New venues use generic artwork automatically until custom artwork exists. Forecasts still become available only within the provider's horizon, and future schedules/venue details depend on the public sources being updated.
