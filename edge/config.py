"""Position-specific outcomes and public sportsbook market identifiers."""
FAMILIES={
 'receiving':{'positions':['WR','TE','RB'],'targets':['receiving_yards','receptions','receiving_tds','targets']},
 'rushing':{'positions':['RB','QB'],'targets':['rushing_yards','carries','rushing_tds']},
 'passing':{'positions':['QB'],'targets':['passing_yards','attempts','completions','passing_tds','passing_interceptions']}}
MARKET_SPECS={
 'player_targets':('Targets','receiving','targets'),
 'player_reception_yds':('Receiving yards','receiving','receiving_yards'),
 'player_receptions':('Receptions','receiving','receptions'),
 'player_reception_tds':('Receiving touchdowns','receiving','receiving_tds'),
 'player_rush_yds':('Rushing yards','rushing','rushing_yards'),
 'player_rush_attempts':('Rush attempts','rushing','carries'),
 'player_rush_tds':('Rushing touchdowns','rushing','rushing_tds'),
 'player_pass_yds':('Passing yards','passing','passing_yards'),
 'player_pass_attempts':('Pass attempts','passing','attempts'),
 'player_pass_completions':('Completions','passing','completions'),
 'player_pass_tds':('Passing touchdowns','passing','passing_tds'),
 'player_pass_interceptions':('Interceptions thrown','passing','passing_interceptions')}
THRESHOLDS={
 'targets':[2.5,4.5,6.5,8.5],
 'receiving_yards':[19.5,39.5,59.5,79.5],'receptions':[1.5,3.5,5.5,7.5],
 'receiving_tds':[.5,1.5],'rushing_yards':[19.5,39.5,59.5,79.5],
 'carries':[4.5,9.5,14.5,19.5],'rushing_tds':[.5,1.5],
 'passing_yards':[174.5,224.5,274.5,324.5],'attempts':[24.5,29.5,34.5,39.5],
 'completions':[14.5,19.5,24.5,29.5],'passing_tds':[.5,1.5,2.5],'passing_interceptions':[.5,1.5]}
