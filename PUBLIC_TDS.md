# Public touchdown scorer prices

The collector reads DraftKings' public player-prop table at https://dknetwork.draftkings.com/draftkings-sportsbook-player-props/ . It accepts only **Anytime TD Scorer** and **2+ TDs** rows. Each quote must match one unique player forecast, both teams, and the upcoming game's Eastern date/time. Book links and observation times are retained. The source does not supply the sportsbook's quote-update time, so observations never become verified fresh offers or qualifying value recommendations.

These are **TDs scored**, not separate rushing or receiving touchdown statistics. Passing TDs are excluded from scorer bets, while house rules can count return TDs. See FanDuel's scorer rules: https://fanduelgroup.my.site.com/hc/s/article/Touchdown-props . Do not substitute scorer prices for an exact rushing-only, receiving-only or offensive-only TD market.

The snapshot refreshes every 15 minutes, subject to GitHub scheduling delays, and during final pregame preparation. It uses no paid API credits. Source outages retain original observations; exact kickoff matching and stale labels continue to apply. The page lists selected props, so coverage is not every player or every sportsbook.

The browser merges these public prices with the existing multi-book API snapshot, preferring API quotes for duplicate player/book/market offers. The 2+ TD market stays distinct from 1+ ATTD. No 2+ model probability is fabricated. Find collected prices inside the sportsbook dropdown in Prop Explorer and TD details in Player Research and Touchdown Lab.
