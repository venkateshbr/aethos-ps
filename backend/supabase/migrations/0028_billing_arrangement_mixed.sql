-- Migration 0028: Add 'mixed' to billing_arrangement enum
-- Mixed billing combines fixed-fee base fees with T&M overage lines.

ALTER TYPE billing_arrangement ADD VALUE IF NOT EXISTS 'mixed';
