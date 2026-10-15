import pytest
from credit_atlas.retail_subgroups_saved import supported_methods,LEGACY_POLICY_SERVING_SHA256
from credit_atlas.retail_subgroups import methods

def test_exact_legacy_adapter_migration_only():
    current=methods()
    assert supported_methods(current)
    assert supported_methods({**current,'retail_policy_views':LEGACY_POLICY_SERVING_SHA256})
    assert not supported_methods({**current,'retail_policy_views':'0'*64})

@pytest.mark.parametrize('key',['retail_subgroups','retail_policy'])
def test_numerical_engine_changes_never_accepted(key):
    assert not supported_methods({**methods(),key:'0'*64,'retail_policy_views':LEGACY_POLICY_SERVING_SHA256})

def test_unknown_method_or_missing_provenance_rejected():
    assert not supported_methods({**methods(),'unknown':'a'*64})
    assert not supported_methods(None)
