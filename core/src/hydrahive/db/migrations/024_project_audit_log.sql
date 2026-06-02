-- Projekt-Audit-Log (#74): wer hat wann was an einem Projekt geändert.
-- Append-only; details_json optional für strukturierten Kontext.

CREATE TABLE IF NOT EXISTS project_audit_log (
  id           TEXT PRIMARY KEY,
  project_id   TEXT NOT NULL,
  user_id      TEXT NOT NULL,
  action       TEXT NOT NULL,
  target       TEXT,
  details_json TEXT,
  created_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_project_audit_project
  ON project_audit_log(project_id, created_at);
