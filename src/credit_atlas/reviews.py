"""Persistent private research findings with atomic revision/audit history."""
from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path

from .workspace import timestamp

VIEWS = {"overview", "sources", "portfolio", "vintage", "transitions", "lifecycle", "models", "loss", "evidence"}
STATUSES = {"draft", "reviewed", "archived"}
REFS = {"portfolio_monthly", "state_transitions", "segmented_transitions", "portfolio_profile",
        "vintage_competing_risk", "observed_loss_summary", "label_outcomes", "case_lineage",
        "episode_events", "model_readiness", "source_quality", "loan_timeline", "period_transitions"}


class ReviewConflict(ValueError):
    pass


class Reviews:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS findings (
                    id TEXT PRIMARY KEY, case_id TEXT NOT NULL, title TEXT NOT NULL,
                    body TEXT NOT NULL, view TEXT NOT NULL, status TEXT NOT NULL,
                    filters_json TEXT NOT NULL, refs_json TEXT NOT NULL,
                    revision INTEGER NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS finding_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, finding_id TEXT NOT NULL,
                    revision INTEGER NOT NULL, action TEXT NOT NULL, recorded_at TEXT NOT NULL,
                    record_json TEXT NOT NULL, UNIQUE(finding_id, revision));
            """)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    @staticmethod
    def decode(row):
        value = dict(row)
        value["filters"] = json.loads(value.pop("filters_json"))
        value["evidence_refs"] = json.loads(value.pop("refs_json"))
        return value

    def list(self, case_id: str):
        with self.connect() as db:
            return [self.decode(r) for r in db.execute(
                "SELECT * FROM findings WHERE case_id=? ORDER BY updated_at DESC,id", [case_id])]

    @staticmethod
    def validate(payload):
        if not isinstance(payload, dict):
            raise ValueError("Finding must be a JSON object")
        title, body = payload.get("title"), payload.get("body")
        if not isinstance(title, str) or not 1 <= len(title.strip()) <= 200:
            raise ValueError("Title must contain 1–200 characters")
        if not isinstance(body, str) or not 1 <= len(body.strip()) <= 10000:
            raise ValueError("Finding must contain 1–10000 characters")
        view, status = payload.get("view"), payload.get("status", "draft")
        if (not isinstance(view, str) or view not in VIEWS or
                not isinstance(status, str) or status not in STATUSES):
            raise ValueError("Unsupported research view or review status")
        refs = payload.get("evidence_refs", [])
        filters = payload.get("filters", {})
        if (not isinstance(refs, list) or len(refs) > 12 or
                any(not isinstance(r, str) or r not in REFS for r in refs) or len(refs) != len(set(refs))):
            raise ValueError("Evidence references must use known contract tables")
        if not isinstance(filters, dict) or len(json.dumps(filters)) > 4000:
            raise ValueError("Invalid finding filter context")
        allowed = {"segment", "basis", "horizon", "from", "to", "loan_key", "transition_year"}
        if set(filters) - allowed or any(not isinstance(v, (str, int)) for v in filters.values()):
            raise ValueError("Only bounded application filter context may be saved")
        return title.strip(), body.strip(), refs, filters

    def save(self, case_id: str, payload: dict, finding_id: str | None = None):
        title, body, refs, filters = self.validate(payload)
        now = timestamp()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            current = None
            if finding_id:
                row = db.execute("SELECT * FROM findings WHERE id=? AND case_id=?", [finding_id, case_id]).fetchone()
                if row is None:
                    raise KeyError("Finding not found in this case")
                current = self.decode(row)
                if type(payload.get("revision")) is not int or payload.get("revision") != current["revision"]:
                    raise ReviewConflict("Finding changed; reload before editing")
            identifier = finding_id or uuid.uuid4().hex
            record = {"id": identifier, "case_id": case_id, "title": title, "body": body,
                      "view": payload["view"], "status": payload.get("status", "draft"),
                      "filters": filters, "evidence_refs": refs,
                      "revision": current["revision"] + 1 if current else 1,
                      "created_at": current["created_at"] if current else now, "updated_at": now}
            db.execute("""INSERT INTO findings VALUES(?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET title=excluded.title,body=excluded.body,
                  view=excluded.view,status=excluded.status,filters_json=excluded.filters_json,
                  refs_json=excluded.refs_json,revision=excluded.revision,updated_at=excluded.updated_at""",
                [record["id"], case_id, title, body, record["view"], record["status"],
                 json.dumps(filters, ensure_ascii=False), json.dumps(refs), record["revision"],
                 record["created_at"], now])
            db.execute("INSERT INTO finding_history(finding_id,revision,action,recorded_at,record_json) VALUES(?,?,?,?,?)",
                       [identifier, record["revision"], "updated" if current else "created", now,
                        json.dumps(record, ensure_ascii=False)])
        return record

    def history(self, case_id: str, finding_id: str):
        with self.connect() as db:
            if db.execute("SELECT 1 FROM findings WHERE id=? AND case_id=?", [finding_id, case_id]).fetchone() is None:
                raise KeyError("Finding not found in this case")
            return [dict(revision=r[0], action=r[1], recorded_at=r[2], record=json.loads(r[3])) for r in
                    db.execute("SELECT revision,action,recorded_at,record_json FROM finding_history WHERE finding_id=? ORDER BY revision", [finding_id])]
