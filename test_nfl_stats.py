import unittest
from nfl_stats import parse
class ParserTests(unittest.TestCase):
    def test_columns_identity_and_next_page(self):
        html = '<table><thead><tr><th>Player</th><th>Yds</th><th>Yds</th></tr></thead><tbody><tr><td><a href="/players/test/">Test Player</a></td><td>1,000</td><td>5</td></tr></tbody></table><a href="?aftercursor=abc">Next Page</a>'
        rows, next_url = parse(html, 'https://www.nfl.com/stats/test')
        self.assertEqual(rows[0]['Yds'], '1,000')
        self.assertEqual(rows[0]['Yds_duplicate'], '5')
        self.assertEqual(rows[0]['playerUrl'], 'https://www.nfl.com/players/test/')
        self.assertEqual(next_url, 'https://www.nfl.com/stats/test?aftercursor=abc')
    def test_blocked_or_empty_page_fails(self):
        for html in ['Access denied', '<table><thead><th>Player</th></thead><tbody></tbody></table>']:
            with self.assertRaises(ValueError):
                parse(html, 'https://www.nfl.com/')
if __name__ == '__main__':
    unittest.main()
