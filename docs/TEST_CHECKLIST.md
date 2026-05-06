# ✅ Test Implementation Checklist

> Tracking-Dokument für Test-Implementierung HydraHive2  
> **Ziel:** 40% Coverage in 1 Woche, 80% in 3 Monaten

---

## 🎯 Phase 1: Foundation (1-2 Tage)

### Setup
- [ ] `pytest`, `pytest-asyncio`, `pytest-cov`, `httpx` installieren
- [ ] `core/tests/` Verzeichnis erstellen (unit/, integration/)
- [ ] `core/tests/conftest.py` mit Basis-Fixtures
- [ ] `pyproject.toml` pytest-Config hinzufügen
- [ ] `.github/workflows/tests.yml` CI-Pipeline erstellen

### Erste kritische Unit-Tests

#### Tools (Security-kritisch)
- [ ] `test_shell_exec_basic_execution`
- [ ] `test_shell_exec_timeout`
- [ ] `test_shell_exec_error_handling`
- [ ] `test_file_read_basic`
- [ ] `test_file_read_path_traversal_prevention`
- [ ] `test_file_write_basic`
- [ ] `test_file_write_path_traversal_prevention`
- [ ] `test_file_patch_basic`
- [ ] `test_file_patch_invalid_old_string`

#### Memory
- [ ] `test_memory_store_write_read`
- [ ] `test_memory_store_delete`
- [ ] `test_memory_store_list_keys`
- [ ] `test_memory_store_search`
- [ ] `test_memory_store_serialization`

#### Compaction (Datenverlust-Risiko)
- [ ] `test_compactor_basic_shrink`
- [ ] `test_compactor_preserves_important_messages`
- [ ] `test_compactor_token_counting`
- [ ] `test_cut_point_detection`

---

## 🔗 Phase 2: Integration (1 Woche)

### Agent-Runner
- [ ] `test_runner_tool_call_flow` (Mock-LLM → Tool → Response)
- [ ] `test_runner_multiple_tool_calls`
- [ ] `test_runner_tool_error_handling`
- [ ] `test_runner_context_management`
- [ ] `test_runner_compaction_trigger`

### LLM-Client
- [ ] `test_llm_client_anthropic_call` (Mock)
- [ ] `test_llm_client_provider_switching`
- [ ] `test_llm_client_token_limit_handling`
- [ ] `test_llm_client_error_retry`

### Auth & API
- [ ] `test_login_success`
- [ ] `test_login_invalid_credentials`
- [ ] `test_login_lockout_after_failed_attempts`
- [ ] `test_jwt_validation`
- [ ] `test_jwt_expiry`
- [ ] `test_protected_endpoint_requires_auth`
- [ ] `test_admin_endpoint_requires_admin_role`

### Database
- [ ] `test_session_crud`
- [ ] `test_message_crud`
- [ ] `test_message_compaction_persistence`
- [ ] `test_concurrent_session_writes`

### Plugins
- [ ] `test_plugin_loader_valid_plugin`
- [ ] `test_plugin_loader_invalid_manifest`
- [ ] `test_plugin_tool_registration`
- [ ] `test_plugin_uninstall_cleanup`

---

## 🌐 Phase 3: E2E (1-2 Wochen)

### Web-UI (Playwright)
- [ ] `test_user_login_flow`
- [ ] `test_create_session`
- [ ] `test_send_message_receive_response`
- [ ] `test_tool_call_confirmation_banner`
- [ ] `test_plugin_install_via_ui`

### AgentLink
- [ ] `test_agent_handoff_master_to_project`
- [ ] `test_agent_handoff_state_preservation`
- [ ] `test_agent_handoff_error_handling`

### Full-Stack
- [ ] `test_user_creates_session_sends_message_gets_llm_response`
- [ ] `test_admin_updates_system_via_ui`

---

## 🔒 Phase 4: Security (1 Woche)

### Auth
- [ ] `test_jwt_tampering_rejected`
- [ ] `test_user_isolation` (User A kann nicht User B's Daten sehen)
- [ ] `test_admin_only_endpoints`
- [ ] `test_rate_limiting`

### Input-Validation
- [ ] `test_path_traversal_in_all_file_tools`
- [ ] `test_command_injection_in_shell_exec`
- [ ] `test_sql_injection_if_raw_sql_exists`
- [ ] `test_xss_in_api_responses`

### Tool-Execution
- [ ] `test_shell_exec_infinite_loop_timeout`
- [ ] `test_file_write_outside_workspace_rejected`
- [ ] `test_tool_confirmation_auto_deny_after_timeout`

---

## 🚀 Phase 5: Performance (1 Woche)

### Load-Tests
- [ ] `test_session_with_1000_messages`
- [ ] `test_concurrent_10_sessions`
- [ ] `test_large_file_read_100mb`
- [ ] `test_api_rate_limiting_under_load`

### Stress-Tests
- [ ] `test_compaction_with_large_context`
- [ ] `test_memory_store_with_1000_entries`

---

## 📊 Coverage-Tracking

### Wöchentliches Update

**Woche 1:**
- Coverage: ____% (Ziel: 40%)
- Tests geschrieben: ____
- Tests passing: ____
- Bugs gefunden: ____

**Woche 2:**
- Coverage: ____% (Ziel: 50%)
- Tests geschrieben: ____
- Tests passing: ____
- Bugs gefunden: ____

**Woche 3:**
- Coverage: ____% (Ziel: 60%)
- Tests geschrieben: ____
- Tests passing: ____
- Bugs gefunden: ____

**Woche 4:**
- Coverage: ____% (Ziel: 70%)
- Tests geschrieben: ____
- Tests passing: ____
- Bugs gefunden: ____

---

## 🐛 Bug-Tracking (während Tests)

### Gefundene Bugs

| ID | Beschreibung | Severity | Status | Fixed in |
|----|--------------|----------|--------|----------|
| BUG-001 | ... | HIGH | OPEN | - |
| BUG-002 | ... | MEDIUM | FIXED | #commit-hash |

---

## 📝 Notes

- Tests sollten **schnell** sein (<10s für Unit-Tests, <1min für Integration)
- Tests sollten **isoliert** sein (keine gegenseitigen Dependencies)
- Tests sollten **deterministisch** sein (keine Flaky-Tests)
- Mock externe Services (LLM-APIs, AgentLink) für Geschwindigkeit
- Nutze `pytest -k <pattern>` um einzelne Tests zu laufen

---

## 🎓 Lessons Learned

(Während der Implementierung ausfüllen)

### Was gut funktioniert hat:
- ...

### Was schwierig war:
- ...

### Was wir nächstes Mal anders machen würden:
- ...
