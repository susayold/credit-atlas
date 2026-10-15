"""Independent administrator-rate comparison; existing ABS projections stay frozen."""
import json
import re
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from html.parser import HTMLParser
import pyarrow.parquet as pq
from .workspace import contained, read_json, sha256

SOURCE_ID = 'sofr-source-a076d14b0327'
RECEIPT_SHA = 'f0495d7d4722fda580aa2930a289078f2c9a590c42a0962cf12c9a3f860e4849'
PROSPECTUS_SHA = 'dc34695537492fd7f452e3dd735d4938e76eedde87f441e127e94875e708e653'


class Text(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []; self.skip = 0
    def handle_starttag(self, tag, attrs):
        if tag in ('script','style'): self.skip += 1
        if tag in ('h2','h3','p','li'): self.parts.append('\n')
    def handle_endtag(self, tag):
        if tag in ('script','style'): self.skip = max(0,self.skip-1)
        if tag in ('h2','h3','p','li'): self.parts.append('\n')
    def handle_data(self, data):
        if not self.skip: self.parts.append(data)


def calendar(html, year):
    parser = Text(); parser.feed(html)
    text = '\n'.join(' '.join(line.split()) for line in ''.join(parser.parts).splitlines() if line.strip())
    if year == 2025:
        text = text.split('2025\nNew Year',1)[1].split('\n2024\n',1)[0]
    elif year == 2026:
        text = text.split('U.S. Holiday Recommendations',1)[1].split('U.K. Holiday Recommendations',1)[0]
    else: raise ValueError('Calendar year outside acquired evidence')
    full = []; early = []
    pattern = r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), ([A-Za-z]+ \d{1,2}, \d{4})'
    for line in text.splitlines():
        match = re.search(pattern,line)
        if not match: continue
        from datetime import datetime
        d = datetime.strptime(match[2],'%B %d, %Y').date()
        if d.year != year: continue
        if d.strftime('%A') != match[1]: raise ValueError('Calendar weekday mismatch')
        (early if 'Early Close' in line else full).append(d.isoformat())
    if len(set(full)) != (12 if year == 2025 else 11) or len(full)!=len(set(full)):
        raise ValueError('Incomplete or ambiguous SIFMA full-close calendar')
    if (year == 2025 and '2025-04-18' not in full
            or year == 2026 and ('2026-04-03' in full or '2026-04-03' not in early)):
        raise ValueError('Good Friday full/early close distinction changed')
    return {'year':year,'full_closes':sorted(full),'early_closes':sorted(set(early))}


def adjustment_date(start, calendars):
    d = date.fromisoformat(start); counted = []
    while len(counted)<2:
        d -= timedelta(days=1)
        if d.year not in calendars: raise ValueError('Calendar evidence does not cover lookback')
        if d.weekday()<5 and d.isoformat() not in calendars[d.year]['full_closes']:
            counted.append(d.isoformat())
    return counted[-1], counted


def rates_from(payload):
    if not isinstance(payload,dict) or set(payload)!={'refRates'} or not isinstance(payload['refRates'],list) or not payload['refRates']:
        raise ValueError('Administrator SOFRAI array required')
    rates = {}
    for r in payload['refRates']:
        d = r['effectiveDate']; date.fromisoformat(d)
        if r.get('type')!='SOFRAI' or d in rates: raise ValueError('Wrong/duplicate administrator series')
        value = r['average30day']
        if isinstance(value,bool) or not isinstance(value,(int,Decimal)):
            raise ValueError('Numeric administrator rate required')
        value = Decimal(value)
        if not value.is_finite() or not Decimal('-10')<=value<=Decimal('30'):
            raise ValueError('Invalid administrator rate')
        rates[d] = {'percent_exact':str(value), 'fraction_exact':str(value/100),
                    'revision_indicator':r.get('revisionIndicator','')}
    return rates


def reference(root):
    folder = contained(root,'data/private/reference-rates/'+SOURCE_ID)
    if sha256(folder/'acquisition-complete.json')!=RECEIPT_SHA: raise ValueError('Reference acquisition receipt changed')
    receipt = read_json(folder/'acquisition-complete.json')
    if receipt.get('source_id')!=SOURCE_ID or receipt.get('status')!='OFFICIAL_REFERENCE_SOURCES_ACQUIRED' or receipt.get('public_release_approved') is not False:
        raise ValueError('Reference source contract changed')
    for item in receipt['sources']:
        p=contained(root,'data/private/reference-rates/'+SOURCE_ID+'/'+item['file'])
        if p.stat().st_size!=item['bytes'] or sha256(p)!=item['sha256']:
            raise ValueError('Administrator/calendar source bytes changed')
    rates=rates_from(json.loads((folder/'sofrai.json').read_text(),parse_float=Decimal))
    calendars={2025:calendar((folder/'sifma-archive.html').read_text(encoding='utf-8'),2025),
               2026:calendar((folder/'sifma-current.html').read_text(encoding='utf-8'),2026)}
    if len(rates)!=receipt['rate_rows']: raise ValueError('Administrator rate count changed')
    return rates,calendars,receipt


