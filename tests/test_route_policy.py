import unittest
import numpy as np
import pandas as pd
from edge.route_policy import RoutePolicy,rationale
class RoutePolicyTests(unittest.TestCase):
 def test_warmup_adjustments_are_bounded_and_count_samples_remain_coherent(self):
  policy=RoutePolicy({1,2});test=pd.DataFrame([{'week':3,'routeContext':{'status':'available','direction':1,'signal':.2}}]);samples=np.tile([10,8,100,1],(1,512,1)).astype(float)
  adjusted,meta=policy.apply(test,samples,['targets','receptions','receiving_yards','receiving_tds'],[])
  self.assertAlmostEqual(adjusted[0,:,0].mean(),10.5);self.assertTrue((adjusted[0,:,1]<=adjusted[0,:,0]).all());self.assertTrue((adjusted%1==0).all());self.assertEqual(meta[0]['routeFactors']['targets'],1.05)
 def test_future_and_partial_week_outcomes_do_not_tune_the_policy(self):
  policy=RoutePolicy({1,2});records=[{'week':3,'game_id':str(i),'routeCandidates':{'targets':[10,11,12,13],'receptions':[8,9,10,11],'receiving_yards':[100,110,120,130]},'targets':{'actual':13},'receptions':{'actual':11},'receiving_yards':{'actual':130}} for i in range(300)]
  selected=policy.select(records,3);self.assertEqual(selected['n'],0);self.assertEqual(selected['volume'],.05)
 def test_learned_policy_disables_a_layer_that_does_not_improve(self):
  records=[{'week':1,'game_id':str(i%40),'routeCandidates':{'targets':[10,11,12,13],'receptions':[8,9,10,11],'receiving_yards':[100,110,120,130]},'targets':{'actual':10},'receptions':{'actual':8},'receiving_yards':{'actual':100}} for i in range(240)]
  selected=RoutePolicy({1}).select(records,2);self.assertEqual(selected['volume'],0);self.assertEqual(selected['yards'],0)
 def test_incremental_quality_gate_requires_enough_independent_games_and_actual_improvement(self):
  policy=RoutePolicy({1});record={'week':1,'game_id':'g','routeCandidates':{'receptions':[4,4.2,4.4,4.6]},'receptions':{'actual':5,'mean':4.5,'unadjustedMean':4}}
  self.assertFalse(policy.validation([record],['receptions'])['receptions']['incrementalPassed'])
  rows=[{**record,'game_id':str(i%40)} for i in range(500)]
  self.assertTrue(policy.validation(rows,['receptions'])['receptions']['incrementalPassed'])
