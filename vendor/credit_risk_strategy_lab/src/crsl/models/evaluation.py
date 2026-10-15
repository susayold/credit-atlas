"""Validation-only development probability metrics on one row per loan."""
import math
import re
from bisect import bisect_right

from ..evidence_checks import require
from ..policy.engine import amount, day


def evaluate_probabilities(records, *, evaluation_cutoff, bin_edges, minimum_events=50):
    cutoff = day(evaluation_cutoff)
    require(cutoff is not None, 'Evaluation cutoff required')
    require(type(minimum_events) is int and minimum_events > 0, 'Positive support threshold required')
    edges = [amount(v) for v in bin_edges]
    require(len(edges) >= 2 and all(v is not None for v in edges)
            and edges[0] == 0 and edges[-1] == 1
            and all(a < b for a, b in zip(edges, edges[1:])), 'Bins must strictly increase from 0 to 1')
    rows = list(records)
    require(bool(rows), 'Empty evaluation cohort')
    seen = set()
    targets, probabilities = [], []
    groups = [[] for _ in edges[:-1]]
    score_digest = None
    for row in rows:
        digest = row.get('score_sha256')
        require(isinstance(digest, str) and re.fullmatch('[0-9a-f]{64}', digest), 'Score artifact digest required')
        if score_digest is None:
            score_digest = digest
        require(digest == score_digest, 'Mixed score artifacts in evaluation')
        identity = row.get('loan_id')
        require(isinstance(identity, str) and identity and identity not in seen, 'Unique evaluation loan required')
        seen.add(identity)
        require(row.get('partition') == 'validation' and row.get('included') is True,
                'Development metrics require included validation rows, never final test')
        known, landmark = day(row.get('label_known_month')), day(row.get('landmark'))
        available = day(row.get('score_available_at'))
        require(all(v is not None for v in (known, landmark, available))
                and available <= landmark <= known < cutoff, 'Invalid label/score availability order')
        target, probability = row.get('target'), amount(row.get('pd'))
        require(type(target) is int and target in (0, 1), 'Known binary validation outcome required')
        require(probability is not None and 0 <= probability <= 1, 'Finite probability in [0,1] required')
        targets.append(target)
        probabilities.append(float(probability))
        position = min(bisect_right(edges, probability) - 1, len(groups) - 1)
        groups[position].append((target, float(probability)))
    n, events = len(rows), sum(targets)
    support = min(events, n - events) >= minimum_events
    auc = average_precision = None
    if support:
        from sklearn.metrics import roc_auc_score, average_precision_score
        auc = float(roc_auc_score(targets, probabilities))
        average_precision = float(average_precision_score(targets, probabilities))
    epsilon = 1e-15
    clipped = [min(1 - epsilon, max(epsilon, p)) for p in probabilities]
    reliability = []
    for index, group in enumerate(groups):
        size = len(group)
        positives = sum(y for y, _ in group)
        reliability.append(dict(lower=str(edges[index]), upper=str(edges[index + 1]),
            upper_inclusive=index == len(groups) - 1, loans=size, events=positives,
            mean_pd=math.fsum(p for _, p in group) / size if size else None,
            event_rate=positives / size if size else None,
            support_sufficient=min(positives, size - positives) >= minimum_events))
    require(sum(r['loans'] for r in reliability) == n and sum(r['events'] for r in reliability) == events,
            'Reliability bins do not reconcile')
    return dict(status='development_validation_metrics', score_sha256=score_digest, loans=n, events=events, event_prevalence=events / n,
        roc_auc=auc, average_precision=average_precision,
        pr_metric_definition='average_precision_not_trapezoidal_pr_auc',
        discrimination_suppression_reason=None if support else 'insufficient_class_support',
        brier_score=math.fsum((p-y)**2 for p, y in zip(probabilities, targets)) / n,
        log_loss=-math.fsum(y * math.log(p) + (1-y) * math.log1p(-p) for p, y in zip(clipped, targets)) / n,
        log_loss_clip=epsilon, log_loss_clipped_predictions=sum(a != b for a, b in zip(probabilities, clipped)),
        reliability=reliability, minimum_events=minimum_events,
        evaluation_cutoff=str(cutoff), final_test_access=False, research_ready=False)
