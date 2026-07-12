-- =============================================================================
-- Migration 0103: Cumulative standard tenant provisioning
-- =============================================================================
-- Replaces the historical COA seed with the complete current standard chart,
-- adds the 17 established service-catalogue rows to future-tenant setup, and
-- safely backfills existing tenants. Existing rows retain their IDs. A code,
-- name, deletion-state, or semantic collision is recorded for review instead
-- of silently reactivating, renaming, retyping, relinking, or replacing data.
-- =============================================================================

BEGIN;

-- Normal balance is explicit because accumulated depreciation is a credit-
-- normal contra asset. It remains nullable for non-standard custom accounts.
ALTER TABLE accounts
    ADD COLUMN IF NOT EXISTS normal_balance TEXT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ck_accounts_normal_balance'
          AND conrelid = 'accounts'::regclass
    ) THEN
        ALTER TABLE accounts
            ADD CONSTRAINT ck_accounts_normal_balance CHECK (
                normal_balance IS NULL OR normal_balance IN ('debit', 'credit')
            );
    END IF;
END
$$;

-- Durable exception ledger. Provisioning never "fixes" a conflicting row by
-- overwriting it; operators can resolve each collision with the original row
-- and the desired semantics visible side by side in details.
CREATE TABLE IF NOT EXISTS tenant_provisioning_audit (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    entity_type         TEXT NOT NULL CHECK (entity_type IN ('account', 'service')),
    desired_code        TEXT NOT NULL,
    desired_name        TEXT NOT NULL,
    issue_type          TEXT NOT NULL,
    existing_id         UUID,
    existing_code       TEXT,
    existing_name       TEXT,
    fingerprint         TEXT NOT NULL,
    details             JSONB NOT NULL DEFAULT '{}'::jsonb,
    first_seen_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at         TIMESTAMPTZ,
    UNIQUE (tenant_id, entity_type, desired_code, issue_type, fingerprint)
);

ALTER TABLE tenant_provisioning_audit ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "tenant_isolation" ON tenant_provisioning_audit;
CREATE POLICY "tenant_isolation" ON tenant_provisioning_audit
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

DROP POLICY IF EXISTS "authenticated_member_read" ON tenant_provisioning_audit;
CREATE POLICY "authenticated_member_read" ON tenant_provisioning_audit
    FOR SELECT
    TO authenticated
    USING (public.is_tenant_member(auth.uid(), tenant_id));

CREATE INDEX IF NOT EXISTS idx_tenant_provisioning_audit_open
    ON tenant_provisioning_audit(tenant_id, entity_type, desired_code)
    WHERE resolved_at IS NULL;

CREATE OR REPLACE FUNCTION record_tenant_provisioning_issue(
    p_tenant_id UUID,
    p_entity_type TEXT,
    p_desired_code TEXT,
    p_desired_name TEXT,
    p_issue_type TEXT,
    p_existing_id UUID,
    p_existing_code TEXT,
    p_existing_name TEXT,
    p_details JSONB
)
RETURNS VOID
LANGUAGE plpgsql
SET search_path = public
AS $$
DECLARE
    issue_fingerprint TEXT;
BEGIN
    issue_fingerprint := COALESCE(p_existing_id::TEXT, p_issue_type);

    INSERT INTO tenant_provisioning_audit (
        tenant_id,
        entity_type,
        desired_code,
        desired_name,
        issue_type,
        existing_id,
        existing_code,
        existing_name,
        fingerprint,
        details
    ) VALUES (
        p_tenant_id,
        p_entity_type,
        p_desired_code,
        p_desired_name,
        p_issue_type,
        p_existing_id,
        p_existing_code,
        p_existing_name,
        issue_fingerprint,
        p_details
    )
    ON CONFLICT (
        tenant_id,
        entity_type,
        desired_code,
        issue_type,
        fingerprint
    ) DO UPDATE
    SET last_seen_at = NOW(),
        existing_code = EXCLUDED.existing_code,
        existing_name = EXCLUDED.existing_name,
        details = EXCLUDED.details,
        resolved_at = NULL;
END;
$$;

-- Complete standard chart: the 13 accounts established by migrations 0002
-- and 0076, the 3 service-line revenue accounts from 0033, and 8 operational
-- accounts required for payroll, deferrals, equipment, and depreciation.
CREATE OR REPLACE FUNCTION seed_standard_coa(p_tenant_id UUID)
RETURNS VOID
LANGUAGE plpgsql
SET search_path = public
AS $$
DECLARE
    desired RECORD;
    code_match accounts%ROWTYPE;
    name_match accounts%ROWTYPE;
    has_code_match BOOLEAN;
    has_name_match BOOLEAN;
