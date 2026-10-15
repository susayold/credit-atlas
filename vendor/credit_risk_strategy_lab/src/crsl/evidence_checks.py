"""Mandatory evidence guards; remain active under Python -O."""
from .source import sha256


def require(condition, message):
    if not condition:
        raise ValueError(message)


def require_hash(path, expected):
    require(sha256(path) == expected, f'Evidence hash mismatch: {path.name}')


def require_outcome_totals(outcomes, loans):
    require(type(loans) is int and loans > 0, 'Invalid loan denominator')
    names = [row['outcome'] for row in outcomes]
    require(len(names) == len(set(names)), 'Duplicate outcome groups')
    require(all(isinstance(n, str) and n for n in names), 'Invalid outcome name')
    require(all(type(row['loans']) is int and row['loans'] >= 0 for row in outcomes),
            'Invalid outcome counts')
    require(sum(row['loans'] for row in outcomes) == loans,
            'Outcome counts do not reconcile to loan denominator')
