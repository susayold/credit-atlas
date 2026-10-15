"""Private, maturity-aware descriptive competing-event curves; not model training."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import random
import uuid

import duckdb

from .cli import code_fingerprint
from .labels import create_labels
from .source import sha256, utc_now, write_json_new

CAUSES = ('d3', 'prepayment', 'other_exit')


def curve(counts, max_age):
    """Discrete Aalen-Johansen: tied events occur before end-month censoring."""
    if type(max_age) is not int or not 1 <= max_age <= 60:
        raise ValueError('Invalid observation horizon')
    for (age, cause), count in counts.items():
        if (type(age) is not int or not 0 <= age <= max_age or
                cause not in (*CAUSES, 'censored') or (age == 0 and cause != 'censored') or
                type(count) is not int or count < 0):
            raise ValueError('Invalid first-event ledger counts')
    population = sum(counts.values())
    risk = population - counts.get((0, 'censored'), 0)
    survival = 1.0
    incidence = dict.fromkeys(CAUSES, 0.0)
    result = []
    for age in range(1, max_age + 1):
        events = {cause: counts.get((age, cause), 0) for cause in CAUSES}
        censor = counts.get((age, 'censored'), 0)
        if sum(events.values()) + censor > risk:
            raise ValueError('Risk set does not reconcile')
        supported = population > 0 and (risk > 0 or survival <= 1e-14)
        if risk:
            for cause in CAUSES:
                incidence[cause] += survival * events[cause] / risk
            survival *= 1 - sum(events.values()) / risk
        result.append(dict(observation_age=age, at_risk=risk, censored=censor,
            **{f'new_{cause}': events[cause] for cause in CAUSES},
            **{f'cif_{cause}': incidence[cause] if supported else None for cause in CAUSES},
            event_free_probability=survival if supported else None,
            supported=supported))
        risk -= sum(events.values()) + censor
    if risk != 0:
        raise ValueError('Follow-up ledger extends beyond requested horizon')
    return result


def _quantile(values, fraction):
    values = sorted(values)
    index = (len(values) - 1) * fraction
    low = math.floor(index)
    high = math.ceil(index)
    return values[low] + (values[high] - values[low]) * (index - low)


def bootstrap_intervals(counts, max_age, horizons, *, resamples=500, seed=17):
    """IID loan bootstrap, grouped by identical follow-up outcome; no row resampling."""
    if type(resamples) is not int or not 100 <= resamples <= 10000:
        raise ValueError('Use 100..10000 bootstrap replicates')
    if type(seed) is not int or seed < 0:
        raise ValueError('Invalid bootstrap seed')
    curve(counts, max_age)  # validate before random sampling
    if any(type(h) is not int or not 1 <= h <= max_age for h in horizons):
        raise ValueError('Invalid bootstrap horizons')
    n = sum(counts.values())
    keys = sorted(counts)
    rng = random.Random(seed)
    draws = defaultdict(list)
    if n:
        for _ in range(resamples):
            sampled = Counter(rng.choices(keys, weights=[counts[k] for k in keys], k=n))
            estimate = curve(sampled, max_age)
            for h in horizons:
                value = estimate[h - 1]['cif_d3']
                if value is not None:
                    draws[h].append(value)
    intervals = {}
    for h in horizons:
        d3 = sum(v for (age, cause), v in counts.items() if cause == 'd3' and age <= h)
        enough = len(draws[h]) >= math.ceil(resamples * .95)
        # A nonparametric bootstrap cannot learn an unseen rare event.
        status = ('boundary_event_support' if d3 in (0, n) else
                  'available' if enough else 'insufficient_defined_draws')
        intervals[h] = dict(ci_method='iid_loan_percentile_bootstrap', ci_level=.95,
            ci_lower=_quantile(draws[h], .025) if status == 'available' else None,
            ci_upper=_quantile(draws[h], .975) if status == 'available' else None,
            ci_status=status, defined_draws=len(draws[h]), resamples=resamples, seed=seed)
    return intervals


def create_ledger(db, sql_dir, cohort_config, max_age=24):
    create_labels(db, sql_dir, {**cohort_config, 'horizon_months': max_age})
    db.execute('CREATE TEMP TABLE vintage_ledger AS ' +
               (sql_dir/'marts/vintage.sql').read_text().format(max_age=max_age))
    expected = db.execute("SELECT COUNT(*) FROM labels WHERE eligibility_reason='eligible'").fetchone()[0]
    actual = db.execute('SELECT COUNT(*),COUNT(DISTINCT loan_id) FROM vintage_ledger').fetchone()
    if actual != (expected, expected):
        raise ValueError('Vintage ledger cardinality mismatch')
    mismatch = db.execute('''SELECT COUNT(*) FROM vintage_ledger v JOIN labels l USING(loan_id)
       WHERE (v.endpoint='d3') IS DISTINCT FROM (l.outcome='d3_event')
          OR (v.endpoint='prepayment') IS DISTINCT FROM (l.outcome='prepayment')
          OR (v.endpoint='other_exit') IS DISTINCT FROM (l.outcome='other_exit')''').fetchone()[0]
    if mismatch:
        raise ValueError('First-event ledger disagrees with horizon labels')
    db.execute('''CREATE TEMP TABLE vintage_stock AS
      SELECT o.origination_year, date_diff('month',o.landmark,p.period)::INTEGER AS observation_age,
       COUNT(*) AS reported_loans,
       COUNT(*) FILTER (WHERE p.terminal_type IS NULL) AS active_loans,
       COUNT(*) FILTER (WHERE p.terminal_type IS NULL AND p.delinquency_state<>'UNKNOWN') AS usable_active_loans,
       COUNT(*) FILTER (WHERE p.terminal_type IS NULL AND p.delinquency_state='UNKNOWN') AS unknown_active_loans,
       COUNT(*) FILTER (WHERE p.terminal_type IS NULL AND p.delinquency_state='D3PLUS') AS d3_active_loans,
       d3_active_loans / NULLIF(usable_active_loans,0)::DOUBLE AS d3_stock_share
      FROM fact_loan_month p JOIN observation o USING(loan_id)
      WHERE date_diff('month',o.landmark,p.period) BETWEEN 0 AND ?
      GROUP BY ALL ORDER BY 1,2''', [max_age])


def summarize(db, max_age, horizons, resamples, seed):
    result = {'curves': [], 'horizons': [], 'cohorts': []}
    for year, in db.execute('SELECT DISTINCT origination_year FROM observation ORDER BY 1').fetchall():
        for segment, predicate in [('all', 'TRUE'), ('relief', 'is_relief_refinance IS TRUE'),
                                   ('non_relief', 'is_relief_refinance IS FALSE'),
                                   ('unknown_relief', 'is_relief_refinance IS NULL')]:
            total = db.execute(f'SELECT COUNT(*) FROM observation WHERE origination_year=? AND {predicate}', [year]).fetchone()[0]
            if not total:
                continue
            rows = db.execute(f'''SELECT stop_age,endpoint,COUNT(*) FROM vintage_ledger
                WHERE origination_year=? AND {predicate} GROUP BY ALL''', [year]).fetchall()
            counts = {(age, cause): n for age, cause, n in rows}
            n = sum(counts.values())
            cohort = dict(origination_year=year, segment=segment, source_loans=total,
                          eligible_loans=n, excluded_loans=total-n, excluded_share=(total-n)/total)
            result['cohorts'].append(cohort)
            estimates = curve(counts, max_age)
            intervals = bootstrap_intervals(counts, max_age, horizons, resamples=resamples, seed=seed)
            for item in estimates:
                h = item['observation_age']
                mature = db.execute(f'''SELECT COUNT(*) FROM vintage_ledger
                    WHERE origination_year=? AND {predicate} AND calendar_age>=?''', [year, h]).fetchone()[0]
                item.update(cohort, calendar_mature_loans=mature,
                            maturity_complete=n > 0 and mature == n)
                for cause in CAUSES:
                    item[f'observed_{cause}_count'] = sum(v for (age, c), v in counts.items() if c == cause and age <= h)
                item['unknown_before_horizon'] = sum(v for (age, c), v in counts.items() if c == 'censored' and age < h)
                item['unknown_share'] = item['unknown_before_horizon']/n if n else None
                item['observed_d3_lower_bound'] = item['observed_d3_count']/n if n else None
                item['sparse_d3'] = item['observed_d3_count'] < 10
                if not item['maturity_complete']:
                    for cause in CAUSES:
                        item[f'cif_{cause}'] = None
                    item['event_free_probability'] = None
                result['curves'].append(item)
                if h in horizons:
                    summary = {**item, **intervals[h]}
                    if not item['maturity_complete'] or not item['supported']:
                        summary.update(ci_lower=None, ci_upper=None, ci_status='immature_or_unsupported')
                    result['horizons'].append(summary)
    return result


def run(root, canonical_run, *, max_age=24, resamples=500, seed=17):
    if max_age != 24:
        raise ValueError('The development vintage protocol fixes 6/12/24-month comparisons')
    source_path = canonical_run/'run-complete.json'
    source = json.loads(source_path.read_text())
    if source.get('status') != 'CANONICAL_COMPLETE':
        raise ValueError('Completed canonical input required')
    inputs = {name: canonical_run/(name+'.parquet') for name in ('dim_loan','fact_loan_month')}
    for name, path in inputs.items():
        if sha256(path) != source['outputs_sha256'][path.name]:
            raise ValueError('Canonical input changed')
    cohort = json.loads((root/'configs/cohort.json').read_text())
    target = root/'artifacts/private'/('vintage-'+uuid.uuid4().hex[:12])
    target.mkdir(parents=True, exist_ok=False)
    manifest = dict(started_at=utc_now(), canonical_run=canonical_run.name,
        canonical_manifest_sha256=sha256(source_path), inputs_sha256=source['outputs_sha256'],
        cohort_config=cohort, horizons=[6,12,24], max_age=max_age, resamples=resamples, seed=seed,
        code_sha256=code_fingerprint(root), visibility='private', research_ready=False,
        public_release_approved=False, evidence_class='retrospective_observed_sample',
        estimator='discrete_Aalen_Johansen_three_competing_causes')
    write_json_new(target/'run-start.json', manifest)
    try:
        with duckdb.connect() as db:
            db.execute("SET memory_limit='1GB'")
            for name, path in inputs.items():
                db.read_parquet(str(path)).create_view(name)
            create_ledger(db, root/'sql', cohort, max_age)
            summary = summarize(db, max_age, [6,12,24], resamples, seed)
            for table in ('vintage_ledger', 'vintage_stock'):
                db.table(table).write_parquet(str(target/(table+'.parquet')), compression='zstd')
        write_json_new(target/'summary.json', summary)
        manifest.update(completed_at=utc_now(), status='VINTAGE_DEVELOPMENT_COMPLETE',
            outputs_sha256={p.name: sha256(p) for p in target.iterdir() if p.suffix == '.parquet' or p.name == 'summary.json'})
        write_json_new(target/'run-complete.json', manifest)
        return target
    except Exception as error:
        write_json_new(target/'run-failed.json', dict(failed_at=utc_now(), exception_type=type(error).__name__))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--canonical-run', required=True, type=Path)
    parser.add_argument('--resamples', default=500, type=int)
    args = parser.parse_args()
    print(run(Path(__file__).resolve().parents[2], args.canonical_run.resolve(), resamples=args.resamples))
