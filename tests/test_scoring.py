import itertools
import unittest
from scoring import JOBS, MONTHS, CONTACTS, OUTCOMES, priority_grade, score_marketing_priority


class ScoringTests(unittest.TestCase):
    def score(self, **overrides):
        args = dict(age=45, job='blue-collar', month='jan', contact='unknown', previous_outcome='unknown')
        args.update(overrides)
        return score_marketing_priority(**args).score

    def test_previous_outcomes(self):
        for outcome, expected in [('success', 4), ('failure', -1), ('other', 0), ('unknown', 0)]:
            with self.subTest(outcome=outcome):
                self.assertEqual(self.score(previous_outcome=outcome), expected)

    def test_jobs(self):
        expected = [3, 3, 2, 2, 2, 1, 1, 1, 0, 0, 0, 0]
        for job, points in zip(JOBS, expected):
            with self.subTest(job=job):
                self.assertEqual(self.score(job=job), points)

    def test_age_boundaries(self):
        for age, points in [(25, 2), (26, 2), (29, 2), (30, 1), (39, 1), (40, 0), (49, 0), (50, 2)]:
            with self.subTest(age=age):
                self.assertEqual(self.score(age=age), points)

    def test_months(self):
        for month in MONTHS:
            self.assertEqual(self.score(month=month), 2 if month in ('mar', 'sep', 'oct', 'dec') else 0)

    def test_contacts(self):
        for contact, expected in [('cellular', 2), ('telephone', 1), ('unknown', 0)]:
            self.assertEqual(self.score(contact=contact), expected)

    def test_grade_boundaries(self):
        for score, grade in [(-1, '낮은 우선순위'), (2, '낮은 우선순위'), (3, '일반 검토'),
                             (4, '일반 검토'), (5, '우선 타겟'), (7, '우선 타겟'), (8, '최우선 타겟'), (13, '최우선 타겟')]:
            self.assertEqual(priority_grade(score), grade)

    def test_range(self):
        scores = [score_marketing_priority(*args).score for args in
                  itertools.product([29, 35, 45, 50], JOBS, MONTHS, CONTACTS, OUTCOMES)]
        self.assertEqual((min(scores), max(scores)), (-1, 13))

    def test_reasons_and_result(self):
        result = score_marketing_priority(29, 'student', 'mar', 'cellular', 'success')
        self.assertEqual(result.score, 13)
        self.assertEqual(result.grade, '최우선 타겟')
        self.assertEqual(len(result.reasons), 5)
        self.assertEqual(sum(int(reason.split()[0]) for reason in result.reasons), result.score)

    def test_invalid_input(self):
        for values in [{'age': True}, {'age': 29.5}, {'age': 0}, {'age': 121}, {'job': 'admin'},
                       {'month': 'March'}, {'contact': ''}, {'previous_outcome': 'invalid'}]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.score(**values)
