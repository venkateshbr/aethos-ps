-- =============================================================================
-- Migration 0031: Service Line on Engagements, Practice Area + Seniority on Employees
-- =============================================================================
-- Adds classification fields needed for practice-area reporting and routing:
--   * engagements.service_line  — which practice area owns this engagement
--   * employees.practice_area   — which practice area this employee belongs to
--   * employees.seniority       — grade / level of the employee
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- engagements.service_line
-- ---------------------------------------------------------------------------
ALTER TABLE engagements
    ADD COLUMN IF NOT EXISTS service_line TEXT
    CONSTRAINT ck_engagements_service_line CHECK (
        service_line IS NULL
        OR service_line IN ('accounting', 'tax', 'cosec', 'payroll', 'advisory', 'other')
    );

-- ---------------------------------------------------------------------------
-- employees.practice_area
-- ---------------------------------------------------------------------------
ALTER TABLE employees
    ADD COLUMN IF NOT EXISTS practice_area TEXT
    CONSTRAINT ck_employees_practice_area CHECK (
        practice_area IS NULL
        OR practice_area IN ('accounting', 'tax', 'cosec', 'payroll', 'advisory', 'other')
    );

-- ---------------------------------------------------------------------------
-- employees.seniority
-- ---------------------------------------------------------------------------
ALTER TABLE employees
    ADD COLUMN IF NOT EXISTS seniority TEXT
    CONSTRAINT ck_employees_seniority CHECK (
        seniority IS NULL
        OR seniority IN ('partner', 'director', 'manager', 'senior', 'associate', 'analyst')
    );

COMMIT;
