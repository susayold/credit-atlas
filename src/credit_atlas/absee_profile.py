"""Quarantined mirror structural profile. Does not qualify credit labels or source fidelity."""
from collections import Counter
from datetime import datetime
from decimal import Decimal
from pathlib import Path
import pyarrow.parquet as pq
from .workspace import contained,read_json,sha256

SOURCE='absee-mirror-f97dcd09916d'
RECEIPT='482aff4e853f68cdb718c6251fd4355eeea7d96c1cc32bfb8a4449ab443b49f1'
OFFICIAL_KPI='artifacts/private/woart-absee-official-kpi-report-635e871305b5/kpis.json'
OFFICIAL_KPI_RECEIPT='artifacts/private/woart-absee-official-kpi-report-635e871305b5/receipt.json'
OFFICIAL_KPI_SHA256='493daf113f66c895710b4e8803c5b42d586d7ec450201672b313676ba8bc7fb3'
FEATURE_AUDIT='artifacts/private/woart-absee-feature-anomaly-audit-4458d2d6bb1a/audit.json'
FEATURE_AUDIT_RECEIPT='artifacts/private/woart-absee-feature-anomaly-audit-4458d2d6bb1a/receipt.json'
FEATURE_AUDIT_SHA256='bdcdb30de97dfffe3baf5fe2d3ea1cf5b68dcb0987ce3fa85a64652d2b1c8c84'
PEER_SAMPLES=[
    ('artifacts/private/sec-auto-abs-peer-profile-0931a69b6d7d/profile.json',
     'artifacts/private/sec-auto-abs-peer-profile-0931a69b6d7d/receipt.json',
     '69e606b4d5619beef4e32f1b55beb144d1d39ae05a21cacbb6c4f04868297262',
     'Toyota Auto Receivables 2026-C Owner Trust',46601,57),
    ('artifacts/private/sec-auto-abs-peer-profile-c431b5e89405/profile.json',
     'artifacts/private/sec-auto-abs-peer-profile-c431b5e89405/receipt.json',
     '9be63f80b8c13de3eb6c26af43c955abbdfef68f51e4c5b2473c005f1946da73',
     'Toyota Auto Receivables 2022-B Owner Trust',20916,62),
]
TOYOTA_HISTORY_AUDIT='artifacts/private/toyota-2022b-absee-panel-audit-c9fbf983fa4e/audit.json'
TOYOTA_HISTORY_RECEIPT='artifacts/private/toyota-2022b-absee-panel-audit-c9fbf983fa4e/receipt.json'
TOYOTA_HISTORY_SHA256='64da7c7b10b160909b24e22d4ab25ea8d99c8750bbecd89d3aa7aceb4f7753b9'
TOYOTA_TARGET_AUDIT='artifacts/private/toyota-2022b-target-feasibility-cb7b6624bc3f/audit.json'
TOYOTA_TARGET_RECEIPT='artifacts/private/toyota-2022b-target-feasibility-cb7b6624bc3f/receipt.json'
TOYOTA_TARGET_SHA256='7e5c8fb340b31e13b522b91489fe7aecd1bf1b118957c5fff427af7e09e78449'
TOYOTA_EX103_PROFILE='artifacts/private/toyota-2022b-ex103-profile-af05e72ef9c3/profile.json'
TOYOTA_EX103_RECEIPT='artifacts/private/toyota-2022b-ex103-profile-af05e72ef9c3/receipt.json'
TOYOTA_EX103_SHA256='665a5d845ef3ad355e7b9dd51130535b41d328feccb2c9a868b3d07c7e076df8'
TOYOTA_TEMPORAL_AUDIT='artifacts/private/toyota-2022b-temporal-split-70fdbfa168fc/audit.json'
TOYOTA_TEMPORAL_RECEIPT='artifacts/private/toyota-2022b-temporal-split-70fdbfa168fc/receipt.json'
TOYOTA_TEMPORAL_SHA256='eea8a4799f22fb2d9e46b935de582232215b4c63a8cc8f56450f78b9241af222'
TOYOTA_10D_ACQUISITION='data/private/structured/toyota-2022b-10d-certificates-941fa44791c8/acquisition-complete.json'
TOYOTA_CERTIFICATE_AUDIT='artifacts/private/toyota-2022b-certificate-tieout-cec933ed357e/audit.json'
TOYOTA_CERTIFICATE_RECEIPT='artifacts/private/toyota-2022b-certificate-tieout-cec933ed357e/receipt.json'
TOYOTA_CERTIFICATE_SHA256='7d1403ab1d2b1c602a8843cd1d7d9e353b423b78cf5c41ed80d798354238c41f'
TOYOTA_FEATURE_AUDIT='artifacts/private/toyota-2022b-feature-availability-2d031c8fcb66/audit.json'
TOYOTA_FEATURE_RECEIPT='artifacts/private/toyota-2022b-feature-availability-2d031c8fcb66/receipt.json'
TOYOTA_FEATURE_SHA256='affcb49eb007e40dc4d43c546ff8b3c8e2ec8b8e1d905d1eb550371c04c4cca6'
TOYOTA_2024B_HISTORY_AUDIT='artifacts/private/toyota-2024b-absee-panel-audit-148e4a9f9a76/audit.json'
TOYOTA_2024B_HISTORY_RECEIPT='artifacts/private/toyota-2024b-absee-panel-audit-148e4a9f9a76/receipt.json'
TOYOTA_2024B_HISTORY_SHA256='9afc0e0a6af3385e4b7822d827b1d0b704f24258c8c256fbbea1c749e881a02c'
TOYOTA_2024B_CERTIFICATE_AUDIT='artifacts/private/toyota-2024b-certificate-tieout-6223784d25dd/audit.json'
TOYOTA_2024B_CERTIFICATE_RECEIPT='artifacts/private/toyota-2024b-certificate-tieout-6223784d25dd/receipt.json'
TOYOTA_2024B_CERTIFICATE_SHA256='2ecd94dbfadaeb2517e13ac9a8cd5a3ae23148ac77ff5778ec818ade8a9107b4'
NISSAN_2024B_ACQUISITION='data/private/structured/nissan-2024b-validation-panel-7cd3605b4e07/acquisition-complete.json'
NISSAN_2024B_PANEL='data/private/derived/nissan-2024b-validation-panel-9534e22c34fc/dataset-complete.json'
NISSAN_2024B_PANEL_AUDIT='artifacts/private/nissan-2024b-absee-panel-audit-8b5590abd3d5/audit.json'
NISSAN_2024B_PANEL_AUDIT_RECEIPT='artifacts/private/nissan-2024b-absee-panel-audit-8b5590abd3d5/receipt.json'
NISSAN_2024B_PANEL_AUDIT_SHA256='33f72cc4e9dfa8798b5bf33307340de3754783152d21d47781dd9549c0e2adc2'
NISSAN_2024B_CERTIFICATE_AUDIT='artifacts/private/nissan-2024b-certificate-tieout-d7a71f85c77c/audit.json'
NISSAN_2024B_CERTIFICATE_RECEIPT='artifacts/private/nissan-2024b-certificate-tieout-d7a71f85c77c/receipt.json'
NISSAN_2024B_CERTIFICATE_SHA256='899ba82f689d8efecc665d3c4d68211375bfb3780dcc35b61e8f9cb3a75163ea'
NISSAN_2024B_SUBMISSIONS_AUDIT='artifacts/private/nissan-2024b-submission-refresh-a26fc17a6676/audit.json'
NISSAN_2024B_SUBMISSIONS_RECEIPT='artifacts/private/nissan-2024b-submission-refresh-a26fc17a6676/receipt.json'
NISSAN_2024B_SUBMISSIONS_SHA256='bbf9d6f974e4fd91d844da26886f8833b88d4c40b5b44bba6376ed3ef8f7c964'
NISSAN_2024B_RECOVERY_DPD_AUDIT='artifacts/private/nissan-2024b-recovery-dpd-exceptions-71362b31b1c1/audit.json'
NISSAN_2024B_RECOVERY_DPD_RECEIPT='artifacts/private/nissan-2024b-recovery-dpd-exceptions-71362b31b1c1/receipt.json'
NISSAN_2024B_RECOVERY_DPD_SHA256='98e6bb1b95df93c425b1511da7413339f5627b30272c825354620819521a83b3'
NISSAN_2024B_DPD_BOUNDARY_AUDIT='artifacts/private/nissan-2024b-dpd-boundary-audit-762c0a8bcdf2/audit.json'
NISSAN_2024B_DPD_BOUNDARY_RECEIPT='artifacts/private/nissan-2024b-dpd-boundary-audit-762c0a8bcdf2/receipt.json'
NISSAN_2024B_DPD_BOUNDARY_SHA256='d50cad8e52ee8cfe001939ebbea49fd500775311ef8205c4a225325a3a89630a'
MONEY=['originalLoanAmount','reportingPeriodBeginningLoanBalanceAmount',
       'reportingPeriodActualEndBalanceAmount','scheduledPrincipalAmount','scheduledInterestAmount',
       'actualPrincipalCollectedAmount','actualInterestCollectedAmount','recoveredAmount','repossessedProceedsAmount']

