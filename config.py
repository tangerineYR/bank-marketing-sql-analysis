"""Shared paths and environment-only MySQL configuration."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / 'bank-full.csv'


def connect():
    import pymysql
    return pymysql.connect(
        host=os.getenv('DB_HOST', '127.0.0.1'),
        port=int(os.getenv('DB_PORT', '3306')),
        user=os.environ['DB_USER'], password=os.environ['DB_PASSWORD'],
        database=os.environ['DB_NAME'], charset='utf8mb4', autocommit=False,
        cursorclass=pymysql.cursors.DictCursor,
    )
