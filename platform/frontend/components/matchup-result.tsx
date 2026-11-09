'use client';
import {matchupResult} from '../../../web/matchup-result.mjs';
import {Card} from './ui';
import TeamMark from './team-mark';
import './matchup-result.css';
export default function MatchupResult({game,snapshot,history}:any){
 const result=matchupResult(game,snapshot,history);if(!result)return null;
 const {state,projection:p,checks}=result;
 return <Card className="matchup-result"><header><h3>Final result & model review</h3><span>Finished</span></header><div className="matchup-result-score"><TeamMark team={game.away_team} small/><strong>{state.awayScore}</strong><span>—</span><strong>{state.homeScore}</strong><TeamMark team={game.home_team} small/></div>{p?<><p className="small muted">Pregame score: {game.away_team} {p.awayPoints.toFixed(1)} · {game.home_team} {p.homePoints.toFixed(1)}. Issued {new Date(p.projectedAt).toLocaleString()}.</p><div className="matchup-result-checks">{checks.map((c:any)=><div className={'matchup-result-check result-'+c.tone} key={c.label}><span>{c.label}</span><strong>{c.tone==='good'?'✓ ':c.tone==='bad'?'× ':''}{c.result}</strong><small>{c.detail}</small></div>)}</div><p className="matchup-result-note">Green = correct winner or actual inside the forecast range. Red = missed winner or outside range. Range coverage is not a sportsbook bet result or proof of profitability.</p></>:<p className="small muted">No verified pregame forecast saved for this game; model performance cannot be graded.</p>}</Card>;
}