BEGIN
    FOR desired IN
        SELECT *
        FROM (VALUES
            ('1100', 'Bank', 'asset', 'debit'),
            ('1200', 'Accounts Receivable', 'asset', 'debit'),
            ('1300', 'Input Tax Recoverable', 'asset', 'debit'),
            ('1500', 'Prepaid Expenses', 'asset', 'debit'),
            ('1600', 'Equipment', 'asset', 'debit'),
            ('1690', 'Accumulated Depreciation', 'asset', 'credit'),
            ('1999', 'Suspense', 'asset', 'debit'),
            ('2000', 'Accounts Payable', 'liability', 'credit'),
            ('2100', 'Accrued Reimbursement', 'liability', 'credit'),
            ('2150', 'Payroll Accrual', 'liability', 'credit'),
            ('2200', 'Deferred Revenue', 'liability', 'credit'),
            ('2300', 'Sales Tax Payable', 'liability', 'credit'),
            ('3000', 'Retained Earnings', 'equity', 'credit'),
            ('3100', 'Owner Capital', 'equity', 'credit'),
            ('4000', 'Revenue', 'revenue', 'credit'),
            ('4001', 'Revenue — Tax Services', 'revenue', 'credit'),
            ('4002', 'Revenue — Company Secretarial', 'revenue', 'credit'),
            ('4003', 'Revenue — Payroll', 'revenue', 'credit'),
            ('5000', 'Expenses', 'expense', 'debit'),
            ('5100', 'Employee Expenses', 'expense', 'debit'),
            ('5300', 'Payroll Expense', 'expense', 'debit'),
            ('6000', 'Software Expense', 'expense', 'debit'),
            ('6100', 'Depreciation Expense', 'expense', 'debit'),
            ('7900', 'Realized FX Gain/Loss', 'expense', 'debit')
        ) AS standard_account(code, name, account_type, normal_balance)
    LOOP
        SELECT *
        INTO code_match
        FROM accounts
        WHERE tenant_id = p_tenant_id
          AND code = desired.code;
        has_code_match := FOUND;

        IF has_code_match THEN
            IF code_match.deleted_at IS NOT NULL THEN
                PERFORM record_tenant_provisioning_issue(
                    p_tenant_id,
                    'account',
                    desired.code,
                    desired.name,
                    'soft_deleted_code_collision',
                    code_match.id,
                    code_match.code,
                    code_match.name,
                    jsonb_build_object(
                        'desired_account_type', desired.account_type,
                        'desired_normal_balance', desired.normal_balance,
                        'existing_account_type', code_match.account_type,
                        'existing_normal_balance', code_match.normal_balance,
                        'deleted_at', code_match.deleted_at
                    )
                );
                CONTINUE;
            END IF;

            IF lower(btrim(code_match.name)) = lower(btrim(desired.name))
               AND code_match.account_type::TEXT = desired.account_type
               AND code_match.is_system IS TRUE
               AND code_match.parent_id IS NULL
               AND (
                   code_match.normal_balance IS NULL
                   OR code_match.normal_balance = desired.normal_balance
               ) THEN
                -- The new column is additive provenance. Filling only NULL on
                -- an otherwise exact standard row preserves its identity and
                -- all pre-existing business semantics.
                UPDATE accounts
                SET normal_balance = desired.normal_balance
                WHERE id = code_match.id
                  AND normal_balance IS NULL;

                SELECT *
                INTO name_match
                FROM accounts
                WHERE tenant_id = p_tenant_id
                  AND code <> desired.code
                  AND lower(btrim(name)) = lower(btrim(desired.name))
                ORDER BY (deleted_at IS NULL) DESC, code, id
                LIMIT 1;
                has_name_match := FOUND;

                IF has_name_match THEN
                    PERFORM record_tenant_provisioning_issue(
                        p_tenant_id,
                        'account',
                        desired.code,
                        desired.name,
                        'duplicate_standard_name',
                        name_match.id,
                        name_match.code,
                        name_match.name,
                        jsonb_build_object(
                            'existing_account_type', name_match.account_type,
                            'existing_normal_balance', name_match.normal_balance,
                            'deleted_at', name_match.deleted_at
                        )
                    );
                END IF;
                CONTINUE;
            END IF;

            PERFORM record_tenant_provisioning_issue(
                p_tenant_id,
                'account',
                desired.code,
                desired.name,
                'code_semantic_conflict',
                code_match.id,
                code_match.code,
                code_match.name,
                jsonb_build_object(
                    'desired_account_type', desired.account_type,
                    'desired_normal_balance', desired.normal_balance,
                    'desired_is_system', TRUE,
                    'existing_account_type', code_match.account_type,
                    'existing_normal_balance', code_match.normal_balance,
                    'existing_is_system', code_match.is_system,
                    'existing_parent_id', code_match.parent_id
                )
            );
            CONTINUE;
        END IF;

        SELECT *
        INTO name_match
        FROM accounts
        WHERE tenant_id = p_tenant_id
          AND lower(btrim(name)) = lower(btrim(desired.name))
        ORDER BY (deleted_at IS NULL) DESC, code, id
        LIMIT 1;
        has_name_match := FOUND;

        IF has_name_match THEN
            PERFORM record_tenant_provisioning_issue(
                p_tenant_id,
                'account',
                desired.code,
                desired.name,
                CASE
                    WHEN name_match.deleted_at IS NOT NULL
                        THEN 'soft_deleted_name_collision'
                    ELSE 'name_code_collision'
                END,
                name_match.id,
                name_match.code,
                name_match.name,
                jsonb_build_object(
                    'desired_account_type', desired.account_type,
                    'desired_normal_balance', desired.normal_balance,
                    'existing_account_type', name_match.account_type,
                    'existing_normal_balance', name_match.normal_balance,
                    'deleted_at', name_match.deleted_at
                )
            );
            CONTINUE;
        END IF;

        INSERT INTO accounts (
            tenant_id,
            code,
            name,
            account_type,
            normal_balance,
            is_system,
            parent_id
        ) VALUES (
            p_tenant_id,
            desired.code,
            desired.name,
            desired.account_type::account_type,
            desired.normal_balance,
            TRUE,
            NULL
        )
        ON CONFLICT (tenant_id, code) DO NOTHING;
    END LOOP;
