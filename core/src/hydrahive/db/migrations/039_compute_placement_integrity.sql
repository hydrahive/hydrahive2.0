-- 039: Enforce compute-node placement without rebuilding legacy resource tables.
CREATE INDEX IF NOT EXISTS idx_containers_node_id ON containers(node_id);
CREATE INDEX IF NOT EXISTS idx_vms_node_id ON vms(node_id);

CREATE TRIGGER IF NOT EXISTS containers_node_exists_insert
BEFORE INSERT ON containers
WHEN NOT EXISTS (SELECT 1 FROM compute_nodes WHERE node_id = NEW.node_id)
BEGIN
    SELECT RAISE(ABORT, 'compute_node_not_found');
END;

CREATE TRIGGER IF NOT EXISTS containers_node_exists_update
BEFORE UPDATE OF node_id ON containers
WHEN NOT EXISTS (SELECT 1 FROM compute_nodes WHERE node_id = NEW.node_id)
BEGIN
    SELECT RAISE(ABORT, 'compute_node_not_found');
END;

CREATE TRIGGER IF NOT EXISTS vms_node_exists_insert
BEFORE INSERT ON vms
WHEN NOT EXISTS (SELECT 1 FROM compute_nodes WHERE node_id = NEW.node_id)
BEGIN
    SELECT RAISE(ABORT, 'compute_node_not_found');
END;

CREATE TRIGGER IF NOT EXISTS vms_node_exists_update
BEFORE UPDATE OF node_id ON vms
WHEN NOT EXISTS (SELECT 1 FROM compute_nodes WHERE node_id = NEW.node_id)
BEGIN
    SELECT RAISE(ABORT, 'compute_node_not_found');
END;

CREATE TRIGGER IF NOT EXISTS vms_runtime_matches_node_insert
BEFORE INSERT ON vms
WHEN (NEW.node_id = 'local' AND NEW.runtime != 'qemu')
  OR (NEW.node_id != 'local' AND NEW.runtime != 'incus')
BEGIN
    SELECT RAISE(ABORT, 'vm_runtime_node_mismatch');
END;

CREATE TRIGGER IF NOT EXISTS vms_runtime_matches_node_update
BEFORE UPDATE OF node_id, runtime ON vms
WHEN (NEW.node_id = 'local' AND NEW.runtime != 'qemu')
  OR (NEW.node_id != 'local' AND NEW.runtime != 'incus')
BEGIN
    SELECT RAISE(ABORT, 'vm_runtime_node_mismatch');
END;

CREATE TRIGGER IF NOT EXISTS compute_nodes_restrict_delete
BEFORE DELETE ON compute_nodes
WHEN OLD.node_id = 'local'
  OR EXISTS (SELECT 1 FROM containers WHERE node_id = OLD.node_id)
  OR EXISTS (SELECT 1 FROM vms WHERE node_id = OLD.node_id)
BEGIN
    SELECT RAISE(ABORT, 'compute_node_in_use');
END;
