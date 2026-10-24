"""Hand-designed heuristic weights informed by descriptive SQL analysis.

These five factors produce a priority score, not a calibrated probability.
Call duration is deliberately excluded because it is known only after contact.
"""
from dataclasses import dataclass

JOBS = ('student', 'retired', 'unemployed', 'admin.', 'management', 'unknown',
        'self-employed', 'technician', 'services', 'housemaid', 'entrepreneur', 'blue-collar')
MONTHS = ('jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec')
CONTACTS = ('cellular', 'telephone', 'unknown')
OUTCOMES = ('success', 'failure', 'other', 'unknown')


@dataclass(frozen=True)
class PriorityResult:
    score: int
    grade: str
    reasons: tuple[str, ...]


def priority_grade(score):
    if score >= 8:
        return '최우선 타겟'
    if score >= 5:
        return '우선 타겟'
    if score >= 3:
        return '일반 검토'
    return '낮은 우선순위'


def score_marketing_priority(age, job, month, contact, previous_outcome):
    if isinstance(age, bool) or not isinstance(age, int) or not 1 <= age <= 120:
        raise ValueError('age must be an integer between 1 and 120')
    for name, value, choices in [('job', job, JOBS), ('month', month, MONTHS),
                                 ('contact', contact, CONTACTS), ('previous_outcome', previous_outcome, OUTCOMES)]:
        if value not in choices:
            raise ValueError(f'Invalid {name}: {value}')
    job_points = (3 if job in ('student', 'retired') else
                  2 if job in ('unemployed', 'management', 'admin.') else
                  1 if job in ('self-employed', 'unknown', 'technician') else 0)
    age_points = 2 if age < 30 or age >= 50 else 1 if age < 40 else 0
    factors = [(job_points, f'직업: {job}'), (age_points, f'연령대: {age}세'),
               (2 if month in ('mar', 'sep', 'oct', 'dec') else 0, f'연락 월: {month}'),
               ({'cellular': 2, 'telephone': 1, 'unknown': 0}[contact], f'연락 방식: {contact}'),
               (4 if previous_outcome == 'success' else -1 if previous_outcome == 'failure' else 0,
                f'이전 캠페인 결과: {previous_outcome}')]
    score = sum(points for points, _ in factors)
    return PriorityResult(score, priority_grade(score), tuple(f'{points:+d} {reason}' for points, reason in factors))
