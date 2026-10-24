"""Run SQL analysis: python -m scripts.run_analysis [--output PATH]."""
import argparse
import json
import os
import re
import tempfile
from decimal import Decimal
from pathlib import Path
from config import ROOT, connect
from scripts.load_data import ROWS, verify_integrity


def validate_summary(summary):
    overall = summary['overall']
    if summary['source_rows'] != ROWS or overall['total'] != ROWS or overall['subscribed'] != 5289:
        raise ValueError('Unexpected overall counts')
    for name in ['job_rates', 'age_band_rates', 'month_rates', 'contact_rates', 'previous_outcome_rates']:
        groups = summary[name]
        if sum(g['total'] for g in groups) != ROWS or sum(g['subscribed'] for g in groups) != 5289:
            raise ValueError(f'Invalid aggregate counts: {name}')
        if len({g['category'] for g in groups}) != len(groups):
            raise ValueError(f'Duplicate group: {name}')
        for group in groups:
            if not 0 <= group['subscribed'] <= group['total'] or abs(group['rate_percent'] - 100 * group['subscribed'] / group['total']) > 0.001:
                raise ValueError(f'Invalid rate: {name}')
    expected = {'job_rates': {'student': 28.7, 'retired': 22.8},
                'month_rates': {'mar': 52.0, 'sep': 46.5, 'oct': 43.8, 'dec': 46.7},
                'previous_outcome_rates': {'success': 64.7}}
    if abs(overall['rate_percent'] - 100 * 5289 / ROWS) > 0.001:
        raise ValueError('Unexpected overall rate')
    for name, rates in expected.items():
        actual = {row['category']: row['rate_percent'] for row in summary[name]}
        for category, rate in rates.items():
            if abs(actual[category] - rate) > 0.1:
                raise ValueError(f'Unexpected descriptive rate: {name}/{category}')


def run_analysis():
    summary = {'source_rows': ROWS, 'rate_unit': 'percent',
               'interpretation': 'Historical descriptive associations, not predicted probabilities or causal effects.'}
    with connect() as connection:
        verify_integrity(connection)
        with connection.cursor() as cur:
            for block in (ROOT / 'sql/analysis.sql').read_text().split(';'):
                if not block.strip():
                    continue
                name = re.search(r'-- name: (\w+)', block).group(1)
                cur.execute(block)
                rows = [{key: (int(value) if key == 'subscribed' else float(value))
                         if isinstance(value, Decimal) else value
                         for key, value in row.items()} for row in cur.fetchall()]
                summary[name] = rows[0] if name == 'overall' else rows
    validate_summary(summary)
    return summary


def write_summary(summary, path):
    validate_summary(summary)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(summary, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'results/analysis_summary.json')
    args = parser.parse_args()
    write_summary(run_analysis(), args.output)
    print(f'Validated SQL analysis written to {args.output}')
