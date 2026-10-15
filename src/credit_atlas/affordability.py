"""Explicit income/expense/debt intake and exact declared-policy assessment."""
import re
from datetime import date
from decimal import Decimal,localcontext
from fractions import Fraction

GROUPS=['gross_income','net_income','recurring_expenses','debt_payments','proposed_payments']
FACTORS={'monthly':Fraction(1),'annual':Fraction(1,12),'quarterly':Fraction(1,3),
         'weekly':Fraction(52,12),'biweekly':Fraction(26,12),'semimonthly':Fraction(2)}
ID=re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}\Z')

def number(value,signed=False):
    pattern=r'-?\d{1,18}(?:\.\d{1,6})?' if signed else r'\d{1,18}(?:\.\d{1,6})?'
    if not isinstance(value,str) or not re.fullmatch(pattern,value):raise ValueError('Amounts must be finite decimal strings with explicit sign convention')
    return Fraction(Decimal(value))

def exact(value):
    if value is None:return None
    with localcontext() as ctx:
        ctx.prec=50
        return {'numerator':str(value.numerator),'denominator':str(value.denominator),'decimal50':str(Decimal(value.numerator)/Decimal(value.denominator))}

def assess(payload):
    keys={'case_ref','as_of','currency','scope','scope_ref','members','coverage','gross_income','net_income','recurring_expenses','debt_payments','proposed_payments','policy','stress'}
    if not isinstance(payload,dict) or set(payload)-keys:raise ValueError('Unknown affordability input field')
    if any(not isinstance(payload.get(k),str) or not ID.fullmatch(payload[k]) for k in ['case_ref','scope_ref']):raise ValueError('Pseudonymous case/scope references required')
    try:as_of=date.fromisoformat(payload['as_of'])
    except (KeyError,ValueError,TypeError):raise ValueError('Valid assessment date required')
    if not isinstance(payload.get('currency'),str) or not re.fullmatch('[A-Z]{3}',payload['currency']):raise ValueError('Explicit single currency required')
    if not isinstance(payload.get('scope'),str) or payload['scope'] not in {'individual','household'} or type(payload.get('members')) is not int or not 1<=payload['members']<=100:raise ValueError('Explicit household/individual scope and member count required')
    if payload['scope']=='individual' and payload['members']!=1:raise ValueError('Individual scope must have one member')
    coverage=payload.get('coverage')
    if not isinstance(coverage,dict) or set(coverage)!=set(GROUPS) or any(type(v) is not bool for v in coverage.values()):raise ValueError('Coverage attestation required for every input group')
    totals={};groups={};cost_refs=set();evidence_gaps=[]
    for group in GROUPS:
        items=payload.get(group)
        if not isinstance(items,list) or len(items)>500:raise ValueError('Bounded item list required for '+group)
        refs=set();known=Fraction(0);missing=[];rows=[]
        for item in items:
            if not isinstance(item,dict) or set(item)!={'ref','amount','period','evidence_ref','valid_through'}:raise ValueError('Invalid affordability item schema')
            ref=item['ref']
            if not isinstance(ref,str) or not ID.fullmatch(ref) or ref in refs:raise ValueError('Unique item reference required')
            refs.add(ref)
            if group in {'recurring_expenses','debt_payments','proposed_payments'}:
                if ref in cost_refs:raise ValueError('Duplicate obligation across expense/debt/proposed groups')
                cost_refs.add(ref)
            if not isinstance(item['period'],str) or item['period'] not in FACTORS:raise ValueError('Unsupported cash-flow period')
            evidence=item['evidence_ref']
            if evidence is not None and (not isinstance(evidence,str) or not ID.fullmatch(evidence)):raise ValueError('Invalid evidence reference')
            if evidence is None:evidence_gaps.append({'group':group,'ref':ref})
            expired=False
            if item['valid_through'] is not None:
                try:expired=date.fromisoformat(item['valid_through'])<as_of
                except (TypeError,ValueError):raise ValueError('Invalid source validity date')
            amount=number(item['amount']) if item['amount'] is not None else None
            monthly=amount*FACTORS[item['period']] if amount is not None else None
            if monthly is None or expired:missing.append({'ref':ref,'reason':'expired_validity' if expired else 'missing_amount'})
            else:known+=monthly
            rows.append({'ref':ref,'source_amount':item['amount'],'source_period':item['period'],'monthly_factor':exact(FACTORS[item['period']]),
                         'monthly_amount':exact(monthly),'evidence_ref':evidence,'source_valid_through':item['valid_through'],'evidence_reference_verified':False,'expired':expired})
        usable=coverage[group] and not missing
        totals[group]=known if usable else None
        groups[group]={'coverage_attested':coverage[group],'items':rows,'known_monthly_sum':exact(known),
                       'usable_monthly_total':exact(totals[group]),'issues':missing,'coverage_verified':False}
    policy=payload.get('policy')
    if not isinstance(policy,dict) or set(policy)!={'policy_ref','max_total_dti_fraction','min_monthly_residual'}:raise ValueError('Explicit policy object required')
    maximum=number(policy['max_total_dti_fraction']) if policy['max_total_dti_fraction'] is not None else None
    minimum=number(policy['min_monthly_residual'],signed=True) if policy['min_monthly_residual'] is not None else None
    if any(x is not None for x in [maximum,minimum]) and (not isinstance(policy['policy_ref'],str) or not ID.fullmatch(policy['policy_ref'])):raise ValueError('Policy reference required with thresholds')
    if policy['policy_ref'] is not None and (not isinstance(policy['policy_ref'],str) or not ID.fullmatch(policy['policy_ref'])):raise ValueError('Invalid policy reference')
    def compute(values):
        debt=values['debt_payments'];proposed=values['proposed_payments'];gross=values['gross_income'];net=values['net_income'];expenses=values['recurring_expenses']
        total_debt=debt+proposed if debt is not None and proposed is not None else None
        dti=total_debt/gross if total_debt is not None and gross is not None and gross>0 else None
        residual=net-expenses-total_debt if all(x is not None for x in [net,expenses,total_debt]) else None
        return {'gross_monthly_income':exact(gross),'net_monthly_income':exact(net),'monthly_existing_debt':exact(debt),
            'monthly_proposed_payment':exact(proposed),'monthly_total_debt':exact(total_debt),'monthly_recurring_expenses':exact(expenses),
            'total_dti_fraction':exact(dti),'monthly_residual_after_expenses_and_debt':exact(residual),
            'dti_unavailable_reason':None if dti is not None else 'missing_or_incomplete_debt_or_gross_income' if gross!=0 else 'zero_gross_income',
            'dti_policy_comparison':'UNAVAILABLE' if dti is None or maximum is None else 'WITHIN_DECLARED_LIMIT' if dti<=maximum else 'EXCEEDS_DECLARED_LIMIT',
            'residual_policy_comparison':'UNAVAILABLE' if residual is None or minimum is None else 'MEETS_DECLARED_FLOOR' if residual>=minimum else 'BELOW_DECLARED_FLOOR'}
    baseline=compute(totals);stress=payload.get('stress');stressed=None
    if stress is not None:
        if not isinstance(stress,dict) or set(stress)!={'gross_income_reduction_fraction','net_income_reduction_fraction','extra_monthly_expense'}:raise ValueError('Invalid stress assumptions')
        gs=number(stress['gross_income_reduction_fraction']);ns=number(stress['net_income_reduction_fraction']);extra=number(stress['extra_monthly_expense'])
        if gs>1 or ns>1:raise ValueError('Income reductions must be fractions between zero and one')
        adjusted=dict(totals)
        for group,reduction in [('gross_income',gs),('net_income',ns)]:adjusted[group]=totals[group]*(1-reduction) if totals[group] is not None else None
        adjusted['recurring_expenses']=totals['recurring_expenses']+extra if totals['recurring_expenses'] is not None else None
        stressed={'assumptions':stress,'results':compute(adjusted),'kind':'declared_sensitivity_not_observed_actuals'}
    return {'schema_version':1,'case_ref':payload['case_ref'],'as_of':as_of.isoformat(),'currency':payload['currency'],
        'scope':payload['scope'],'scope_ref':payload['scope_ref'],'members':payload['members'],'groups':groups,'baseline':baseline,'stress':stressed,
        'policy':policy,'policy_confirmed':False,'missing_evidence_references':evidence_gaps,'income_verification_qualified':False,
        'assessment_kind':'DECLARED_INPUT_ARITHMETIC_ASSESSMENT','credit_decision':None,'legal_compliance_qualified':False,
        'source_coverage_verified':False,'public_release_approved':False,'visibility':'private',
        'definitions':{'dti':'Monthly existing debt plus proposed payments divided by monthly gross income.',
            'residual':'Monthly net income minus recurring non-debt expenses minus existing and proposed debt payments.',
            'frequency':'Average-month convention:weekly52/year,biweekly26/year,semimonthly24/year;not a calendar cash-flow forecast.',
            'evidence':'References/coverage are user declarations;this calculation has not verified documents or financial completeness.'},
        'limitations':['No income inferred from credit limits or lender-assigned risk scores.',
            'Missing/expired inputs or incomplete declared coverage keep dependent results unavailable;known partial sums remain separate.',
            'DTI thresholds and residual floors are declared policy inputs,not universal or legal approval limits.',
            'Obligation reference uniqueness prevents exact duplicate references;semantic expense/debt overlap still needs review.',
            'No credit approval,rejection,verified-income or legal compliance conclusion is produced.']}
