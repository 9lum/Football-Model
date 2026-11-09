import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pandas as pd
from edge.profiles import aggregate,COUNTERS,player_profiles
from edge.model import DistributionForest
from edge.pipeline import run
from test_engine import fixture

class ProfileTests(unittest.TestCase):
    def test_weighted_rates_and_unknown_fields(self):
        frame=pd.DataFrame({'attempts':[10,30],'completions':[10,15],'passing_yards':[100,150],'passing_tds':[1,1],'passing_interceptions':[0,1],'carries':[2,4],'rushing_yards':[8,12]})
        stats=aggregate(frame)
        self.assertEqual(stats['completion_pct'],62.5)
        self.assertAlmostEqual(stats['yards_per_carry'],20/6)
        self.assertTrue(pd.isna(stats['receiving_yards']))
        self.assertGreater(stats['passer_rating'],0)
    def test_complete_position_pipeline_exports_basic_stats_history_and_all_families(self):
        source,sched=fixture();rows=[]
        # A compact synthetic integration fixture, not reported as a real backtest.
        for position in ['QB','RB','WR','TE']:
            for i in range(45):
                part=source[source.player_id.eq('SEA0')].copy()
                part['player_id']=position+str(i);part['player_display_name']=position+' Player '+str(i);part['position']=position
                for field in COUNTERS:
                    if field not in part:part[field]=0.
                part['receiving_tds']=i%2;part['receiving_yards']=i+part.week
                part['attempts']=30 if position=='QB' else 0;part['completions']=20 if position=='QB' else 0
                part['passing_yards']=200+i if position=='QB' else 0;part['passing_tds']=i%3 if position=='QB' else 0
                part['passing_interceptions']=i%2 if position=='QB' else 0;part['carries']=i%15;part['rushing_yards']=i*2;part['rushing_tds']=i%2
                rows.append(part)
        stats=pd.concat(rows,ignore_index=True)
        future=sched[(sched.season==2026)&(sched.week==8)].copy();future['week']=10;future['game_id']='2026_10_SEA_SF';future['kickoff']=pd.Timestamp('2026-11-08T20:00:00Z');future['completed']=False
        sched=pd.concat([sched,future],ignore_index=True)
        # Only Seattle has fixture players, so absent SF is explicitly a coverage issue.
        with tempfile.TemporaryDirectory() as temp,patch('edge.pipeline.collect',return_value=(stats,sched,{},[],{})):
            report=run(2025,2026,Path(temp),trees=2,as_of='2026-11-06T00:00:00Z',enrich=False)
            bundle=json.loads((Path(temp)/'latest.json').read_text())
            self.assertEqual(bundle['schemaVersion'],3)
            self.assertEqual(set(bundle['familyValidation']),{'receiving','rushing','passing'})
            self.assertEqual(len(bundle['marketConfig']),12)
            self.assertIn('player_targets',bundle['marketConfig'])
            qb=next(f for f in bundle['forecasts'] if f['position']=='QB')
            self.assertIn('player_pass_yds',qb['marketSamples']);self.assertNotIn('player_reception_yds',qb['marketSamples'])
            profile=next(p for p in bundle['players'] if p['playerId']==qb['playerId'])
            self.assertEqual(len(profile['history']),8);self.assertEqual(profile['basicStats']['season']['attempts'],240)
            self.assertTrue(all('passing_yards' in h for h in profile['history']))

if __name__=='__main__':unittest.main()
