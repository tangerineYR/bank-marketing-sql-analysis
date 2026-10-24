import csv
import tempfile
import unittest
from pathlib import Path
from config import CSV_PATH
from scripts.load_data import COLUMNS, ROWS, read_source


class DataContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = read_source()

    def test_shape_and_target(self):
        self.assertEqual(len(self.rows), ROWS)
        self.assertEqual(list(self.rows[0]), COLUMNS)
        self.assertEqual(len(COLUMNS), 17)
        self.assertEqual({row['y'] for row in self.rows}, {'yes', 'no'})
        self.assertEqual(sum(row['y'] == 'yes' for row in self.rows), 5289)

    def test_student_absolute_count(self):
        self.assertEqual(sum(row['job'] == 'student' for row in self.rows), 938)

    def test_missing_columns_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bad.csv'
            path.write_text('age;y\n29;yes\n')
            with self.assertRaises(ValueError):
                read_source(path)

    def test_invalid_data_rejected(self):
        for mutation in [{'age': '-1'}, {'y': 'maybe'}, {'job': ''}, {'pdays': '-2'}, {'day': '32'}]:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'bad.csv'
                with path.open('w', newline='') as stream:
                    writer = csv.DictWriter(stream, fieldnames=COLUMNS, delimiter=';')
                    writer.writeheader()
                    writer.writerow(self.rows[0] | mutation)
                with self.assertRaises(ValueError):
                    read_source(path)

    def test_short_file_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'short.csv'
            with CSV_PATH.open() as stream:
                path.write_text(next(stream) + next(stream))
            with self.assertRaises(ValueError):
                read_source(path)