def saved_report(root,query):
    if query:raise ValueError('ABS-EE mirror profile has no scope filters')
    source(root)
    path=contained(root,'artifacts/private/absee-profile-63397e5ebbc6/profile.json')
    if sha256(path)!='94e1e9d5742d04e20cd6203da0d11b7dafe7f18ba7ef517de5588d8c68c13ddd':
        raise ValueError('ABS-EE saved profile changed')
    result=read_json(path)
    kpi_path=contained(root,OFFICIAL_KPI)
    kpi_receipt=read_json(contained(root,OFFICIAL_KPI_RECEIPT))
    if (sha256(kpi_path)!=OFFICIAL_KPI_SHA256
            or sha256(kpi_path)!=kpi_receipt.get('kpi_sha256')
            or kpi_receipt.get('status')!='OFFICIAL_ABSEE_MONTHLY_KPI_REPORT_BUILT'
            or kpi_receipt.get('periods')!=20 or kpi_receipt.get('rows')!=880773
            or kpi_receipt.get('balance_checks_passed')!=20
            or kpi_receipt.get('chargeoff_checks_passed')!=20):
        raise ValueError('Official ABS-EE monthly KPI report changed or failed qualification')
    official=read_json(kpi_path)
    if official.get('status')!='OFFICIAL_ABSEE_MONTHLY_KPI_REPORT_BUILT':
        raise ValueError('Official ABS-EE monthly KPI status mismatch')
    result['official_loan_kpis']=official
    feature_path=contained(root,FEATURE_AUDIT)
    feature_receipt=read_json(contained(root,FEATURE_AUDIT_RECEIPT))
    if (sha256(feature_path)!=FEATURE_AUDIT_SHA256
            or sha256(feature_path)!=feature_receipt.get('audit_sha256')
            or feature_receipt.get('status')!='OFFICIAL_ABSEE_FEATURE_ANOMALY_AUDIT_BUILT'
            or feature_receipt.get('periods')!=20 or feature_receipt.get('rows')!=880773):
        raise ValueError('Official ABS-EE feature-anomaly audit changed or failed qualification')
    result['official_feature_anomalies']=read_json(feature_path)
    peer_profiles=[]
    for peer_path_rel,peer_receipt_rel,expected_sha,expected_issuer,expected_rows,expected_fields in PEER_SAMPLES:
        peer_path=contained(root,peer_path_rel)
        peer_receipt=read_json(contained(root,peer_receipt_rel))
        peer=read_json(peer_path)
        if (sha256(peer_path)!=expected_sha
                or sha256(peer_path)!=peer_receipt.get('profile_sha256')
                or peer_receipt.get('status')!='SEC_AUTO_ABS_PEER_XML_PROFILED'
                or peer_receipt.get('rows')!=expected_rows
                or peer_receipt.get('fields')!=expected_fields
                or peer_receipt.get('duplicate_key_rows')!=0 or peer_receipt.get('decimal_parse_errors')!=0
                or peer.get('peer',{}).get('issuer')!=expected_issuer):
            raise ValueError('Official Toyota ABS-EE peer profile changed or failed qualification')
        peer_profiles.append(peer)
    result['official_peer_samples']=peer_profiles
    result['official_peer_sample']=peer_profiles[0]
    history_path=contained(root,TOYOTA_HISTORY_AUDIT)
    history_receipt=read_json(contained(root,TOYOTA_HISTORY_RECEIPT))
    history=read_json(history_path)
    if (sha256(history_path)!=TOYOTA_HISTORY_SHA256
            or sha256(history_path)!=history_receipt.get('audit_sha256')
            or history_receipt.get('status')!='TOYOTA_2022B_LONGITUDINAL_PANEL_AUDITED'
            or history_receipt.get('periods')!=51 or history_receipt.get('rows')!=2508991
            or history_receipt.get('transition_pairs')!=50):
        raise ValueError('Toyota ABS-EE longitudinal panel audit changed or failed qualification')
    target_path=contained(root,TOYOTA_TARGET_AUDIT)
    target_receipt=read_json(contained(root,TOYOTA_TARGET_RECEIPT))
    target=read_json(target_path)
    if (sha256(target_path)!=TOYOTA_TARGET_SHA256
            or sha256(target_path)!=target_receipt.get('audit_sha256')
            or target_receipt.get('status')!='TOYOTA_2022B_SERVICING_TARGET_FEASIBILITY_AUDITED'
            or target_receipt.get('periods')!=51 or target_receipt.get('chargeoff_events')!=1122
            or target_receipt.get('horizons')!=['6','12','24']
            or target_receipt.get('labels_qualified_for_training') is not False):
        raise ValueError('Toyota ABS-EE target-feasibility audit changed or failed qualification')
    ex103_path=contained(root,TOYOTA_EX103_PROFILE)
    ex103_receipt=read_json(contained(root,TOYOTA_EX103_RECEIPT))
    if (sha256(ex103_path)!=TOYOTA_EX103_SHA256
            or sha256(ex103_path)!=ex103_receipt.get('profile_sha256')
            or ex103_receipt.get('status')!='TOYOTA_2022B_EX103_FIELD_NARRATIVES_PROFILED'
            or ex103_receipt.get('periods')!=51 or ex103_receipt.get('fields')!=32
            or ex103_receipt.get('changed_field_definitions')!=0):
        raise ValueError('Toyota EX-103 field narrative profile changed or failed qualification')
    temporal_path=contained(root,TOYOTA_TEMPORAL_AUDIT)
    temporal_receipt=read_json(contained(root,TOYOTA_TEMPORAL_RECEIPT))
    temporal=read_json(temporal_path)
    if (sha256(temporal_path)!=TOYOTA_TEMPORAL_SHA256
            or sha256(temporal_path)!=temporal_receipt.get('audit_sha256')
            or temporal_receipt.get('status')!='TOYOTA_2022B_TEMPORAL_SPLIT_FEASIBILITY_AUDITED'
            or temporal_receipt.get('report_count')!=51
            or temporal_receipt.get('horizons_with_two_way_oot_support')!=2
            or temporal_receipt.get('three_way_split_available') is not False
            or temporal_receipt.get('model_fitted') is not False):
        raise ValueError('Toyota temporal split support audit changed or failed qualification')
    certificate_acquisition=read_json(contained(root,TOYOTA_10D_ACQUISITION))
    certificate_path=contained(root,TOYOTA_CERTIFICATE_AUDIT)
    certificate_receipt=read_json(contained(root,TOYOTA_CERTIFICATE_RECEIPT))
    certificate=read_json(certificate_path)
    if (certificate_acquisition.get('status')!='SEC_OFFICIAL_TOYOTA_2022B_10D_CERTIFICATES_ACQUIRED'
            or certificate_acquisition.get('period_count')!=51
            or sha256(certificate_path)!=TOYOTA_CERTIFICATE_SHA256
            or sha256(certificate_path)!=certificate_receipt.get('audit_sha256')
            or certificate_receipt.get('status')!='TOYOTA_2022B_ABSEE_TO_10D_CERTIFICATE_TIEOUT_AUDITED'
            or certificate_receipt.get('periods')!=51
            or certificate['check_counts'].get('pool_balance_exact')!=51
            or certificate['check_counts'].get('chargeoff_event_count_matches')!=51
            or certificate['check_counts'].get('chargeoff_amount_matches_gross_liquidations')!=51
            or certificate['check_counts'].get('recovered_amount_matches_aggregate_net_liquidation_proceeds')!=2):
        raise ValueError('Toyota 10-D certificate acquisition/tie-out changed or failed qualification')
    feature_path=contained(root,TOYOTA_FEATURE_AUDIT)
    feature_receipt=read_json(contained(root,TOYOTA_FEATURE_RECEIPT))
    feature=read_json(feature_path)
    if (sha256(feature_path)!=TOYOTA_FEATURE_SHA256
            or sha256(feature_path)!=feature_receipt.get('audit_sha256')
            or feature_receipt.get('status')!='TOYOTA_2022B_FEATURE_AVAILABILITY_AUDITED'
            or feature_receipt.get('periods')!=51 or feature_receipt.get('horizon_months')!=12
            or feature_receipt.get('train_rows')!=999342 or feature_receipt.get('test_rows')!=486182
            or feature['information_timing']['filing_lag_days'].get('median')!=27
            or feature['candidate_static_field_stability'].get('obligorGeographicLocation',{}).get('assets_with_value_changes_after_first_observation')!=2870):
        raise ValueError('Toyota feature availability/timing audit changed or failed qualification')
    result['official_toyota_2022b_history']={
        'audit':history,'target_feasibility':target,'ex103_field_narratives':read_json(ex103_path),
        'temporal_split_feasibility':temporal,'certificate_tieout':certificate,
        'feature_availability':feature}
    validation_path=contained(root,TOYOTA_2024B_HISTORY_AUDIT)
    validation_receipt=read_json(contained(root,TOYOTA_2024B_HISTORY_RECEIPT))
    validation=read_json(validation_path)
    if (sha256(validation_path)!=TOYOTA_2024B_HISTORY_SHA256
            or sha256(validation_path)!=validation_receipt.get('audit_sha256')
            or validation_receipt.get('status')!='TOYOTA_2024B_LONGITUDINAL_PANEL_AUDITED'
            or validation_receipt.get('periods')!=29 or validation_receipt.get('rows')!=1518106
            or validation_receipt.get('unique_assets')!=70254
            or validation_receipt.get('default_or_exit_labels_qualified') is not False):
        raise ValueError('Toyota 2024-B longitudinal audit changed or failed qualification')
    validation_tieout_path=contained(root,TOYOTA_2024B_CERTIFICATE_AUDIT)
    validation_tieout_receipt=read_json(contained(root,TOYOTA_2024B_CERTIFICATE_RECEIPT))
    validation_tieout=read_json(validation_tieout_path)
    if (sha256(validation_tieout_path)!=TOYOTA_2024B_CERTIFICATE_SHA256
            or sha256(validation_tieout_path)!=validation_tieout_receipt.get('audit_sha256')
            or validation_tieout_receipt.get('status')!='TOYOTA_2024B_ABSEE_TO_10D_CERTIFICATE_TIEOUT_AUDITED'
            or validation_tieout_receipt.get('periods')!=29
            or validation_tieout['check_counts'].get('pool_balance_exact')!=29
            or validation_tieout['check_counts'].get('chargeoff_event_count_matches')!=29
            or validation_tieout['check_counts'].get('chargeoff_amount_matches_gross_liquidations')!=29
            or validation_tieout['check_counts'].get('recovered_amount_matches_aggregate_net_liquidation_proceeds')!=1):
        raise ValueError('Toyota 2024-B certificate tie-out changed or failed qualification')
    result['official_toyota_2024b_validation']={
        'audit':validation,'certificate_tieout':validation_tieout,
        'same_issuer_family_as_2022b':True,'issuer_independent_validation':False}
    nissan_acquisition=read_json(contained(root,NISSAN_2024B_ACQUISITION))
    nissan_panel=read_json(contained(root,NISSAN_2024B_PANEL))
    nissan_history_path=contained(root,NISSAN_2024B_PANEL_AUDIT)
    nissan_history_receipt=read_json(contained(root,NISSAN_2024B_PANEL_AUDIT_RECEIPT))
    nissan_history=read_json(nissan_history_path)
    if (nissan_acquisition.get('status')!='SEC_OFFICIAL_NISSAN_2024B_PAIRED_HISTORY_ACQUIRED'
            or nissan_acquisition.get('issuer')!='Nissan Auto Receivables 2024-B Owner Trust'
            or nissan_acquisition.get('period_count')!=23
            or nissan_panel.get('status')!='OFFICIAL_NISSAN_2024B_VALIDATION_PANEL_PARQUET_BUILT'
            or nissan_panel.get('report_count')!=23 or nissan_panel.get('row_count')!=1154259
            or sha256(nissan_history_path)!=NISSAN_2024B_PANEL_AUDIT_SHA256
            or sha256(nissan_history_path)!=nissan_history_receipt.get('audit_sha256')
            or nissan_history_receipt.get('status')!='NISSAN_2024B_LONGITUDINAL_PANEL_AUDITED'
            or nissan_history_receipt.get('periods')!=23 or nissan_history_receipt.get('rows')!=1154259
            or nissan_history_receipt.get('unique_assets')!=63688):
        raise ValueError('Nissan 2024-B source/panel audit changed or failed qualification')
    nissan_certificate_path=contained(root,NISSAN_2024B_CERTIFICATE_AUDIT)
    nissan_certificate_receipt=read_json(contained(root,NISSAN_2024B_CERTIFICATE_RECEIPT))
    nissan_certificate=read_json(nissan_certificate_path)
    if (sha256(nissan_certificate_path)!=NISSAN_2024B_CERTIFICATE_SHA256
            or sha256(nissan_certificate_path)!=nissan_certificate_receipt.get('audit_sha256')
            or nissan_certificate_receipt.get('status')!='NISSAN_2024B_ABSEE_TO_10D_CERTIFICATE_TIEOUT_AUDITED'
            or nissan_certificate_receipt.get('periods')!=23
            or nissan_certificate['check_counts'].get('pool_balance_exact')!=23
            or nissan_certificate['check_counts'].get('positive_balance_count_matches')!=23
            or nissan_certificate['check_counts'].get('chargeoff_event_count_matches')!=20
            or nissan_certificate['check_counts'].get('chargeoff_amount_matches_gross_defaulted_principal')!=21
            or nissan_certificate['check_counts'].get('first_code4_event_count_matches_certificate')!=21
            or nissan_certificate['check_counts'].get('first_code4_chargeoff_amount_matches_certificate')!=20
            or nissan_certificate['check_counts'].get('monthly_net_loss_equals_defaulted_principal_less_recoveries')!=23
            or nissan_certificate['check_counts'].get('cumulative_net_loss_equals_sum_of_monthly_net_loss')!=23):
        raise ValueError('Nissan 2024-B certificate tie-out changed or failed qualification')
    submissions_path=contained(root,NISSAN_2024B_SUBMISSIONS_AUDIT)
    submissions_receipt=read_json(contained(root,NISSAN_2024B_SUBMISSIONS_RECEIPT))
    submissions=read_json(submissions_path)
    if (sha256(submissions_path)!=NISSAN_2024B_SUBMISSIONS_SHA256
            or sha256(submissions_path)!=submissions_receipt.get('audit_sha256')
            or submissions.get('status')!='NISSAN_2024B_SEC_SUBMISSIONS_REFRESH_VERIFIED'
            or submissions.get('snapshot_latest_filing_date')!='2026-09-25'
            or submissions.get('submission_row_count')!=57
            or submissions.get('live_matches_acquisition_snapshot') is not True
            or submissions.get('july_report_date_amendments')!=[]
            or submissions_receipt.get('amendments_for_2025_07_31')!=0):
        raise ValueError('Nissan live SEC submission census changed or shows amendment')
    recovery_path=contained(root,NISSAN_2024B_RECOVERY_DPD_AUDIT)
    recovery_receipt=read_json(contained(root,NISSAN_2024B_RECOVERY_DPD_RECEIPT))
    recovery_dpd=read_json(recovery_path)
    if (sha256(recovery_path)!=NISSAN_2024B_RECOVERY_DPD_SHA256
            or sha256(recovery_path)!=recovery_receipt.get('audit_sha256')
            or recovery_dpd.get('status')!='NISSAN_2024B_RECOVERY_AND_DPD_EXCEPTIONS_ANALYZED'
            or len(recovery_dpd.get('recovery_periods',[]))!=6
            or any(set(p.get('positive_recovery_row_months',{}))!={'code4_previously_observed'} for p in recovery_dpd['recovery_periods'])
            or recovery_dpd['june_2025_delinquency']['exact_day_60_count_and_balance']!={'count':2,'balance':'50837.98000000'}
            or recovery_dpd['june_2025_delinquency']['exact_day_90_count_and_balance']!={'count':1,'balance':'22729.88000000'}):
        raise ValueError('Nissan recovery/DPD exception audit changed or failed qualification')
    boundary_path=contained(root,NISSAN_2024B_DPD_BOUNDARY_AUDIT)
    boundary_receipt=read_json(contained(root,NISSAN_2024B_DPD_BOUNDARY_RECEIPT))
    boundary=read_json(boundary_path)
    if (sha256(boundary_path)!=NISSAN_2024B_DPD_BOUNDARY_SHA256
            or sha256(boundary_path)!=boundary_receipt.get('audit_sha256')
            or boundary.get('status')!='NISSAN_2024B_DPD_BOUNDARY_RULES_COMPARED'
            or boundary['aggregate_exact_checks'].get('literal')!=178
            or boundary['aggregate_exact_checks'].get('shifted')!=86
            or boundary_receipt.get('aggregate_exact_checks')!=boundary['aggregate_exact_checks']):
        raise ValueError('Nissan DPD boundary diagnostic changed')
    result['official_nissan_2024b_external_validation']={
        'acquisition':nissan_acquisition,'panel':nissan_panel,'audit':nissan_history,
        'certificate_tieout':nissan_certificate,'submission_history':submissions,
        'recovery_dpd_exception_audit':recovery_dpd,'dpd_boundary_diagnostic':boundary,
        'different_issuer_servicer_family_from_toyota':True,
        'model_external_validation_completed':False}
    return result

