"""Run the complete collected suite in sequential fresh processes on D:."""
import argparse
import collections
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from xml.etree import ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from credit_atlas.workspace import app_root,timestamp,write_new

def run(batch_files):
    root=app_root(); identifier=uuid.uuid4().hex[:12]
    output=root/'artifacts/private'/('test-batches-'+identifier); output.mkdir()
    scratch=Path('D:/data/Codex/scratch/credit-atlas-tests')/identifier; scratch.mkdir(parents=True)
    import_roots=[root/'src',root/'vendor/credit_risk_strategy_lab/src',root/'vendor/credit_risk_strategy_lab']
    inherited=os.environ.get('PYTHONPATH','')
    pythonpath=os.pathsep.join([*(str(path) for path in import_roots),*([inherited] if inherited else [])])
    environment={**os.environ,'PYTHONPATH':pythonpath,'PYTHONDONTWRITEBYTECODE':'1','TEMP':str(root/'.tmp'),'TMP':str(root/'.tmp')}
    (root/'.tmp').mkdir(exist_ok=True)
    command=[sys.executable,'-m','pytest','-c','pyproject.toml']
    collection=subprocess.run(command+['tests','vendor/credit_risk_strategy_lab/tests','--collect-only','-q'],cwd=root,env=environment,capture_output=True,text=True,encoding='utf-8')
    (output/'collection.log').write_text(collection.stdout+collection.stderr,encoding='utf-8')
    if collection.returncode: raise RuntimeError('Complete-suite collection failed: '+str(output/'collection.log'))
    nodes=[line.strip() for line in collection.stdout.splitlines() if '::' in line and (root/line.split('::',1)[0]).is_file()]
    if not nodes or len(nodes)!=len(set(nodes)): raise RuntimeError('Complete unique collection required')
    counts=collections.Counter(node.split('::',1)[0] for node in nodes); files=sorted(counts)
    batches=[files[i:i+batch_files] for i in range(0,len(files),batch_files)]; results=[]
    for index,selected in enumerate(batches,1):
        expected=sum(counts[path] for path in selected); xml=output/f'batch-{index:02}.xml'
        invocation=command+selected+['--basetemp',str(scratch/f'batch-{index:02}'),'--junitxml',str(xml),'-q']
        print(f'Batch {index}/{len(batches)}: {len(selected)} files, {expected} collected tests',flush=True)
        completed=subprocess.run(invocation,cwd=root,env=environment,capture_output=True,text=True,encoding='utf-8')
        (output/f'batch-{index:02}.log').write_text(completed.stdout+completed.stderr,encoding='utf-8')
        totals={'tests':0,'failures':0,'errors':0,'skipped':0}
        if xml.exists():
            for suite in ET.parse(xml).getroot().iter('testsuite'):
                for key in totals: totals[key]+=int(suite.attrib.get(key,0))
        ok=completed.returncode==0 and totals['tests']==expected and not totals['failures'] and not totals['errors']
        results.append({'batch':index,'files':selected,'expected_tests':expected,'exit_code':completed.returncode,'junit':totals,'status':'PASS' if ok else 'FAIL'})
        print(json.dumps({'batch':index,'status':results[-1]['status'],'counts':totals}),flush=True)
        if not ok: print(completed.stdout[-3000:],flush=True)
    ok=all(r['status']=='PASS' for r in results) and sum(r['junit']['tests'] for r in results)==len(nodes)
    receipt={'status':'PASS' if ok else 'FAIL','completed_at':timestamp(),'collected_tests':len(nodes),
        'files':len(files),'batch_files':batch_files,'batches':results,'all_collected_nodes_executed':sum(r['junit']['tests'] for r in results)==len(nodes),
        'policy':'Fresh sequential processes; no omitted tests or automatic failure retries',
        'visibility':'private','public_release_approved':False}
    write_new(output/'receipt.json',receipt)
    print(json.dumps({'status':receipt['status'],'collected_tests':len(nodes),'receipt':str(output/'receipt.json')}),flush=True)
    return 0 if ok else 1

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--batch-files',type=int,default=8);args=parser.parse_args()
    if not 1<=args.batch_files<=32: parser.error('--batch-files must be between 1 and 32')
    raise SystemExit(run(args.batch_files))
