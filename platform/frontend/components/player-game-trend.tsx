'use client';
import Chart from './chart';
import {playerTrendOption} from '../../../web/player-game-data.mjs';
import {usePlayerGames} from './use-player-games';
export default function PlayerGameTrend({player,forecast,market,target,gameId,height=300}:any){const {games,archives}=usePlayerGames(player,gameId);return <><Chart height={height} label="Player game-by-game actual stats versus published pregame and upcoming projections" option={playerTrendOption({games,archives,playerId:player?.playerId,market,target,upcoming:forecast,focusGameId:gameId})}/><p className="research-chart-note">Hover or tap a game for Actual vs Published pregame projection. Missing forecasts show “Not archived”; missing outcomes are not treated as zero.</p></>}