def source(root):
    folder=contained(root,'data/private/structured/'+SOURCE)
    if sha256(folder/'acquisition-complete.json')!=RECEIPT:raise ValueError('ABS-EE mirror receipt changed')
    receipt=read_json(folder/'acquisition-complete.json')
    for item in receipt['sources']:
        p=folder/item['file']
        if p.parent!=folder or p.stat().st_size!=item['bytes'] or sha256(p)!=item['sha256']:
            raise ValueError('ABS-EE mirror source changed')
    return folder,receipt

def profile_file(path,report_date):
    parquet=pq.ParquetFile(path)
    if parquet.metadata.num_rows>200000:raise ValueError('Mirror row bound exceeded')
    names=parquet.schema_arrow.names
    required=set(MONEY+['assetNumber','assetTypeNumber','reportingPeriodBeginningDate','reportingPeriodEndingDate','currentDelinquencyStatus'])
    if not required<=set(names) or len(names)!=len(set(names)):raise ValueError('Missing/duplicate mirror columns')
    missing=Counter();invalid=Counter();negative=Counter();totals={k:Decimal(0) for k in MONEY}
    status=Counter();types=Counter();dates=Counter();keys=set();duplicates=0;count=0
    for batch in parquet.iter_batches(batch_size=4096):
        for row in batch.to_pylist():
            count+=1
            for key,value in row.items():
                if value is None or str(value).strip()=='':missing[key]+=1
            asset=row['assetNumber'];kind=row['assetTypeNumber']
            if asset is None or not str(asset).strip():invalid['asset_key']+=1
            else:
                identity=(kind,asset)
                if identity in keys:duplicates+=1
                keys.add(identity)
            types[str(kind)]+=1;status[str(row['currentDelinquencyStatus'])]+=1
            begin,end=row['reportingPeriodBeginningDate'],row['reportingPeriodEndingDate']
            dates[str(begin)+' / '+str(end)]+=1
            try:
                b=datetime.strptime(begin,'%m-%d-%Y').date();e=datetime.strptime(end,'%m-%d-%Y').date()
                if b>e or e.isoformat()!=report_date:invalid['reporting_dates']+=1
            except (TypeError,ValueError):invalid['reporting_dates']+=1
            for key in MONEY:
                value=row[key]
                if value is None or str(value).strip()=='':continue
                try:
                    number=Decimal(str(value))
                    if not number.is_finite():raise ValueError('Non-finite')
                    totals[key]+=number
                    if number<0:negative[key]+=1
                except Exception:invalid[key]+=1
    return {'rows':count,'parquet_declared_rows':parquet.metadata.num_rows,'columns':names,
        'missing_by_field':{k:missing[k] for k in names},'invalid_by_field':dict(invalid),
        'negative_money_counts':dict(negative),'money_sums_exact':{k:str(v) for k,v in totals.items()},
        'money_sums_units':'unqualified source units; not silently assigned USD',
        'raw_status_counts':dict(status),'asset_type_counts':dict(types),'reporting_dates':dict(dates),
        'unique_keys':len(keys),'duplicate_key_rows':duplicates},keys

