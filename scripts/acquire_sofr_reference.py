"""Acquire administrator rates and primary calendar evidence over public HTTP."""
import json, uuid
from pathlib import Path
from urllib.request import urlopen, Request
from credit_atlas.workspace import sha256, timestamp, write_new

root = Path.cwd()
identifier = 'sofr-source-' + uuid.uuid4().hex[:12]
folder = root / 'data/private/reference-rates' / identifier
folder.mkdir(parents=True)
sources = {
    'sofrai.json': 'https://markets.newyorkfed.org/api/rates/secured/sofrai/search.json?startDate=2025-01-01&endDate=2026-10-11',
    'sifma-archive.html': 'https://www.sifma.org/resources/guides-playbooks/us-holiday-archive',
    'sifma-current.html': 'https://www.sifma.org/resources/general/holiday-schedule',
    'nyfed-method.html': 'https://www.newyorkfed.org/markets/reference-rates/sofr-averages-and-index',
    'nyfed-good-friday.html': 'https://www.newyorkfed.org/markets/opolicy/operating_policy_260312',
}
records = []
for name, url in sources.items():
    with urlopen(Request(url,headers={'User-Agent':'CreditAtlas private source research'}),timeout=45) as response:
        if response.status != 200 or response.url != url:
            raise ValueError('Unexpected source response/redirect')
        data = response.read(8 * 1024**2 + 1)
        if not data or len(data) > 8 * 1024**2:
            raise ValueError('Empty or oversize source')
        (folder/name).write_bytes(data)
        records.append({'file':name,'url':url,'http_status':response.status,'retrieved_at':timestamp(),
                        'bytes':len(data),'sha256':sha256(folder/name)})
rates = json.loads((folder/'sofrai.json').read_text())['refRates']
write_new(folder/'acquisition-complete.json', {'source_id':identifier,'status':'OFFICIAL_REFERENCE_SOURCES_ACQUIRED',
    'visibility':'private','public_release_approved':False,'sources':records,
    'rate_rows':len(rates),'requested_start':'2025-01-01','requested_end':'2026-10-11',
    'earliest':min(r['effectiveDate'] for r in rates),'latest':max(r['effectiveDate'] for r in rates),
    'historical_publication_vintage_verified':False,'rights':'Administrator/SIFMA terms apply; internal source research with attribution',
    'script_sha256':sha256(Path(__file__))})
print(identifier); print(json.dumps({'files':len(records),'rate_rows':len(rates),'bytes':sum(r['bytes'] for r in records)}))
