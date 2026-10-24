"""Load with `python -m scripts.load_data` after exporting DB_* variables.

Use a dedicated MySQL 8.0.16+ database. Schema creation is separate because MySQL
DDL commits implicitly. All data replacement is one InnoDB transaction: failure
preserves the previous load (or leaves an empty schema on first initialization).
Only the eight declared tables are replaced; legacy tables are not migrated.
"""
import csv
import json
from config import CSV_PATH, ROOT, connect

COLUMNS = 'age job marital education default balance housing loan contact day month duration campaign pdays previous poutcome y'.split()
ROWS = 45211
LOOKUPS = {'job': 'job', 'marital_status': 'marital', 'education': 'education',
           'contact_method': 'contact', 'previous_outcome': 'poutcome'}
CATEGORIES = {
    'job': 'admin. blue-collar entrepreneur housemaid management retired self-employed services student technician unemployed unknown'.split(),
    'marital': ['divorced', 'married', 'single'],
    'education': ['primary', 'secondary', 'tertiary', 'unknown'],
    'contact': ['cellular', 'telephone', 'unknown'],
    'poutcome': ['failure', 'other', 'success', 'unknown'],
    'month': 'jan feb mar apr may jun jul aug sep oct nov dec'.split(),
    **{key: ['yes', 'no'] for key in ['default', 'housing', 'loan', 'y']},
}
INTEGERS = {'age': (1, 120), 'balance': (-2147483648, 2147483647),
            'day': (1, 31), 'duration': (0, 2147483647), 'campaign': (1, 2147483647),
            'pdays': (-1, 2147483647), 'previous': (0, 2147483647)}


def read_source(path=CSV_PATH):
    with open(path, newline='', encoding='utf-8') as stream:
        reader = csv.DictReader(stream, delimiter=';')
        if reader.fieldnames != COLUMNS:
            raise ValueError('Expected the 17 ordered source columns')
        rows = []
        for number, row in enumerate(reader, 1):
            if set(row) != set(COLUMNS) or any(v is None or v == '' for v in row.values()):
                raise ValueError(f'Malformed source row {number}')
            for key, choices in CATEGORIES.items():
                if row[key] not in choices:
                    raise ValueError(f'Invalid {key} at source row {number}')
            for key, (low, high) in INTEGERS.items():
                value = int(row[key])
                if not low <= value <= high:
                    raise ValueError(f'Invalid {key} at source row {number}')
                row[key] = value
            rows.append(row)
    if len(rows) != ROWS:
        raise ValueError(f'Expected {ROWS} source rows, got {len(rows)}')
    return rows


def statements(path):
    return [part.strip() for part in path.read_text().split(';') if part.strip()]


def verify_integrity(connection):
    counts, orphans = {}, {}
    with connection.cursor() as cur:
        for table in ['staging_bank_full', 'client_record', 'campaign_contact']:
            cur.execute(f'SELECT COUNT(*) AS n, COUNT(DISTINCT source_row_id) AS d FROM {table}')
            result = cur.fetchone()
            counts[table] = result['n']
            if result['n'] != ROWS or result['d'] != ROWS:
                raise ValueError(f'Invalid row count or duplicate ID in {table}')
        relations = [('client_record', 'staging_bank_full', 'source_row_id', 'source_row_id'),
                     ('campaign_contact', 'client_record', 'source_row_id', 'source_row_id')]
        relations += [('client_record' if table in ['job', 'marital_status', 'education'] else 'campaign_contact', table, table + '_id', 'id') for table in LOOKUPS]
        for child, parent, fk, pk in relations:
            cur.execute(f'SELECT COUNT(*) AS n FROM {child} c LEFT JOIN {parent} p ON c.{fk}=p.{pk} WHERE p.{pk} IS NULL')
            orphans[f'{child}.{fk}'] = cur.fetchone()['n']
        if any(orphans.values()):
            raise ValueError('Foreign key orphan detected')
    return {'counts': counts, 'fk_orphans': orphans, 'duplicate_source_row_ids': 0}


def load_data(path=CSV_PATH, *, before_verify=None):
    rows = read_source(path)  # Validate before any database mutation.
    connection = connect()
    locked = False
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT GET_LOCK(CONCAT(DATABASE(), ':bank_load'), 30) AS acquired")
            locked = cur.fetchone()['acquired'] == 1
            if not locked:
                raise RuntimeError('Another loader holds the database lock')
            for statement in statements(ROOT / 'sql/schema.sql'):
                cur.execute(statement)
        connection.begin()
        with connection.cursor() as cur:
            for table in ['campaign_contact', 'client_record', *LOOKUPS, 'staging_bank_full']:
                cur.execute(f'DELETE FROM {table}')
            fields = ', '.join(f'`{column}`' for column in COLUMNS)
            cur.executemany(f'INSERT INTO staging_bank_full (source_row_id, {fields}) VALUES ({", ".join(["%s"] * 18)})',
                            [(i, *(row[c] for c in COLUMNS)) for i, row in enumerate(rows, 1)])
            for table, column in LOOKUPS.items():
                values = sorted({row[column] for row in rows})
                cur.executemany(f'INSERT INTO {table} (id, value) VALUES (%s, %s)', list(enumerate(values, 1)))
            cur.execute('''INSERT INTO client_record
                SELECT s.source_row_id, s.age, j.id, m.id, e.id, s.`default`, s.balance, s.housing, s.loan
                FROM staging_bank_full s JOIN job j ON j.value=s.job
                JOIN marital_status m ON m.value=s.marital JOIN education e ON e.value=s.education''')
            cur.execute('''INSERT INTO campaign_contact
                SELECT s.source_row_id, c.id, s.day, s.month, s.duration, s.campaign,
                       s.pdays, s.previous, p.id, s.y
                FROM staging_bank_full s JOIN contact_method c ON c.value=s.contact
                JOIN previous_outcome p ON p.value=s.poutcome''')
        if before_verify is not None:
            before_verify(connection)
        report = verify_integrity(connection)
        connection.commit()
        return report
    except BaseException:
        connection.rollback()
        raise
    finally:
        if locked:
            with connection.cursor() as cur:
                cur.execute("SELECT RELEASE_LOCK(CONCAT(DATABASE(), ':bank_load'))")
        connection.close()


if __name__ == '__main__':
    print(json.dumps(load_data(), indent=2))
