"""Protect the shared Odds API allowance for final pregame TD and game-market pulls."""
import calendar,datetime as dt,math,os

def kickoff_reserve(now=None):
 now=now or dt.datetime.now(dt.timezone.utc)
 try:return max(0,int(os.environ['ODDS_KICKOFF_RESERVE_CREDITS']))
 except (KeyError,ValueError):pass
 days=calendar.monthrange(now.year,now.month)[1]-now.day+1
 # Six markets/game: ATTD, first TD, last TD, moneyline, spread and total.
 return 6*16*math.ceil(days/7)+16

def routine_budget(remaining,requested,now=None):return max(0,min(int(requested),int(remaining)-kickoff_reserve(now)))
