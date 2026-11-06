"""Export every NFL.com player-stat category and pagination page for a season."""
import argparse
import csv
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from html.parser import HTMLParser

class Node:
    def __init__(self, tag="root", attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []
    def get(self, key, default=None):
        return self.attrs.get(key, default)
    def __getitem__(self, key):
        return self.attrs[key]
    def descendants(self):
        for c in self.children:
            if isinstance(c, Node):
                yield c
                yield from c.descendants()
    def get_text(self, separator=" ", strip=True):
        def texts(node):
            for c in node.children:
                if isinstance(c, str):
                    if c.strip(): yield c.strip()
                else: yield from texts(c)
        return separator.join(texts(self))
    def find_all(self, tag, recursive=True):
        return [n for n in (self.descendants() if recursive else self.children) if isinstance(n, Node) and n.tag == tag]
    def select(self, selector):
        if selector == "a[href]":
            return [n for n in self.descendants() if n.tag == "a" and n.get("href")]
        if selector == 'a[href*="/players/"]':
            return [n for n in self.select("a[href]") if "/players/" in n["href"]]
        parts = selector.split()
        if len(parts) == 1: return self.find_all(parts[0])
        return [n for parent in self.find_all(parts[0]) for n in parent.select(" ".join(parts[1:]))]
    def select_one(self, selector):
        return next(iter(self.select(selector)), None)

class Document(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.stack = [self.root]
        self.feed(html)
    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in {"area","base","br","col","embed","hr","img","input","link","meta","param","source","track","wbr"}:
            self.stack.append(node)
    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1, 0, -1):
            if self.stack[i].tag == tag:
                self.stack = self.stack[:i]
                break
    def handle_data(self, data):
        self.stack[-1].children.append(data)

def BeautifulSoup(html, parser):
    return Document(html).root

ROOT = 'https://www.nfl.com'

def page(url):
    if urlparse(url).netloc != 'www.nfl.com':
        raise ValueError('Unexpected source host')
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={'User-Agent': 'RouteEdgeStats/0.1 (NFL player statistics research)'}), timeout=45) as r:
                return r.read().decode('utf-8')
        except Exception:
            if attempt == 2:
                raise
            time.sleep(5 * (attempt + 1))

def parse(html, url):
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.select_one('table')
    if not table:
        raise ValueError('No statistics table; source may be unavailable or markup changed')
    headers = [x.get_text(' ', strip=True) for x in table.select('thead th')]
    if not headers:
        raise ValueError('No table headers')
    # Preserve duplicate labels without overwriting columns.
    columns = []
    for h in headers:
        key = h or 'unnamed'
        while key in columns:
            key += '_duplicate'
        columns.append(key)
    rows = []
    for tr in table.select('tbody tr'):
        cells = tr.find_all('td', recursive=False)
        if not cells:
            continue
        if len(cells) != len(columns):
            raise ValueError('Statistics column count changed')
        record = dict(zip(columns, [c.get_text(' ', strip=True) for c in cells]))
        player = tr.select_one('a[href*="/players/"]')
        if player:
            record[columns[0]] = player.get_text(' ', strip=True)
            record['playerUrl'] = urljoin(ROOT, player['href'])
        record['sourceUrl'] = url
        rows.append(record)
    if not rows:
        raise ValueError('Empty statistics table; no successful snapshot written')
    next_links = [urljoin(url, a['href']) for a in soup.select('a[href]')
                  if a.get_text(' ', strip=True).lower() == 'next page' or
                  str(a.get('aria-label', '')).lower() == 'next page']
    return rows, next_links[0] if next_links else None

def export(season, season_type, output, delay=2):
    base = f'{ROOT}/stats/player-stats/category/passing/{season}/{season_type}/all/passingyards/DESC'
    first = page(base)
    soup = BeautifulSoup(first, 'html.parser')
    categories = {'passing': base}
    for a in soup.select('a[href]'):
        href = urljoin(ROOT, a['href'])
        parts = urlparse(href).path.strip('/').split('/')
        if len(parts) >= 9 and parts[:3] == ['stats', 'player-stats', 'category']:
            # Preserve discovered category/sort slug while explicitly selecting season/type.
            parts[4], parts[5] = str(season), season_type
            categories.setdefault(parts[3], ROOT + '/' + '/'.join(parts))
    if len(categories) < 11:
        raise ValueError(f'Expected at least 11 category links, found {len(categories)}; refusing incomplete export')
    collected = {}
    fetched = datetime.now(timezone.utc).isoformat()
    for category, start in categories.items():
        url, seen_urls, seen_pages, rows, urls = start, set(), set(), [], []
        while url:
            if url in seen_urls or len(seen_urls) >= 500:
                raise ValueError('Pagination loop or safety limit: ' + category)
            seen_urls.add(url)
            html = first if url == base else page(url)
            batch, next_url = parse(html, url)
            fingerprint = hashlib.sha256(json.dumps([{k:v for k,v in r.items() if k!='sourceUrl'} for r in batch], sort_keys=True).encode()).hexdigest()
            if fingerprint in seen_pages:
                raise ValueError('Repeated statistics page: ' + category)
            seen_pages.add(fingerprint)
            rows.extend(batch)
            urls.append(url)
            url = next_url
            time.sleep(delay)
        collected[category] = {'rows': rows, 'pages': urls}
    output.mkdir(parents=True, exist_ok=True)
    manifest = {'source': ROOT+'/stats/player-stats/', 'season': season, 'seasonType': season_type,
                'fetchedAt': fetched, 'completedAt': datetime.now(timezone.utc).isoformat(),
                'scope': 'All discovered player-stat categories, all pagination pages, selected season and season type',
                'missingModelInputs': ['routes', 'aDOT', 'routeParticipation', 'projectedDropbacks', 'eventId'],
                'categories': {}}
    for category, data in collected.items():
        (output/(category+'.json')).write_text(json.dumps(data, indent=2), encoding='utf-8')
        fields = list(dict.fromkeys(k for r in data['rows'] for k in r))
        with (output/(category+'.csv')).open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(data['rows'])
        manifest['categories'][category] = {'rows': len(data['rows']), 'pages': len(data['pages'])}
    temp = output/'manifest.json.tmp'
    temp.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    temp.replace(output/'manifest.json')
    return manifest

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--season', type=int, required=True)
    p.add_argument('--season-type', choices=['REG', 'PRE', 'POST'], default='REG')
    p.add_argument('--output', type=Path, default=Path('data/nfl'))
    args = p.parse_args()
    print(json.dumps(export(args.season, args.season_type, args.output), indent=2))
