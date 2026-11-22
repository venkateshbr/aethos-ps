-- Isolated PostgREST test schema, not a production migration.
CREATE ROLE anon NOLOGIN;
CREATE ROLE authenticated NOLOGIN;
CREATE ROLE service_role NOLOGIN BYPASSRLS;
GRANT anon, authenticated, service_role TO postgres;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO service_role;
CREATE TABLE tenants (id uuid PRIMARY KEY, stripe_subscription_status text, trial_ends_at timestamptz, billing_access_override_until timestamptz);
CREATE TABLE tenant_users (id uuid PRIMARY KEY, tenant_id uuid REFERENCES tenants, user_id uuid, role text, must_change_password boolean DEFAULT false, deleted_at timestamptz);
CREATE TABLE chat_threads (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id uuid, user_id uuid, title text, created_at timestamptz DEFAULT now(), updated_at timestamptz DEFAULT now(), deleted_at timestamptz);
CREATE TABLE chat_messages (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), thread_id uuid REFERENCES chat_threads, tenant_id uuid, role text, content text, model text, tool_name text);
CREATE TABLE accounts (id uuid PRIMARY KEY, code text);
CREATE TABLE journal_entries (id uuid PRIMARY KEY, period text, entry_date date, posted_at timestamptz, reference_type text, reference_id uuid);
CREATE TABLE journal_lines (tenant_id uuid, account_id uuid REFERENCES accounts, journal_entry_id uuid REFERENCES journal_entries, direction text, base_amount numeric(15,2));
INSERT INTO tenants(id, stripe_subscription_status) VALUES
 ('00000000-0000-0000-0000-000000000001', 'active'),
 ('00000000-0000-0000-0000-000000000002', 'active');
INSERT INTO tenant_users(id, tenant_id, user_id, role) VALUES
 ('00000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000021', 'manager'),
 ('00000000-0000-0000-0000-000000000012', '00000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000022', 'viewer');
INSERT INTO accounts VALUES ('00000000-0000-0000-0000-000000000031', '1200');
INSERT INTO journal_entries VALUES ('00000000-0000-0000-0000-000000000041', '2020-01', '2020-01-01', '2020-01-01', 'synthetic', null);
INSERT INTO journal_lines VALUES
 ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000031', '00000000-0000-0000-0000-000000000041', 'DR', 125.00),
 ('00000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000031', '00000000-0000-0000-0000-000000000041', 'DR', 987.00);
