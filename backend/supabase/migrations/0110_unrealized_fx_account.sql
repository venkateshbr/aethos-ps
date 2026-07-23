-- =============================================================================
-- Migration 0110: Unrealized FX Gain/Loss account (7910) for period-end
-- remeasurement (#376). Adds 7910 to the standard chart so the
-- fx_remeasurement_agent can post period-end revaluation of open foreign-currency
-- monetary balances (AR/AP) separately from realized FX (7900). Idempotent.
-- =============================================================================

BEGIN;

-- 1. Backfill 7910 into every existing tenant that lacks it.
INSERT INTO accounts (tenant_id, code, name, account_type, normal_balance, is_system)
SELECT t.id, '7910', 'Unrealized FX Gain/Loss', 'expense', 'debit', TRUE
FROM tenants t
WHERE NOT EXISTS (
    SELECT 1 FROM accounts a WHERE a.tenant_id = t.id AND a.code = '7910'
);

-- 2. Add 7910 to the standard-CoA seed so new tenants get it too. This is the
--    0103 seed_standard_coa function reproduced verbatim with the single 7910
--    row added after 7900 (idempotent per-account logic unchanged).
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
            ('7900', 'Realized FX Gain/Loss', 'expense', 'debit'),
            ('7910', 'Unrealized FX Gain/Loss', 'expense', 'debit')
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

COMMIT;
