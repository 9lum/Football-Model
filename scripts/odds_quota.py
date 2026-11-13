"""Protect the shared Odds API allowance for final pregame TD and game-market pulls."""
import calendar,datetime as dt,math,os

def kickoff_reserve(now=None):
 now=now or dt.datetime.now(dt.timezone.utc)
 try:return max(0,int(os.environ['ODDS_KICKOFF_RESERVE_CREDITS']))
 except (KeyError,ValueError):pass
 # Protect one full 16-game slate (six markets/game) plus a 16-credit buffer.
 # Reserving every remaining week can exceed the entire remaining monthly allowance
 # and silently disable collection even when credits are available.
 return 6*16+16

def routine_budget(remaining,requested,now=None):return max(0,min(int(requested),int(remaining)-kickoff_reserve(now)))
