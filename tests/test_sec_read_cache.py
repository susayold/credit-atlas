import json
from pathlib import Path
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import pytest
from credit_atlas.sec_read_cache import VerifiedSecReadCache
from credit_atlas.workspace import sha256

VIEW='sec-view-111111111111'


@pytest.fixture
def backend(tmp_path):
    case=tmp_path/'artifacts/private/sec-case-222222222222';case.mkdir(parents=True)
    source=tmp_path/'data/private/sec/sec-source-333333333333';source.mkdir(parents=True)
    folder=tmp_path/'artifacts/private'/VIEW;folder.mkdir(parents=True)
    (source/'facts.json').write_text('synthetic source')
    (case/'facts.parquet').write_text('synthetic canonical')
    methods={n:sha256(Path(__file__).parents[1]/'src/credit_atlas'/f'{n}.py') for n in ['sec_views','sec_financials','sec_sources','workspace']}
    (source/'acquisition-complete.json').write_text(json.dumps({'methods':methods,'files':[{'file':'facts.json','sha256':sha256(source/'facts.json')}]}))
    (case/'case-complete.json').write_text(json.dumps({'source_id':source.name,'methods':methods,
        'source_receipt_sha256':sha256(source/'acquisition-complete.json'),'files':{'facts.parquet':sha256(case/'facts.parquet')}}))
    (folder/'snapshot.json').write_text('{}')
    (folder/'view-complete.json').write_text(json.dumps({'case_id':case.name,'methods':methods,
        'case_receipt_sha256':sha256(case/'case-complete.json'),'snapshot_sha256':sha256(folder/'snapshot.json')}))
    counter=[];lock=Lock()
    def full(identifier):
        with lock:counter.append(identifier)
        return {'values':[1,2],'source':'synthetic fixture'}
    return SimpleNamespace(root=tmp_path,methods=methods,view=full,calls=counter)


def test_parallel_reads_verify_once_and_return_isolated_copies(backend):
    cache=VerifiedSecReadCache(backend)
    with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(cache.view,[VIEW]*8))
    assert len(backend.calls)==1 and all(r==results[0] for r in results)
    results[0]['values'].append(9)
    assert cache.view(VIEW)['values']==[1,2]


@pytest.mark.parametrize('target',['source','canonical','snapshot','acquisition','case','anchor'])
def test_each_input_mutation_rejects_cached_projection(backend,target):
    cache=VerifiedSecReadCache(backend);cache.view(VIEW)
    paths={'source':'data/private/sec/sec-source-333333333333/facts.json',
        'canonical':'artifacts/private/sec-case-222222222222/facts.parquet',
        'snapshot':f'artifacts/private/{VIEW}/snapshot.json',
        'acquisition':'data/private/sec/sec-source-333333333333/acquisition-complete.json',
        'case':'artifacts/private/sec-case-222222222222/case-complete.json',
        'anchor':f'artifacts/private/{VIEW}/view-complete.json'}
    path=backend.root/paths[target];path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(ValueError):cache.view(VIEW)
    assert len(backend.calls)==1


def test_verifier_failure_does_not_cache_a_result(backend):
    def fail(_):raise MemoryError('Synthetic verifier allocation failure')
    backend.view=fail;cache=VerifiedSecReadCache(backend)
    with pytest.raises(MemoryError):cache.view(VIEW)
    assert not cache._cached


def test_change_during_full_verification_fails_closed(backend):
    old=backend.view
    def mutating(identifier):
        result=old(identifier)
        (backend.root/'data/private/sec/sec-source-333333333333/facts.json').write_text('changed')
        return result
    backend.view=mutating;cache=VerifiedSecReadCache(backend)
    with pytest.raises(ValueError):cache.view(VIEW)
    assert not cache._cached
