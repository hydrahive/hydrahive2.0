-- 005: VM + Container können einem Projekt zugewiesen werden.
--
-- 1 Server = 0 oder 1 Projekt. Beim Projekt-Löschen wird project_id auf NULL
-- gesetzt (kein CASCADE delete der Server selbst — die gehören dem User, nicht
-- dem Projekt).

ALTER TABLE vms        ADD COLUMN project_id TEXT;
ALTER TABLE containers ADD COLUMN project_id TEXT;

CREATE INDEX idx_vms_project        ON vms(project_id);
CREATE INDEX idx_containers_project ON containers(project_id);
