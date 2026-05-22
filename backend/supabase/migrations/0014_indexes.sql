BEGIN;

-- Invoices: most common query pattern is tenant+status+due_date
CREATE INDEX IF NOT EXISTS idx_invoices_tenant_status_due
    ON invoices(tenant_id, status, due_date) WHERE deleted_at IS NULL;

-- Bills: same for AP aging
CREATE INDEX IF NOT EXISTS idx_bills_tenant_status_due
    ON bills(tenant_id, status, due_date) WHERE deleted_at IS NULL;

-- Time entries: billing run + WIP queries filter by project+date+billing_status
CREATE INDEX IF NOT EXISTS idx_time_entries_project_billing
    ON time_entries(tenant_id, project_id, billing_status, date) WHERE deleted_at IS NULL;

-- Journal lines: fetched by journal_entry_id on every post
CREATE INDEX IF NOT EXISTS idx_journal_lines_entry
    ON journal_lines(journal_entry_id);

-- Agent suggestions: autonomy promoter queries by tenant+agent+created_at
CREATE INDEX IF NOT EXISTS idx_agent_suggestions_tenant_agent
    ON agent_suggestions(tenant_id, agent_name, action_type, created_at);

-- HITL tasks: inbox query by tenant+status
CREATE INDEX IF NOT EXISTS idx_hitl_tasks_tenant_status
    ON hitl_tasks(tenant_id, status, created_at DESC);

-- Chat messages: paginated per thread
CREATE INDEX IF NOT EXISTS idx_chat_messages_thread
    ON chat_messages(thread_id, created_at);

-- Payments: look up by invoice
CREATE INDEX IF NOT EXISTS idx_payments_invoice
    ON payments(tenant_id, invoice_id);

COMMIT;
