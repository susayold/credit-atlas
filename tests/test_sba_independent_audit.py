from datetime import date
from decimal import Decimal
import pytest
from scripts.audit_sba_june_acceptance import typed, quality_flags, buckets


def source(**overrides):
    row = {'Program':' 7A','LoanStatus':'EXEMPT','AsOfDate':'2026-06-30','ApprovalDate':'2025-10-01',
        'FirstDisbursementDate':'','PaidInFullDate':'','ChargeOffDate':'','GrossApproval':'9007199254740993.123456789123456789',
        'GrossChargeOffAmount':'0','SBAGuaranteedApproval':'','ApprovalFY':'2026','TermInMonths':'120','JobsSupported':'0',
        'InitialInterestRate':'','LocationID':'lender','ProjectState':'','NaicsCode':'abc','BusinessType':'','BusinessAge':'','ProcessingMethod':''}
    row.update(overrides);return row


def test_unknown_and_withheld_are_not_negative_labels():
    r = typed(source(), '7A','source',1)
    assert r['status'] == 'disbursed_status_withheld' and r['third_party_amount'] is None
    assert r['reported_approval_amount'] == Decimal('9007199254740993.123456789123456789')
    assert r['jobs_supported'] == 0 and r['initial_rate_pct'] is None
    r = typed(source(LoanStatus='future_unknown'), '7A','source',2)
    assert r['status'] == 'unmapped' and quality_flags(r)['unmapped_status']


def test_fiscal_boundary_and_independent_dimensions():
    r = typed(source(), '7A','source',1)
    assert not quality_flags(r)['fiscal_year_mismatch']
    assert buckets(r) == {'program_status':'all','approval_fiscal_year':'2026','project_state':'__unavailable__','naics_two_digit':'__unavailable__'}
    r = typed(source(ApprovalDate='2025-09-30',ApprovalFY='2025',NaicsCode='541330',ProjectState=' CA '), '7A','source',1)
    assert not quality_flags(r)['fiscal_year_mismatch'] and buckets(r)['naics_two_digit']=='54'
    assert buckets(r)['project_state'] == 'CA'


def test_missing_outcome_signed_amount_and_dates_remain_flags():
    r = typed(source(LoanStatus='CHGOFF',GrossApproval='-1',GrossChargeOffAmount='2',FirstDisbursementDate='2025-09-01'), '7A','source',1)
    flags = quality_flags(r)
    assert flags['charged_off_missing_date'] and flags['signed_negative_amount']
    assert flags['chargeoff_exceeds_approval'] and flags['disbursement_before_approval']
    assert r['reported_approval_amount'] == -1


def test_no_rounding_of_nonintegral_integer():
    with pytest.raises(ValueError,match='Nonintegral'):typed(source(JobsSupported='1.2'),'7A','source',1)


def test_504_legacy_status_and_source_row_identity():
    r = typed(source(Program='504',LoanStatus='CLOSED'), '504','source',17)
    assert r['status'] == 'closed_other_legacy' and r['source_record_key'] == 'source:17'
    assert r['approval_date'] == date(2025,10,1)