def report(root):
    folder,receipt=source(root);periods=[];links=[];previous=None;seen=set()
    for item in sorted(receipt['selected_filings'],key=lambda x:x['reportDate']):
        date=item['reportDate']
        if date in seen:raise ValueError('Duplicate selected reporting period')
        seen.add(date)
        data,keys=profile_file(folder/item['file'],date)
        periods.append({'report_date':date,'filing_date':item['filingDate'],'accession':item['accessionNumber'],
            'file':item['file'],**data})
        if previous:
            old_date,old_keys=previous
            a=datetime.fromisoformat(old_date);b=datetime.fromisoformat(date)
            distance=(b.year-a.year)*12+b.month-a.month
            links.append({'from':old_date,'to':date,'month_distance':distance,'adjacent_month':distance==1,
                'matched_keys':len(keys & old_keys),'previous_only_keys':len(old_keys-keys),'current_only_keys':len(keys-old_keys),
                'causal_exit_reason_qualified':False,'transition_labels_qualified':False})
        previous=date,keys
    recent=read_json(folder/'sec-submissions.json')['filings']['recent']
    official_dates=sorted({recent['reportDate'][i] for i,f in enumerate(recent['form']) if f=='ABS-EE' and recent['reportDate'][i]})
    return {'source_id':SOURCE,'source_receipt_sha256':RECEIPT,'mirror_commit':receipt['mirror_commit'],
        'selected_periods':len(periods),'periods':periods,'linkage':links,
        'official_report_dates_without_selected_mirror':sorted(set(official_dates)-seen),
        'total_rows':sum(p['rows'] for p in periods),'raw_xml_acquired':False,'source_value_fidelity_verified':False,
        'model_ready':False,'visibility':'private','public_release_approved':False,
        'limitations':['Metadata accession match does not verify mirror extraction/value fidelity.',
            'Raw assetTypeNumber/status strings are inventoried, not converted into default/PD/LGD labels.',
            'Duplicate/missing/nonnumeric counts and totals are structural diagnostics; monetary units/signs/semantics require official schema/exhibit review.',
            'Month gaps are retained. Matched IDs alone do not prove persistent identity; exits are not automatically defaults/prepayments.',
            'No borrower IDs exported by this profile. Raw third-party files remain private; mirror README claims GPL without a fully reviewed redistribution grant.']}
