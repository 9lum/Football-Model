import datetime as dt
import unittest
from scripts.refresh_stadium_weather import location,kickoff_of,forecast_hours,UTC
class StadiumWeatherTests(unittest.TestCase):
    def test_neutral_madrid_uses_stadium_not_home_city(self):
        coords,roof=location({'home_team':'ATL','location':'Neutral','stadium':'Bernabeu'})
        self.assertAlmostEqual(coords[0],40.4531);self.assertEqual(roof,'retractable')
    def test_unknown_neutral_does_not_use_home_coordinates(self):
        self.assertEqual(location({'home_team':'ATL','location':'Neutral','stadium':'Unknown'}),(None,'unknown'))
    def test_mexico_renamed_venue(self):
        self.assertAlmostEqual(location({'home_team':'SF','location':'Neutral','stadium':'Estadio Banorte'})[0][0],19.3029)
    def test_roof_types_do_not_treat_open_sided_stadium_as_indoor(self):
        for team,expected in [('DET','indoor'),('ATL','retractable'),('LAR','covered-open'),('GB','outdoor')]:
            self.assertEqual(location({'home_team':team})[1],expected)
    def test_schedule_timezone_observes_dst(self):
        self.assertEqual(kickoff_of({'gameday':'2026-11-08','gametime':'13:00'}).hour,18)
        self.assertEqual(kickoff_of({'gameday':'2026-09-13','gametime':'13:00'}).hour,17)
    def test_window_and_missing_fields_are_not_zero_filled(self):
        kickoff=dt.datetime(2026,11,8,18,30,tzinfo=UTC)
        payload={'hourly':{'time':['2026-11-08T10:00','2026-11-08T18:00','2026-11-08T19:00'],'temperature_2m':[2,4,5]}}
        rows=forecast_hours(payload,kickoff);self.assertEqual(len(rows),2);self.assertEqual(rows[0]['temperatureC'],4);self.assertIsNone(rows[0]['gustKph'])
    def test_outside_horizon_has_no_nearest_day_substitution(self):
        self.assertEqual(forecast_hours({'hourly':{'time':['2026-11-07T18:00']}},dt.datetime(2026,11,8,18,tzinfo=UTC)),[])
if __name__=='__main__':unittest.main()
