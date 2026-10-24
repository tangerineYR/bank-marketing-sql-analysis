"""Opt-in integration tests replace project data in the configured test database."""
import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from config import connect
from scripts.load_data import COLUMNS, LOOKUPS, ROWS, load_data, read_source, verify_integrity
from scripts.run_analysis import run_analysis, validate_summary, write_summary


@unittest.skipUnless(os.getenv('RUN_DB_TESTS') == '1', 'Set RUN_DB_TESTS=1 for a dedicated MySQL test database')
class DatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.first = load_data()
        cls.first_hash = cls.fingerprint()
        cls.second = load_data()

    @staticmethod
    def fingerprint():
        digest = hashlib.sha256()
        with connect() as connection, connection.cursor() as cur:
            for table in ['staging_bank_full', *LOOKUPS, 'client_record', 'campaign_contact']:
                cur.execute(f'SELECT * FROM {table} ORDER BY 1')
                digest.update(json.dumps(cur.fetchall(), sort_keys=True).encode())
        return digest.hexdigest()

    def test_schema_table_count(self):
        with connect() as connection, connection.cursor() as cur:
            cur.execute('SHOW TABLES')
            self.assertEqual({next(iter(row.values())) for row in cur.fetchall()},
                             {'staging_bank_full', *LOOKUPS, 'client_record', 'campaign_contact'})

    def test_double_load(self):
        self.assertEqual(self.first, self.second)
        self.assertEqual(self.first_hash, self.fingerprint())
        self.assertEqual(set(self.second['counts'].values()), {ROWS})
        self.assertFalse(any(self.second['fk_orphans'].values()))
        self.assertEqual(self.second['duplicate_source_row_ids'], 0)

    def test_all_source_columns_round_trip(self):
        with connect() as connection, connection.cursor() as cur:
            cur.execute('''SELECT r.age, j.value AS job, m.value AS marital, e.value AS education,
                r.default_credit AS `default`, r.balance, r.housing, r.loan, cm.value AS contact,
                c.day, c.month, c.duration, c.campaign, c.pdays, c.previous, p.value AS poutcome,
                c.subscribed AS y FROM client_record r JOIN campaign_contact c USING (source_row_id)
                JOIN job j ON j.id=r.job_id JOIN marital_status m ON m.id=r.marital_status_id
                JOIN education e ON e.id=r.education_id JOIN contact_method cm ON cm.id=c.contact_method_id
                JOIN previous_outcome p ON p.id=c.previous_outcome_id ORDER BY r.source_row_id''')
            self.assertEqual(cur.fetchall(), read_source())
            cur.execute('SELECT source_row_id FROM staging_bank_full ORDER BY source_row_id')
            self.assertEqual([row['source_row_id'] for row in cur.fetchall()], list(range(1, ROWS + 1)))
            cur.execute('SELECT ' + ','.join(f'`{c}`' for c in COLUMNS) + ' FROM staging_bank_full ORDER BY source_row_id')
            self.assertEqual(cur.fetchall(), read_source())

    def test_failure_rolls_back(self):
        def fail(connection):
            with connection.cursor() as cur:
                cur.execute('UPDATE client_record SET balance=0')
            raise RuntimeError('Injected failure before commit')
        before = self.fingerprint()
        with self.assertRaisesRegex(RuntimeError, 'Injected failure'):
            load_data(before_verify=fail)
        self.assertEqual(self.fingerprint(), before)
        with connect() as connection:
            verify_integrity(connection)

    def test_database_constraints(self):
        import pymysql
        statements = ["INSERT INTO job (id,value) VALUES (99,'student')",
                      "INSERT INTO job (id,value) VALUES (99,NULL)",
                      'UPDATE client_record SET job_id=999 WHERE source_row_id=1',
                      'UPDATE campaign_contact SET duration=-1 WHERE source_row_id=1',
                      'UPDATE campaign_contact SET pdays=-2 WHERE source_row_id=1',
                      'UPDATE campaign_contact SET source_row_id=999999 WHERE source_row_id=1',
                      'UPDATE client_record SET source_row_id=2 WHERE source_row_id=1']
        for statement in statements:
            with self.subTest(statement=statement), connect() as connection:
                with self.assertRaises(pymysql.MySQLError), connection.cursor() as cur:
                    cur.execute(statement)
                connection.rollback()

    def test_analysis_artifact(self):
        summary = run_analysis()
        validate_summary(summary)
        student = next(row for row in summary['job_rates'] if row['category'] == 'student')
        self.assertEqual(student['total'], 938)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'analysis.json'
            write_summary(summary, path)
            self.assertEqual(json.loads(path.read_text()), summary)
        broken = copy.deepcopy(summary)
        broken['job_rates'][0]['total'] *= 6
        with self.assertRaises(ValueError):
            validate_summary(broken)

    def test_sql_matches_independent_source_aggregation(self):
        from collections import defaultdict
        rows, summary = read_source(), run_analysis()
        for name, key in [('job_rates', 'job'), ('month_rates', 'month'), ('contact_rates', 'contact'),
                          ('previous_outcome_rates', 'poutcome'), ('age_band_rates', 'age')]:
            expected = defaultdict(lambda: [0, 0])
            for row in rows:
                value = row[key]
                if key == 'age':
                    value = '<30' if value < 30 else '30-39' if value < 40 else '40-49' if value < 50 else '50+'
                expected[value][0] += 1
                expected[value][1] += row['y'] == 'yes'
            self.assertEqual({g['category']: [g['total'], g['subscribed']] for g in summary[name]}, dict(expected))
