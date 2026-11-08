"""Retain genuine pregame snapshots after kickoff without generating retrospective picks."""
from copy import deepcopy
from datetime import datetime

def retain_pregame_game(previous,game_id,kickoff):
    try:
        start=datetime.fromisoformat(kickoff.replace('Z','+00:00'))
        old=next(g for g in previous.get('games',[]) if g.get('gameId')==game_id and datetime.fromisoformat(g.get('kickoff','').replace('Z','+00:00'))==start)
        stamp=old.get('pregameGeneratedAt') or previous.get('generatedAt','')
        if datetime.fromisoformat(stamp.replace('Z','+00:00'))>=start or not old.get('players'):return None
    except (ValueError,TypeError,StopIteration):return None
    saved=deepcopy(old)
    saved.update(status='started/completed',pregameGeneratedAt=stamp,note='Archived pregame projections retained during play; these are not live scoring probabilities.')
    for player in [*saved.get('players',[]),*saved.get('candidates',[])]:
        for quote in player.get('quotes',[]):quote['qualified']=False
    return saved
