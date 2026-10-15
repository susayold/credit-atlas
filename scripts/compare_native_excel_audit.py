"""Compare native Excel readback with independently extracted saved XML caches."""
import json,sys,re
from pathlib import Path
from decimal import Decimal
from datetime import datetime,timezone
from credit_atlas.workspace import sha256
folder=Path(sys.argv[1]).resolve();plan=json.loads((folder/'plan.json').read_text())
native=json.loads((folder/'native-results.json').read_text(encoding='utf-8-sig'))
differences=[];formula_errors=[];clipped=[];checks=0;formulas=0;numeric=0;summaries=[]
for book,actual in zip(plan['books'],native['books'],strict=True):
    assert book['source']==actual['source'] and actual['read_only']
    assert sha256(Path(book['source']))==book['source_sha256']==sha256(Path(book['copy']))
    values={(x['sheet'],x['cell']):x for x in actual['values']}
    assert len(values)==len(book['cells'])
    count=0;fcount=0
    for item in book['cells']:
        key=(item['sheet'],item['cell']);a=values[key];expected=item['expected'];value=a['value']
        if re.fullmatch(r'#(?:REF!|DIV/0!|VALUE!|NAME\?|N/A|NUM!|NULL!|SPILL!|CALC!)',a['text']):formula_errors.append({'book':book['source'],'sheet':key[0],'cell':key[1],'error':a['text']})
        if re.fullmatch('#{3,}',a['text']):clipped.append({'book':book['source'],'sheet':key[0],'cell':key[1]})
        has_formula=item['formula'] is not None
        if a['has_formula']!=has_formula:differences.append({'book':book['source'],'sheet':key[0],'cell':key[1],'kind':'FORMULA_PRESENCE'})
        if has_formula:formulas+=1;fcount+=1
        if expected is None or expected=='':
            match=value is None or value==''
        elif item['kind']=='d':
            instant=datetime.fromisoformat(expected.replace('Z','+00:00'))
            if instant.tzinfo is None:instant=instant.replace(tzinfo=timezone.utc)
            offset=instant-datetime(1899,12,30,tzinfo=timezone.utc)
            e=Decimal(offset.days)+(Decimal(offset.seconds)+Decimal(offset.microseconds)/1000000)/86400
            match=value is not None and abs(Decimal(str(value))-e)<=Decimal('1e-9')
        elif item['kind'] in ('n','b'):
            numeric+=1
            try:
                e=Decimal(expected);v=Decimal(str(int(value) if isinstance(value,bool) else value))
                tolerance=min(Decimal('0.005'),max(Decimal('1e-12'),abs(e)*Decimal('1e-14')))
                match=v.is_finite() and abs(v-e)<=tolerance
            except Exception:match=False
        else:match=str(value)==expected
        if not match:differences.append({'book':book['source'],'sheet':key[0],'cell':key[1],'expected':expected,'actual':value,'kind':item['kind'],'formula':item['formula']})
        checks+=1;count+=1
    summaries.append({'source':book['source'],'cells':count,'formula_cells':fcount})
result={'status':'PASS' if not differences and not formula_errors else 'FAIL',
    'excel_version':native['excel_version'],'excel_build':native['excel_build'],'workbooks':summaries,
    'cells_compared':checks,'formula_cells_compared':formulas,'numeric_cells_compared':numeric,
    'differences':differences,'formula_errors':formula_errors,'clipped_text_cells':clipped,
    'tolerance':'Numeric max(1e-12,abs(expected)*1e-14), capped at0.005; text/count caches preserved in readback. Baseline calculation only.',
    'originals_unchanged':True,'native_baseline_recalculation_tested':True,'native_input_perturbation_tested':False,
    'native_visual_render_tested':False,'plan_sha256':sha256(folder/'plan.json'),'readback_sha256':sha256(folder/'native-results.json')}
(folder/'receipt.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps({k:result[k] for k in ['status','excel_version','workbooks','cells_compared','formula_cells_compared']}))
print('Differences:',len(differences),'errors:',len(formula_errors),'clipped:',len(clipped))
if differences:print(json.dumps(differences[:6]))
