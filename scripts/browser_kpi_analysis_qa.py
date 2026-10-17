"""Independently reconcile KPI derivations with source API evidence and rendered scopes."""
import json
import uuid
import urllib.request
from decimal import Decimal
from playwright.sync_api import sync_playwright,expect
from credit_atlas.workspace import app_root,sha256


def run():
    root=app_root();out=root/'artifacts/private'/('kpi-analysis-qa-'+uuid.uuid4().hex[:12]);out.mkdir()
    base='http://127.0.0.1:8770';checks=[];errors=[];ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1600,'height':1050},accept_downloads=True)
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(base+'/?view=monitor')
        expect(page.get_by_role('button',name='Xuất monitor JSON',exact=True)).to_be_enabled(timeout=180000)
        expect(page.locator('.kpi-analysis-body')).to_have_attribute('data-analysis-domain','P2')
        with page.expect_download() as pending:page.get_by_role('button',name='Xuất monitor JSON',exact=True).click()
        pending.value.save_as(out/'analysis-all.json');report=json.loads((out/'analysis-all.json').read_text());a=report['kpi_analysis']
        assert set(a)=={'P1','P2','P3','P4','P5'}
        assert sum(len(r['metrics']) for r in a.values())==88
        def metric(d,name):return next(m for m in a[d]['metrics'] if m['name']==name)
        snap=json.load(urllib.request.urlopen(base+'/api/snapshot?run=d01-a24484b21a21'));last=snap['snapshot']['monthly'][-1];prior=snap['snapshot']['monthly'][-2]
        assert abs(metric('P2','D3 share — selected basis')['value']-last['d3_active_loans']/last['state_usable_active_loans'])<1e-12
        decomp=a['P2']['decomposition'];assert abs(decomp['numerator_effect']+decomp['denominator_effect']-(last['d3_count_share']-prior['d3_count_share']))<1e-12
        assert metric('P2','Reported loss sum')['value']==snap['snapshot']['loss_summary']['reported_loss_sum_usd']
        checks.append('Mortgage ratio/support, monthly arithmetic decomposition and observed-loss source parity')
        ts=report['data']['P2']['migration']['lifetime_rows'];ts=[x for x in ts if x['segment']=='all']
        assert metric('P2','Adjacent pairs — lifetime')['value']==sum(x['pairs'] for x in ts)
        for origin in {x['origin'] for x in ts}:
            rs=[x for x in ts if x['origin']==origin];assert sum(x['pairs'] for x in rs)==rs[0]['origin_pairs'];assert abs(sum(x['count_probability'] for x in rs)-1)<1e-9
        for origin,destination in [('CURRENT','D3PLUS'),('D3PLUS','CURRENT')]:
            rs=[x for x in ts if x['origin']==origin];num=sum(x['pairs'] for x in rs if x['destination']==destination)
            assert abs(metric('P2',origin+' → '+destination+' adjacent share')['value']-num/rs[0]['origin_pairs'])<1e-12
        fr=report['data']['P2']['followup']['rows']
        for event in ['FIRST_OBSERVED_D3','SUSTAINED_CURE_CONFIRMED']:
            rs=[x for x in fr if x['segment']=='all' and x['horizon_months']==12 and x['event_type']==event];total=sum(x['events'] for x in rs);complete=sum(x['events'] for x in rs if x['followup_status']=='complete_nonterminal_followup')
            assert total==snap['episode_notes']['episode_events'][event]
            assert metric('P2',event+' complete 12m follow-up share')['value']==complete/total
        checks.append('Lifetime transitions reconcile every origin row; count rates and confirmed-event follow-up supports independently verified')
        suite=json.load(urllib.request.urlopen(base+'/api/suite-view?view_id=suite-view-74e07524f6d0'));h=suite['retail']['holdout'];gap=sum(b['loans']*abs(b['mean_probability']-b['observed_rate']) for b in h['reliability_bins'] if b['loans'])/h['loans']
        assert abs(metric('P1','Weighted absolute bin gap')['value']-gap)<1e-12
        assert metric('P1','Event prevalence')['value']==664/3001
        checks.append('Retail saved population and calibration-gap derivation; empty bins excluded from weighted gap')
        policy=report['data']['P1']['policy'];assert policy['partition']=='validation';c=next(x for x in policy['cases'] if x['id']=='lower_thresholds');matrix=policy['assumptions']['cost_matrix']
        assert sum(x['records'] for x in c['actions'])==4499 and sum(x['events'] for x in c['actions'])==995
        assert metric('P1','Scenario review overflow')['value']==max(0,c['review_records']-600)==1677
        for action in c['actions']:
            assert metric('P1','Scenario '+action['action']+' share')['value']==action['records']/4499
        for case in policy['cases']:
            expected=sum(Decimal(x['expected_declared_cost']['decimal_50']) for x in case['actions']);retro=sum(Decimal(matrix[x['action']]['event'])*x['events']+Decimal(matrix[x['action']]['non_event'])*x['non_events'] for x in case['actions'])
            assert abs(expected-Decimal(case['expected_declared_cost']['decimal_50']))<Decimal('1e-20');assert retro==Decimal(case['retrospective_cost_proxy']['decimal_50'])
        assert abs(metric('P1','Expected declared cost')['value']-4808.640601138364)<1e-9
        assert a['P1']['policy_scope']['case_id']=='lower_thresholds' and a['P1']['policy_scope']['cost_unit']=='declared_cost_units'
        checks.append('Saved validation policy action totals/shares/overflow and all scenario cost decompositions; declared units and partition retained')

        e=report['data']['P4'];hhi=sum(float(x['amount_share'])**2 for x in e['concentrations']);assert abs(metric('P4','Geographic HHI')['value']-hhi)<1e-12
        assert metric('P4','Research EL')['value'] is None
        assert report['provenance'][next(i for i,x in enumerate(report['provenance']) if x['domain']=='P4')]['comparison_source']['identifier']=='exposure-import-facfbef3f419'
        assert metric('P4','Reported sample UPB')['unit']=='USD'
        assert 'Freddie Mac 2012 annual sample' in a['P4']['scope'] and 'not owned book/EAD' in a['P4']['scope']
        assert abs(metric('P4','Reported sample UPB')['comparison']['absolute_change']-(915208989.12-928246113.34))<1e-6
        checks.append('Freddie sample geographic HHI, exact comparison import lineage, UPB movement and null EL')
        bridge=a['P4']['region_bridge'];assert bridge['reconciliation']=='EXACT_CENTS_PASS'
        source_now={r['bucket']:r for r in e['concentrations']};source_prior={r['bucket']:r for r in e['previous']['concentrations']}
        assert {r['bucket'] for r in bridge['rows']}==set(source_now)|set(source_prior)
        for r in bridge['rows']:
            n=Decimal(source_now.get(r['bucket'],{}).get('reported_amount_major_exact','0'));old=Decimal(source_prior.get(r['bucket'],{}).get('reported_amount_major_exact','0'))
            assert Decimal(r['current_amount_exact'])==n and Decimal(r['prior_amount_exact'])==old and Decimal(r['delta_exact'])==n-old
        assert sum(Decimal(r['delta_exact']) for r in bridge['rows'])==Decimal(bridge['total_delta_exact'])==Decimal('915208989.12')-Decimal('928246113.34')
        assert abs(sum(r['contribution_to_prior_total'] for r in bridge['rows'])-float(Decimal(bridge['total_delta_exact'])/Decimal(bridge['prior_total_exact'])))<1e-12
        checks.append('Every region delta independently reconciled with Decimal source values; total exact cents and additive prior-total contributions')
        boundary=page.evaluate('''() => {
          const snap=(period,total,rows)=>({as_of:period,date_grain:"month",amount_kind:"principal",source_namespace:"test",filters:{dimension:"region"},currencies:[{currency:"USD",reported_amount_major_exact:total}],concentrations:rows.map(([bucket,amount])=>({bucket,reported_amount_major_exact:amount,records:1}))});
          const prior=snap("2026-02","10.00",[["old","10.00"]]),now=snap("2026-03","12.00",[["new","12.00"]]);
          const union=kpiRegionBridge(now,prior),zero=kpiRegionBridge(now,snap("2026-02","0.00",[]));
          let mismatch=false;try{kpiRegionBridge(snap("2026-03","13.00",[["new","12.00"]]),prior);}catch(e){mismatch=true;}
          return {union:union.rows.map(x=>[x.bucket,x.delta_exact,x.presence]),zero:zero.rows.every(x=>x.contribution_to_prior_total===null),missing:kpiRegionBridge(now,null)===null,same:kpiRegionBridge(now,{...prior,as_of:now.as_of})===null,scope:kpiRegionBridge(now,{...prior,filters:{dimension:"sector"}})===null,mismatch};
        }''')
        assert boundary['union']==[['old','-10.00','Prior snapshot only'],['new','12.00','Current snapshot only']]
        assert all(boundary[k] for k in ['zero','missing','same','scope','mismatch'])
        checks.append('Region bridge union/absent buckets, zero denominator, unavailable prior, incompatible scope and inconsistent totals safeguards')
        for program in ['7A','504']:
            rs=[r for r in suite['business']['aggregates']['dimensions']['program_status'] if r['program']==program];total=sum(r['records'] for r in rs);charged=next(r['records'] for r in rs if r['status']=='charged_off');assert metric('P3',program+' charged-off status share')['value']==charged/total
        absdata=report['data']['P5'];period=absdata['period_options'][-1];notes=sum(float(v) for v in period['ending_balances'].values());assert abs(metric('P5','Adjusted pool surplus')['value']-(float(period['ending_pool'])-notes))<1e-6
        checks.append('SBA program-specific denominators and ABS reported pool-minus-notes derivation')
        pr=absdata['period_report'];abs_ledger=pr['period']['result']['ledger'];inputs=pr['period']['inputs'];br=a['P5']['cash_bridge'];assert br['reconciliation']=='EXACT_CENTS_PASS'
        assert Decimal(br['cash_residual_exact'])==Decimal(inputs['available_funds'])-sum(Decimal(x['from_available_funds']) for x in abs_ledger)-Decimal(abs_ledger[-1]['cash_after'])==0
        assert Decimal(br['reserve_residual_exact'])==Decimal(inputs['reserve_beginning'])+sum(Decimal(x['reserve_credit'])-Decimal(x['reserve_draw']) for x in abs_ledger)-Decimal(abs_ledger[-1]['reserve_after'])==0
        for i,row in enumerate(abs_ledger):
            assert Decimal(row['cash_before'])-Decimal(row['from_available_funds'])==Decimal(row['cash_after']);assert Decimal(row['reserve_before'])+Decimal(row['reserve_credit'])-Decimal(row['reserve_draw'])==Decimal(row['reserve_after'])
            if i:assert row['cash_before']==abs_ledger[i-1]['cash_after'] and row['reserve_before']==abs_ledger[i-1]['reserve_after']
        assert metric('P5','Replay interest paid')['value']==float(sum(Decimal(x) for x in pr['period']['result']['interest_paid'].values()))
        assert br['period']==absdata['period_options'][-1]['collection_end'] and pr['qualification']['full_contractual_waterfall'] is False
        checks.append('Selected ABS replay all cash/reserve steps and sequence independently reconciled with Decimal; payout/period parity and legal qualification retained')

        issuers=report['data']['P3']['issuers'];assert len(issuers)==4
        names={'current_ratio':'Current ratio','liabilities_assets':'Liabilities / assets','net_income_margin':'Net income margin','operating_cashflow_revenue':'Operating cashflow / revenue'}
        for p in issuers:
            st=p['statement'];assert st and st['filing_date']<=p['filters']['asof'] and st['accession']==p['filters']['accession']
            for key,label in names.items():
                ratio=st['ratios'][key];actual=metric('P3',p['entity']['ticker']+' · '+label)['value']
                if ratio['value_exact'] is None:assert actual is None
                else:
                    n=Decimal(st['fields'][ratio['numerator']]['value_exact']);d=Decimal(st['fields'][ratio['denominator']]['value_exact']);assert abs(actual-float(n/d))<1e-12
            for field in st['fields'].values():
                for evi in field['evidence']:assert evi['unit']=='USD' and evi['filed_date']==st['filing_date'] and evi['end_date']==st['report_date']
        assert metric('P3','F · Net income margin')['value'] is None
        assert metric('P3','GM · Net income margin')['value'] is None
        checks.append('Four issuer ratio calculations independently reconcile exact field values, filing cutoff/period/units; missing Ford and ambiguous GM retained')

        quality={d:r['data_quality'] for d,r in a.items()};assert sum(len(q['metrics']) for q in quality.values())==22
        def control(d,name):return next(x for x in quality[d]['metrics'] if x['name']==name)
        assert control('P1','Reliability support coverage')['value']==1 and control('P1','Raw feature missingness')['value'] is None
        assert control('P2','original_dti missing share')['value']==17400/50000
        for x in report['data']['P2']['quality']['integrity_checks']:assert control('P2',x['check'])['value']==x['value']
        sq=report['data']['P3']['quality'];total=sum(x['retained_rows'] for x in sq.values());duplicates=sum(x['exact_duplicate_excess_rows'] for x in sq.values())
        assert len(sq)==6 and control('P3','SBA retained source rows')['value']==total==2190504 and control('P3','SBA exact duplicate excess share')['value']==duplicates/total
        assert control('P4','Region record coverage')['value']==1 and control('P4','Missing amount share')['value'] is None
        assert control('P5','Failed source-check share')['value']==0/720 and control('P5','Verified cash/reserve ledger steps')['value']==len(abs_ledger)
        checks.append('22 quality controls independently reconcile source populations, missingness, retained duplicate rates, partition checks and unavailable profiles')
        for domain in ['P1','P2','P3','P4','P5']:
            page.locator('.kpi-analysis-nav').get_by_role('button',name=domain+' · '+{'P1':'Retail','P2':'Mortgage','P3':'Business','P4':'Portfolio','P5':'Structured'}[domain],exact=True).click()
            expect(page.locator('.kpi-analysis-body')).to_have_attribute('data-analysis-domain',domain)
            assert page.locator('#kpi-analysis-metrics tbody tr').count()==len(a[domain]['metrics'])
            assert 'KPI cần dữ liệu' in page.locator('.kpi-analysis-body').inner_text()
            assert page.locator('.kpi-data-quality tbody tr').count()>=len(quality[domain]['metrics']) and 'Chất lượng dữ liệu' in page.locator('.kpi-data-quality').inner_text()
            if domain=='P3':
                links=page.locator('.kpi-analysis-body a');assert links.count()==4
                href=links.first.get_attribute('href');assert 'sec_accession=' in href and 'sec_cik=0000320193' in href
            if domain=='P4':
                section=page.locator('.kpi-source-table').filter(has=page.get_by_text('Phân rã biến động theo vùng — exact-cent bridge',exact=True));section.locator('summary').click();assert section.locator('tbody tr').count()==len(bridge['rows'])
            page.locator('#monitor-kpi-analysis').screenshot(path=str(out/(domain+'-analysis.png')))
        checks.append('88 rendered KPI rows across all domains, formulas/interpretation and explicit missing KPI dependencies')
        def export_at(name):
            with page.expect_download() as pending:page.get_by_role('button',name='Xuất monitor JSON',exact=True).click()
            pending.value.save_as(out/name);return json.loads((out/name).read_text())['kpi_analysis']
        page.locator('.kpi-analysis-nav').get_by_role('button',name='P2 · Mortgage',exact=True).click()
        manual=snap['snapshot']['monthly'][-13]['period'];page.get_by_label('KPI baseline P2',exact=True).select_option(manual)
        selected=export_at('analysis-manual-mortgage.json')['P2'];assert selected['comparison_control']['resolved_period']==manual
        previous=next(x for x in snap['snapshot']['monthly'] if x['period']==manual)
        change=next(x['comparison']['absolute_change'] for x in selected['metrics'] if x['name']=='Active loans');assert change==last['active_loans']-previous['active_loans']
        page.get_by_label('KPI baseline P2',exact=True).select_option('none');disabled=export_at('analysis-baseline-disabled.json')['P2'];assert disabled['decomposition']['total_change'] is None and disabled['metrics'][0]['comparison'] is None
        page.get_by_label('KPI baseline P2',exact=True).select_option('auto')
        page.locator('.kpi-analysis-nav').get_by_role('button',name='P5 · Structured',exact=True).click();period=absdata['period_options'][0]['collection_end'];page.get_by_label('KPI baseline P5',exact=True).select_option(period)
        selected=export_at('analysis-manual-abs.json')['P5'];assert selected['comparison_control']['resolved_period']==period and selected['cash_bridge']['period']==absdata['period_options'][-1]['collection_end']
        assert abs(selected['metrics'][0]['comparison']['absolute_change']-(float(absdata['period_options'][-1]['ending_pool'])-float(absdata['period_options'][0]['ending_pool'])))<1e-6
        page.get_by_label('KPI baseline P5',exact=True).select_option('auto');page.locator('.kpi-analysis-nav').get_by_role('button',name='P4 · Portfolio',exact=True).click();page.get_by_label('KPI baseline P4',exact=True).select_option('none')
        disabled=export_at('analysis-portfolio-disabled.json')['P4'];assert disabled['region_bridge'] is None and disabled['metrics'][0]['comparison'] is None
        page.get_by_label('KPI baseline P4',exact=True).select_option('auto')
        gates=page.evaluate("""() => {const rows=[{period:'2025-01-01'},{period:'2025-03-01'}];return [kpiBaseline(rows,'auto').control.status,kpiBaseline(rows,'2025-03-01').control.status,kpiBaseline(rows,'2024-12-01').control.status,kpiBaseline(rows,'2025-01-01').control.status,kpiBaseline([{period:'2025-01-01'},{period:'2025-01-02'},{period:'2025-02-01'}],'auto').control.status];}""")
        assert gates==['NO_UNIQUE_PREVIOUS_CALENDAR_MONTH','UNAVAILABLE_OR_NOT_PRIOR','UNAVAILABLE_OR_NOT_PRIOR','EXACT_SELECTED_PERIOD','NO_UNIQUE_PREVIOUS_CALENDAR_MONTH']
        checks.append('Exact manual/disabled/calendar baseline selection, no nearest fallback for gaps/current/unknown/ambiguous months; stock and replay scopes separated')
        page.get_by_label('Monitor domain',exact=True).select_option('P2');page.get_by_label('Mortgage history',exact=True).select_option('12');page.get_by_label('Mortgage D3 basis',exact=True).select_option('balance')
        with page.expect_download() as pending:page.get_by_role('button',name='Xuất monitor JSON',exact=True).click()
        pending.value.save_as(out/'analysis-P2.json');filtered=json.loads((out/'analysis-P2.json').read_text());assert list(filtered['kpi_analysis'])==['P2'];assert len(filtered['kpi_analysis']['P2']['tables'][1]['rows'])==12
        assert abs(next(m['value'] for m in filtered['kpi_analysis']['P2']['metrics'] if m['name']=='D3 share — selected basis')-last['d3_balance_share'])<1e-12
        fm=filtered['kpi_analysis']['P2'];assert fm['migration_scope']['history_window_applies'] is False
        for origin,destination in [('CURRENT','D3PLUS'),('D3PLUS','CURRENT')]:
            rs=[x for x in ts if x['origin']==origin];num=sum(x['opening_upb'] for x in rs if x['destination']==destination)
            v=next(x['value'] for x in fm['metrics'] if x['name']==origin+' → '+destination+' adjacent share');assert abs(v-num/rs[0]['origin_opening_upb'])<1e-12
        page.get_by_label('KPI baseline P2',exact=True).select_option(manual)
        page.reload();expect(page.get_by_role('button',name='Xuất monitor JSON',exact=True)).to_be_enabled(timeout=180000);expect(page.locator('.kpi-analysis-body')).to_have_attribute('data-analysis-domain','P2')
        assert page.get_by_label('KPI baseline P2',exact=True).input_value()==manual
        checks.append('Filtered/exported/reloaded analysis matches domain, 12-month history and UPB basis')
        page.set_viewport_size({'width':390,'height':844});page.locator('#monitor-kpi-analysis').scroll_into_view_if_needed();assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1');page.screenshot(path=str(out/'analysis-mobile.png'))
        checks.append('Mobile KPI tables scroll within section; no page overflow at390px')
        fail=browser.new_page();fail.on('pageerror',lambda e:errors.append(str(e)));fail.route('**/api/retail-policy?*',lambda route:route.abort())
        fail.route('**/api/sec-report?*cik=0001467858*',lambda route:route.abort());fail.route('**/api/abs-period?*',lambda route:route.abort());fail.goto(base+'/?view=monitor');expect(fail.get_by_role('button',name='Xuất monitor JSON',exact=True)).to_be_enabled(timeout=180000)
        with fail.expect_download() as pending:fail.get_by_role('button',name='Xuất monitor JSON',exact=True).click()
        pending.value.save_as(out/'analysis-policy-unavailable.json');failed_report=json.loads((out/'analysis-policy-unavailable.json').read_text());unavailable=failed_report['kpi_analysis']['P1']
        assert unavailable['policy_scope']['policy_id'] is None and all(x['value'] is None for x in unavailable['metrics'][9:])
        assert len(unavailable['metrics'])==18
        gm=[x for x in failed_report['kpi_analysis']['P3']['metrics'] if x['name'].startswith('GM ·')];assert len(gm)==4 and all(x['value'] is None for x in gm)
        assert next(x['value'] for x in failed_report['kpi_analysis']['P3']['metrics'] if x['name']=='AAPL · Current ratio') is not None
        checks.append('Single-issuer SEC outage preserves four unavailable issuer KPIs and other issuers/source population')
        absent_abs=failed_report['kpi_analysis']['P5'];assert absent_abs['cash_bridge'] is None and all(x['value'] is None for x in absent_abs['metrics'][9:]);assert absent_abs['metrics'][0]['value'] is not None
        checks.append('ABS ledger outage preserves source period KPIs and unavailable replay KPIs without fabricated payout')
        fail.close();checks.append('Unavailable policy preserves model results and nine unavailable scenario KPIs; no invented costs or capacity')
        browser.close()
    assert not errors,errors;assert before==sha256(ledger)
    checks.append('No browser exceptions; frozen holdout access ledger unchanged')
    (out/'receipt.json').write_text(json.dumps({'status':'PASS','checks':checks,'errors':errors,'metric_count':88,'quality_control_count':22,'holdout_ledger_unchanged':True},ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'status':'PASS','checks':len(checks),'receipt':str(out/'receipt.json')},ensure_ascii=False))


if __name__=='__main__':run()
