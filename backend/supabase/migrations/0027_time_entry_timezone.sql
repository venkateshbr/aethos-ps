-- Migration 0027: timezone field on time entries (#190)
-- Stores the IANA timezone string so time entries can be displayed in the
-- user's local timezone. Defaults to UTC for all existing rows.

ALTER TABLE time_entries ADD COLUMN IF NOT EXISTS timezone TEXT NOT NULL DEFAULT 'UTC';

COMMENT ON COLUMN time_entries.timezone IS
  'IANA timezone string (e.g. "America/New_York") of the user who created the entry. '
  'Date is stored as a plain date in local time; this field disambiguates DST gaps.';