def compare_period(p, metrics, rates, calendars):
    fixing,lookback=adjustment_date(p['accrual_start'],calendars)
    available=[d for d in rates if d<=fixing and date.fromisoformat(d).year in calendars
               and date.fromisoformat(d).weekday()<5 and d not in calendars[date.fromisoformat(d).year]['full_closes']]
    source_date=fixing if fixing in rates else max(available,default=None)
    if source_date is None: raise ValueError('No acquired 30-day rate at or before fixing')
    if (date.fromisoformat(fixing)-date.fromisoformat(source_date)).days>10:
        raise ValueError('Rate fallback exceeds acquired evidence support')
    def cell(key):
        rows=[r for r in metrics if r['collection_end']==p['collection_end'] and r['section']=='note_slot' and r['slot']=='A-2b' and r['metric']==key]
        if len(rows)!=1 or rows[0]['status']!='VALUE': raise ValueError('Reported benchmark input unavailable')
        return rows[0]
    sofr=cell('sofr_rate'); coupon=cell('coupon'); balance=cell('beginning_balance')
    official=Decimal(rates[source_date]['fraction_exact']).quantize(Decimal('.0000001'),rounding=ROUND_HALF_UP)
    expected=max(Decimal(0),official+Decimal('.0033'))
    delta=Decimal(sofr['value'])-official; coupon_delta=Decimal(coupon['value'])-expected
    days=(date.fromisoformat(p['distribution_date'])-date.fromisoformat(p['accrual_start'])).days
    interest=(Decimal(balance['value'])*expected*days/360).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
    tolerance=Decimal('1e-15')
    return {'collection_end':p['collection_end'],'accrual_start':p['accrual_start'],'payment_date':p['distribution_date'],
            'adjustment_date':fixing,'counted_business_dates':lookback,'administrator_rate_date':source_date,
            'fallback_used':source_date!=fixing,'administrator_percent_exact':rates[source_date]['percent_exact'],
            'administrator_fraction_exact':str(official),'reported_sofr_fraction_exact':sofr['value'],
            'sofr_delta_exact':str(delta),'coupon_fraction_exact':str(expected),'reported_coupon_fraction_exact':coupon['value'],
            'coupon_delta_exact':str(coupon_delta),'rate_value_match':delta==0,'coupon_match':coupon_delta==0,
            'rate_precision_match':abs(delta)<=tolerance,'coupon_precision_match':abs(coupon_delta)<=tolerance,
            'source_binary_tolerance_fraction_exact':str(tolerance),
            'actual_days':days,'beginning_balance_exact':balance['value'],'independent_base_interest_exact':str(interest),
            'source_cell':{k:sofr[k] for k in ('file','sheet','row','column','raw_value')},
            'revision_indicator':rates[source_date]['revision_indicator']}


def report(views, identifier, query):
    if set(query)-{'view_id','period'} or query.get('view_id',identifier)!=identifier:
        raise ValueError('Verified ABS view/period scope required')
    snapshot,replay=views.evidence(identifier)
    root=views.root
    case=read_json(contained(root,'artifacts/private/'+snapshot['case_id']+'/case-complete.json'))
    prospectus=contained(root,'data/private/structured/'+case['source_id']+'/WOART_2025-A_Final_Prospectus.pdf')
    if sha256(prospectus)!=PROSPECTUS_SHA: raise ValueError('Supported prospectus version required')
    rates,calendars,source=reference(root)
    metrics=pq.read_table(contained(root,'artifacts/private/'+snapshot['case_id']+'/reported_metrics.parquet')).to_pylist()
    periods=case['periods']
    if query.get('period'):
        periods=[p for p in periods if p['collection_end']==query['period']]
        if not periods: raise ValueError('Collection period absent from verified source')
    rows=[compare_period(p,metrics,rates,calendars) for p in periods]
    for row in rows:
        period=next(p for p in replay['periods'] if p['collection_end']==row['collection_end'])
        observed=period['inputs']['interest_due']['A-2b']
        row['reported_interest_due_exact']=observed
        row['interest_delta_exact']=str(Decimal(observed)-Decimal(row['independent_base_interest_exact']))
        row['base_interest_match']=Decimal(row['interest_delta_exact'])==0
    return {'view_id':identifier,'case_id':snapshot['case_id'],'deal':snapshot['deal'],
            'filters':{'period':query.get('period') or 'all'},'rows':rows,'source':source,
            'source_receipt_sha256':RECEIPT_SHA,'calendar':list(calendars.values()),
            'contract_evidence':{'url':snapshot['terms']['source_url'],'sha256':PROSPECTUS_SHA,'pdf_pages':[90,91],
                'rule':'30-day average SOFR; second US government securities business day before accrual start; 15:00 New York; previous published government business day fallback; 33bp spread; zero coupon floor'},
            'summary':{'periods':len(rows),'rate_matches':sum(r['rate_value_match'] for r in rows),
                'coupon_matches':sum(r['coupon_match'] for r in rows),'base_interest_matches':sum(r['base_interest_match'] for r in rows),
                'rate_precision_matches':sum(r['rate_precision_match'] for r in rows),
                'coupon_precision_matches':sum(r['coupon_precision_match'] for r in rows),
                'fallback_periods':sum(r['fallback_used'] for r in rows)},
            'qualification':{'current_administrator_value_comparison':True,'historical_1500_publication_vintage_verified':False,
                'administrator_conforming_changes_and_fallback_events_verified':False,'full_contractual_waterfall':False},
            'limitations':['Current administrator snapshot does not prove the 15:00 publication vintage/revisions available at each historical fixing.',
                'SIFMA scheduled full/early closes acquired; unscheduled notices and administrator conforming changes remain unverified.',
                'Independent base-interest comparison does not qualify unpaid carryover, full legal state, collateral forecast or valuation.'],
            'visibility':'private','public_release_approved':False}
