"""Versioned private findings resolved against the verified immutable case."""
import re


def report(service,query):
    if set(query)-{'run','id','revision'} or not {'run','id'}<=set(query):
        raise ValueError('Finding report requires run,id and optional revision')
    identifier=query['id']
    if not isinstance(identifier,str) or not re.fullmatch(r'[0-9a-f]{32}',identifier):
        raise ValueError('Invalid finding identifier')
    run=query['run'];case=service.case(run)
    history=service.reviews.history(run,identifier)
    revision=query.get('revision')
    if revision is not None and (not isinstance(revision,str) or not re.fullmatch(r'[1-9][0-9]{0,8}',revision)):
        raise ValueError('Finding revision must be a positive integer')
    selected=next((r for r in history if r['revision']==int(revision)),None) if revision is not None else history[-1]
    if selected is None:raise KeyError('Finding revision not found')
    finding=selected['record']
    if finding['case_id']!=run or finding['id']!=identifier or finding['revision']!=selected['revision']:
        raise ValueError('Finding history scope mismatch')
    aggregates=service.report(run,finding['filters'])
    if aggregates['case_id']!=run:raise ValueError('Finding evidence scope mismatch')
    evidence=service.evidence(run)
    view_evidence={}
    if finding['view']=='loss':
        from .observed_loss_details import report as loss_report
        view_evidence['observed_loss_details']=loss_report(service,{'run':run})
    if finding['view']=='sources':
        from .mortgage_provenance import report as provenance_report
        view_evidence['source_provenance']=provenance_report(service,{'run':run})
    if finding['filters'].get('loan_key'):
        view_evidence['loan_timeline']=service.timeline(run,finding['filters']['loan_key'])
    service.case(run)
    return {'schema_version':'private-finding-report-v1','case_id':run,'finding':finding,
            'history':[h for h in history if h['revision']<=finding['revision']],
            'evidence_refs':finding['evidence_refs'],'aggregate_evidence':aggregates,
            'case_evidence':evidence,'view_evidence':view_evidence,'visibility':'private','public_release_approved':False,
            'review_kind':'local_research_review_not_credit_approval',
            'authenticated_reviewer_identity':False,'bank_credit_approval':False,
            'evidence_resolution':'Current verified immutable case and selected finding revision filters;not a saved numerical snapshot from finding creation time',
            'limitations':['Reviewed is a local research status;no authenticated identity,role or bank approval is asserted.',
                           'Reviewer text cannot edit raw/canonical sources or frozen model gates.',
                           'Each aggregate table retains its own filter applicability;whole-source loss/quality remain whole-source.',
                           'Evidence references are reviewer-selected contract labels,not automatic verification of the conclusion.']}
