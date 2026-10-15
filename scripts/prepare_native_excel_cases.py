import json,sys
from pathlib import Path
folder=Path(sys.argv[1]).resolve();plan=json.loads((folder/'plan.json').read_text());cases=[]
def case(book,name,changes,expected):
    cases.append({'copy':plan['books'][book]['copy'],'name':name,'changes':[{'sheet':s,'cell':c,'value':v} for s,c,v in changes],
        'expected':[{'sheet':s,'cell':c,'value':v} for s,c,v in expected]})
for name,a,b,h,i in [('delta',3,2,1,.5),('zero',0,0,0,'Unavailable'),('missing_actual',None,2,'Unavailable','Unavailable')]:
    case(0,'KPI_'+name,[('KPI','E6',a),('KPI','G6',b),('KPI','J6',0)],[('KPI','H6',h),('KPI','I6',i)])
for name,n,d,e in [('ratio',100,50,2),('zero_numerator',0,50,0),('missing_numerator',None,50,'Unavailable'),('missing_denominator',100,None,'Unavailable'),('zero_denominator',100,0,'Unavailable'),('text_numerator','Missing',50,'Unavailable')]:
    case(1,'SEC_'+name,[('Facts','D16',n),('Facts','D17',d)],[('Analysis','I23',e),('Analysis','B10',e)])
for name,n,d in [('missing_prior_numerator',None,25),('missing_prior_denominator',100,None),('zero_prior_denominator',100,0)]:
    case(1,'SEC_'+name,[('Facts','D16',100),('Facts','D17',50),('Facts','D14',n),('Facts','D15',d)],
         [('Analysis','I23',2)]+[('Analysis',c+'23','Unavailable') for c in ['J','K','L','M','N','U']])
case(1,'SEC_zero_prior_numerator',[('Facts','D16',100),('Facts','D17',50),('Facts','D14',0),('Facts','D15',25)],
     [('Analysis',c+'23',v) for c,v in [('I',2),('J',0),('K',2),('L',4),('M',-2),('N',0),('U',4)]])
case(2,'maturity_zero',[('Facts','C6',0)],[('Maturities','B9',0),('Maturities','D9',0)])
case(2,'maturity_missing',[('Facts','C6',None)],[('Maturities','B9','Unavailable'),('Maturities','B18','Unavailable'),('Maturities','B20','NUMERIC_INPUT_UNAVAILABLE')])
baseline=.01*.25*609178386.49+.02*.35*297188723.31
case(5,'portfolio_baseline',[('ScenarioModel','B4',1)],[('ScenarioModel','B5','Baseline'),('ScenarioModel','G20',baseline),('Summary','B14',baseline)])
case(5,'portfolio_unselected_missing',[('ScenarioModel','B4',1),('ScenarioModel','E9',None)],[('ScenarioModel','B9',0),('ScenarioModel','G20',baseline)])
case(5,'portfolio_selected_missing',[('ScenarioModel','B4',3),('ScenarioModel','E9',None)],[('ScenarioModel','B9','Unavailable'),('ScenarioModel','G20','Unavailable'),('Summary','B14','Unavailable')])
(folder/'cases.json').write_text(json.dumps({'cases':cases,'output_folder':str(folder)},indent=2),encoding='utf8')
print(len(cases))