END;
$$;

-- Established service catalogue from migration 0033, now expressed as a
-- reusable tenant seed. New rows use the tenant's base currency instead of the
-- historical global GBP default. Exact matches are left untouched (including
-- deliberate is_active=false); code/name/account/currency collisions are
-- audited and skipped.
CREATE OR REPLACE FUNCTION seed_standard_service_catalogue(p_tenant_id UUID)
RETURNS VOID
LANGUAGE plpgsql
SET search_path = public
AS $$
DECLARE
    desired RECORD;
    code_match service_catalogue%ROWTYPE;
    name_match service_catalogue%ROWTYPE;
    revenue_match accounts%ROWTYPE;
    has_code_match BOOLEAN;
    has_name_match BOOLEAN;
    has_revenue_match BOOLEAN;
    expected_revenue_name TEXT;
    desired_currency TEXT;
BEGIN
    SELECT UPPER(base_currency)
    INTO STRICT desired_currency
    FROM tenants
    WHERE id = p_tenant_id;

    FOR desired IN
        SELECT *
        FROM (VALUES
            ('ACC-001', 'Monthly Management Accounts',
             'Monthly management accounts and commentary',
             'accounting', 'retainer', '4000'),
            ('ACC-002', 'Statutory Annual Accounts',
             'Statutory financial statements preparation and filing',
             'accounting', 'fixed', '4000'),
            ('ACC-003', 'CFO Advisory Services',
             'Part-time CFO and financial advisory (T&M)',
             'accounting', 'hour', '4000'),
            ('ACC-004', 'Group Consolidation',
             'Consolidated group accounts preparation',
             'accounting', 'fixed', '4000'),
            ('TAX-001', 'Corporation Tax Return (CT600)',
             'Annual corporate tax return preparation and HMRC submission',
             'tax', 'fixed', '4001'),
            ('TAX-002', 'VAT Returns (Quarterly)',
             'Quarterly VAT return preparation and submission',
             'tax', 'retainer', '4001'),
            ('TAX-003', 'Tax Advisory',
             'Ad-hoc tax planning and structuring advice',
             'tax', 'hour', '4001'),
            ('TAX-004', 'Personal Tax Return (SA100)',
             'Self-assessment personal tax return',
             'tax', 'fixed', '4001'),
            ('TAX-005', 'Trust Tax Return',
             'Trust and estate tax compliance',
             'tax', 'fixed', '4001'),
            ('TAX-006', 'CGT Computation',
             'Capital gains tax computation and reporting',
             'tax', 'fixed', '4001'),
            ('COS-001', 'Annual Confirmation Statement',
             'Annual confirmation statement filing at Companies House',
             'cosec', 'per_event', '4002'),
            ('COS-002', 'Director Appointment/Resignation',
             'AP01/TM01 filing and register update',
             'cosec', 'per_event', '4002'),
            ('COS-003', 'Share Allotment',
             'SH01 filing and shareholder register update',
             'cosec', 'per_event', '4002'),
            ('COS-004', 'COSEC Retainer',
             'Ongoing company secretarial support and compliance monitoring',
             'cosec', 'retainer', '4002'),
            ('PAY-001', 'Monthly Payroll Run',
             'Monthly payroll processing per employee',
             'payroll', 'per_employee', '4003'),
            ('PAY-002', 'Payroll Year-End (P60/P11D)',
             'Year-end payroll reconciliation and statutory returns',
             'payroll', 'fixed', '4003'),
            ('PAY-003', 'RTI Submission',
             'Real-time information filing with HMRC',
             'payroll', 'fixed', '4003')
        ) AS standard_service(
            code,
            name,
            description,
            service_line,
            billing_unit,
            revenue_code
        )
    LOOP
        expected_revenue_name := CASE desired.revenue_code
            WHEN '4000' THEN 'Revenue'
            WHEN '4001' THEN 'Revenue — Tax Services'
            WHEN '4002' THEN 'Revenue — Company Secretarial'
            WHEN '4003' THEN 'Revenue — Payroll'
        END;

        SELECT *
        INTO revenue_match
        FROM accounts
        WHERE tenant_id = p_tenant_id
          AND code = desired.revenue_code;
        has_revenue_match := FOUND;

        IF NOT has_revenue_match
           OR revenue_match.deleted_at IS NOT NULL
           OR lower(btrim(revenue_match.name)) <> lower(btrim(expected_revenue_name))
           OR revenue_match.account_type::TEXT <> 'revenue'
           OR revenue_match.normal_balance <> 'credit'
           OR revenue_match.is_system IS NOT TRUE
           OR revenue_match.parent_id IS NOT NULL THEN
            PERFORM record_tenant_provisioning_issue(
                p_tenant_id,
                'service',
                desired.code,
                desired.name,
                'missing_revenue_account',
                CASE WHEN has_revenue_match THEN revenue_match.id ELSE NULL END,
                CASE WHEN has_revenue_match THEN revenue_match.code ELSE NULL END,
                CASE WHEN has_revenue_match THEN revenue_match.name ELSE NULL END,
                jsonb_build_object(
                    'required_revenue_code', desired.revenue_code,
                    'required_revenue_name', expected_revenue_name,
                    'existing_account_type',
                        CASE WHEN has_revenue_match
                            THEN revenue_match.account_type::TEXT ELSE NULL END,
                    'existing_normal_balance',
                        CASE WHEN has_revenue_match
                            THEN revenue_match.normal_balance ELSE NULL END,
                    'existing_deleted_at',
                        CASE WHEN has_revenue_match
                            THEN revenue_match.deleted_at ELSE NULL END
                )
            );
            CONTINUE;
        END IF;

        SELECT *
        INTO code_match
        FROM service_catalogue
        WHERE tenant_id = p_tenant_id
          AND code = desired.code;
        has_code_match := FOUND;

        IF has_code_match THEN
            IF lower(btrim(code_match.name)) = lower(btrim(desired.name))
               AND COALESCE(code_match.description, '') = desired.description
               AND code_match.service_line = desired.service_line
               AND code_match.billing_unit = desired.billing_unit
               AND code_match.default_rate IS NULL
               AND upper(code_match.default_currency) = desired_currency
               AND code_match.revenue_account_id = revenue_match.id
               AND code_match.is_system IS TRUE THEN
                SELECT *
                INTO name_match
                FROM service_catalogue
                WHERE tenant_id = p_tenant_id
                  AND code <> desired.code
                  AND lower(btrim(name)) = lower(btrim(desired.name))
                ORDER BY code, id
                LIMIT 1;
                has_name_match := FOUND;

                IF has_name_match THEN
                    PERFORM record_tenant_provisioning_issue(
                        p_tenant_id,
                        'service',
                        desired.code,
                        desired.name,
                        'duplicate_standard_service_name',
                        name_match.id,
                        name_match.code,
                        name_match.name,
                        jsonb_build_object(
                            'existing_service_line', name_match.service_line,
                            'existing_billing_unit', name_match.billing_unit,
                            'existing_revenue_account_id',
                                name_match.revenue_account_id,
                            'existing_is_active', name_match.is_active
                        )
                    );
                END IF;
                CONTINUE;
            END IF;

            PERFORM record_tenant_provisioning_issue(
                p_tenant_id,
                'service',
                desired.code,
                desired.name,
                'service_code_semantic_conflict',
                code_match.id,
                code_match.code,
                code_match.name,
                jsonb_build_object(
                    'desired_description', desired.description,
                    'desired_service_line', desired.service_line,
                    'desired_billing_unit', desired.billing_unit,
                    'desired_default_currency', desired_currency,
                    'desired_revenue_account_id', revenue_match.id,
                    'existing_description', code_match.description,
                    'existing_service_line', code_match.service_line,
                    'existing_billing_unit', code_match.billing_unit,
                    'existing_default_rate', code_match.default_rate,
                    'existing_default_currency', code_match.default_currency,
                    'existing_revenue_account_id', code_match.revenue_account_id,
                    'existing_is_system', code_match.is_system,
                    'existing_is_active', code_match.is_active
                )
            );
            CONTINUE;
        END IF;

        SELECT *
        INTO name_match
        FROM service_catalogue
        WHERE tenant_id = p_tenant_id
          AND lower(btrim(name)) = lower(btrim(desired.name))
        ORDER BY code, id
        LIMIT 1;
        has_name_match := FOUND;

        IF has_name_match THEN
            PERFORM record_tenant_provisioning_issue(
                p_tenant_id,
                'service',
                desired.code,
                desired.name,
                'service_name_code_collision',
                name_match.id,
                name_match.code,
                name_match.name,
                jsonb_build_object(
                    'desired_service_line', desired.service_line,
                    'desired_billing_unit', desired.billing_unit,
                    'desired_revenue_account_id', revenue_match.id,
                    'existing_service_line', name_match.service_line,
                    'existing_billing_unit', name_match.billing_unit,
                    'existing_revenue_account_id', name_match.revenue_account_id,
                    'existing_is_system', name_match.is_system,
                    'existing_is_active', name_match.is_active
                )
            );
            CONTINUE;
        END IF;

        INSERT INTO service_catalogue (
            tenant_id,
            code,
            name,
            description,
            service_line,
            billing_unit,
            default_rate,
            default_currency,
            revenue_account_id,
            is_active,
            is_system
        ) VALUES (
            p_tenant_id,
            desired.code,
            desired.name,
            desired.description,
            desired.service_line,
            desired.billing_unit,
            NULL,
            desired_currency,
            revenue_match.id,
            TRUE,
            TRUE
        )
        ON CONFLICT (tenant_id, code) DO NOTHING;
    END LOOP;
END;
$$;

-- The original tenant trigger already calls this function by name. Redefining
-- it cumulatively keeps the existing trigger and adds service provisioning.
CREATE OR REPLACE FUNCTION trg_seed_coa_on_tenant_insert()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = public
AS $$
BEGIN
    PERFORM seed_standard_coa(NEW.id);
    PERFORM seed_standard_service_catalogue(NEW.id);
    RETURN NEW;
END;
$$;

-- Existing tenants are processed through the same guarded code path as future
-- tenants. Re-running the functions preserves IDs and is idempotent for exact
-- standard rows.
DO $$
DECLARE
    tenant_row RECORD;
BEGIN
    -- Backfill only currently usable tenants. Historical deleted rows and
    -- incomplete pre-migration signup attempts are not expanded. Every future
    -- tenant, including a newly inserted provisioning row, receives the seed
    -- from the insert trigger above.
    FOR tenant_row IN
        SELECT id
        FROM tenants
        WHERE status::TEXT = 'active'
        ORDER BY id
    LOOP
        PERFORM seed_standard_coa(tenant_row.id);
        PERFORM seed_standard_service_catalogue(tenant_row.id);
    END LOOP;
END
$$;

COMMIT;
