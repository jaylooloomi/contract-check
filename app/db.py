import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS laws(id TEXT PRIMARY KEY, name TEXT, source_url TEXT, amended_date TEXT, fetched_at TEXT);
CREATE TABLE IF NOT EXISTS articles(id INTEGER PRIMARY KEY, law_id TEXT REFERENCES laws(id), article_no TEXT,
  chapter TEXT, content TEXT, UNIQUE(law_id, article_no));
CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(content, content='articles', content_rowid='id', tokenize='trigram');
CREATE TRIGGER IF NOT EXISTS articles_ai AFTER INSERT ON articles BEGIN
  INSERT INTO articles_fts(rowid, content) VALUES (new.id, new.content); END;
CREATE TRIGGER IF NOT EXISTS articles_ad AFTER DELETE ON articles BEGIN
  INSERT INTO articles_fts(articles_fts, rowid, content) VALUES ('delete', old.id, old.content); END;
CREATE TRIGGER IF NOT EXISTS articles_au AFTER UPDATE ON articles BEGIN
  INSERT INTO articles_fts(articles_fts, rowid, content) VALUES ('delete', old.id, old.content);
  INSERT INTO articles_fts(rowid, content) VALUES (new.id, new.content); END;
CREATE TABLE IF NOT EXISTS contracts(id INTEGER PRIMARY KEY, filename TEXT, uploaded_at TEXT,
  extract_method TEXT CHECK (extract_method IN ('text','ocr')), raw_text TEXT);
CREATE TABLE IF NOT EXISTS clauses(id INTEGER PRIMARY KEY, contract_id INTEGER REFERENCES contracts(id), seq INTEGER, title TEXT, text TEXT);
CREATE TABLE IF NOT EXISTS findings(id INTEGER PRIMARY KEY, contract_id INTEGER, clause_id INTEGER REFERENCES clauses(id),
  source TEXT CHECK (source IN ('rule','ai')), title TEXT, reason TEXT, law_id TEXT, article_no TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS reviews(id INTEGER PRIMARY KEY, finding_id INTEGER REFERENCES findings(id),
  decision TEXT CHECK (decision IN ('confirm','reject')), note TEXT, reviewed_at TEXT);
"""


def connect(path="data/app.db") -> sqlite3.Connection:
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()
