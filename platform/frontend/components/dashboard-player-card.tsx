'use client';
import PlayerStatusLight from './player-status-light';
import {Badge,Card} from './ui';
import TeamMark from './team-mark';
import DashboardPropComparison from './dashboard-prop-comparison';
import {researchHref} from '../../../web/research-links.mjs';
const fmt=(n:any)=>Number.isFinite(n)?Number(n).toLocaleString(undefined,{maximumFractionDigits:1}):'—';
export default function DashboardPlayerCard({player:p,quotes}:any){
 const href=researchHref('players',{player:p.playerId,team:p.team,market:p.market});
 return <Card className="model-favorite-card"><div className="dashboard-card-badges"><span className="player-card-position"><Badge>{p.position}</Badge><PlayerStatusLight player={p}/></span><Badge tone={p.qualityPassed?'good':'warn'}>{p.qualityPassed?'Gate passed':'Research'}</Badge></div><h3 className="dashboard-card-title"><a title={p.name} href={href}>{p.name}</a></h3><div className="model-card-matchup"><TeamMark team={p.team} small/><a href={researchHref('matchups',{game:p.gameId,team:p.team})} aria-label={p.team+' versus '+p.opponent+' matchup'}>vs</a><TeamMark team={p.opponent} small/></div><DashboardPropComparison low={p.summary.low} high={p.summary.high} projection={p.summary.mean} quotes={quotes} market={p.market}/><footer className="dashboard-card-footer"><span>Past error {fmt(p.pastMae)} · {p.testGames} test games</span><a href={href}>Player research <span aria-hidden="true">↗</span></a></footer></Card>;
}
