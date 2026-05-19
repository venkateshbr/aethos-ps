-- =============================================================================
-- seed.sql — Reference data (FX rates + system tax rates)
-- =============================================================================
-- This file is safe to run multiple times (INSERT ... ON CONFLICT DO NOTHING).
--
-- FX rates: placeholder rates for 2026-05-19 vs USD.
-- Tax rates: system-level (tenant_id IS NULL) for all 5 launch markets.
--            UK, SG, AU, IN seeded with standard rates.
--            US: admin enables per-state codes from built-in catalog (v1).
-- =============================================================================

BEGIN;

-- =============================================================================
-- FX Rates  (2026-05-19 placeholder rates — update daily via fx_refresh_worker)
-- =============================================================================
-- USD ↔ GBP
INSERT INTO fx_rates (from_currency, to_currency, rate, source, rate_date)
VALUES
    ('USD', 'GBP', 0.789500, 'seed', '2026-05-19'),
    ('GBP', 'USD', 1.266600, 'seed', '2026-05-19')
ON CONFLICT (from_currency, to_currency, rate_date) DO NOTHING;

-- USD ↔ SGD
INSERT INTO fx_rates (from_currency, to_currency, rate, source, rate_date)
VALUES
    ('USD', 'SGD', 1.348500, 'seed', '2026-05-19'),
    ('SGD', 'USD', 0.741600, 'seed', '2026-05-19')
ON CONFLICT (from_currency, to_currency, rate_date) DO NOTHING;

-- USD ↔ INR
INSERT INTO fx_rates (from_currency, to_currency, rate, source, rate_date)
VALUES
    ('USD', 'INR', 83.521000, 'seed', '2026-05-19'),
    ('INR', 'USD', 0.011972, 'seed',  '2026-05-19')
ON CONFLICT (from_currency, to_currency, rate_date) DO NOTHING;

-- USD ↔ AUD
INSERT INTO fx_rates (from_currency, to_currency, rate, source, rate_date)
VALUES
    ('USD', 'AUD', 1.551200, 'seed', '2026-05-19'),
    ('AUD', 'USD', 0.644700, 'seed', '2026-05-19')
ON CONFLICT (from_currency, to_currency, rate_date) DO NOTHING;

-- Cross pairs: GBP ↔ SGD
INSERT INTO fx_rates (from_currency, to_currency, rate, source, rate_date)
VALUES
    ('GBP', 'SGD', 1.708800, 'seed', '2026-05-19'),
    ('SGD', 'GBP', 0.585200, 'seed', '2026-05-19')
ON CONFLICT (from_currency, to_currency, rate_date) DO NOTHING;

-- Cross pairs: GBP ↔ INR
INSERT INTO fx_rates (from_currency, to_currency, rate, source, rate_date)
VALUES
    ('GBP', 'INR', 105.800000, 'seed', '2026-05-19'),
    ('INR', 'GBP', 0.009452, 'seed',  '2026-05-19')
ON CONFLICT (from_currency, to_currency, rate_date) DO NOTHING;

-- Cross pairs: GBP ↔ AUD
INSERT INTO fx_rates (from_currency, to_currency, rate, source, rate_date)
VALUES
    ('GBP', 'AUD', 1.965100, 'seed', '2026-05-19'),
    ('AUD', 'GBP', 0.508900, 'seed', '2026-05-19')
ON CONFLICT (from_currency, to_currency, rate_date) DO NOTHING;

-- Cross pairs: SGD ↔ INR
INSERT INTO fx_rates (from_currency, to_currency, rate, source, rate_date)
VALUES
    ('SGD', 'INR', 61.929000, 'seed', '2026-05-19'),
    ('INR', 'SGD', 0.016148, 'seed', '2026-05-19')
ON CONFLICT (from_currency, to_currency, rate_date) DO NOTHING;

-- Cross pairs: SGD ↔ AUD
INSERT INTO fx_rates (from_currency, to_currency, rate, source, rate_date)
VALUES
    ('SGD', 'AUD', 1.150100, 'seed', '2026-05-19'),
    ('AUD', 'SGD', 0.869500, 'seed', '2026-05-19')
ON CONFLICT (from_currency, to_currency, rate_date) DO NOTHING;

-- Cross pairs: INR ↔ AUD
INSERT INTO fx_rates (from_currency, to_currency, rate, source, rate_date)
VALUES
    ('INR', 'AUD', 0.018577, 'seed', '2026-05-19'),
    ('AUD', 'INR', 53.836000, 'seed', '2026-05-19')
ON CONFLICT (from_currency, to_currency, rate_date) DO NOTHING;


-- =============================================================================
-- System Tax Rates  (tenant_id IS NULL = visible to all tenants)
-- rate stored as fraction: 0.2000 = 20%, 0.0900 = 9%
-- =============================================================================

-- ---------------------------------------------------------------------------
-- United Kingdom — VAT
-- ---------------------------------------------------------------------------
INSERT INTO tax_rates (tenant_id, country, code, name, rate, is_default, is_active, is_seeded)
VALUES
    (NULL, 'GB', 'VAT-20', 'UK VAT Standard Rate (20%)',  0.2000, TRUE,  TRUE, TRUE),
    (NULL, 'GB', 'VAT-5',  'UK VAT Reduced Rate (5%)',    0.0500, FALSE, TRUE, TRUE),
    (NULL, 'GB', 'VAT-0',  'UK VAT Zero Rate (0%)',       0.0000, FALSE, TRUE, TRUE)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- Singapore — GST
-- ---------------------------------------------------------------------------
INSERT INTO tax_rates (tenant_id, country, code, name, rate, is_default, is_active, is_seeded)
VALUES
    (NULL, 'SG', 'GST-9',  'Singapore GST (9%)',          0.0900, TRUE,  TRUE, TRUE),
    (NULL, 'SG', 'GST-0',  'Singapore GST Zero-Rated (0%)', 0.0000, FALSE, TRUE, TRUE)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- Australia — GST
-- ---------------------------------------------------------------------------
INSERT INTO tax_rates (tenant_id, country, code, name, rate, is_default, is_active, is_seeded)
VALUES
    (NULL, 'AU', 'GST-AU-10', 'Australia GST (10%)',        0.1000, TRUE,  TRUE, TRUE),
    (NULL, 'AU', 'GST-AU-0',  'Australia GST Exports (0%)', 0.0000, FALSE, TRUE, TRUE)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- India — GST slabs
-- Note: CGST/SGST/IGST split deferred to v1.1; admin can annotate per line.
-- ---------------------------------------------------------------------------
INSERT INTO tax_rates (tenant_id, country, code, name, rate, is_default, is_active, is_seeded)
VALUES
    (NULL, 'IN', 'GST-IN-0',  'India GST 0%',   0.0000, FALSE, TRUE, TRUE),
    (NULL, 'IN', 'GST-IN-5',  'India GST 5%',   0.0500, FALSE, TRUE, TRUE),
    (NULL, 'IN', 'GST-IN-12', 'India GST 12%',  0.1200, FALSE, TRUE, TRUE),
    (NULL, 'IN', 'GST-IN-18', 'India GST 18%',  0.1800, TRUE,  TRUE, TRUE),
    (NULL, 'IN', 'GST-IN-28', 'India GST 28%',  0.2800, FALSE, TRUE, TRUE)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- United States — placeholder (per-state catalog; admin enables per tenant)
-- No default US tax rate seeded — too jurisdiction-specific.
-- We seed a zero-rate as a safe fallback that the admin can use explicitly.
-- ---------------------------------------------------------------------------
INSERT INTO tax_rates (tenant_id, country, code, name, rate, is_default, is_active, is_seeded)
VALUES
    (NULL, 'US', 'US-EXEMPT', 'US Tax Exempt / No Tax', 0.0000, FALSE, TRUE, TRUE)
ON CONFLICT DO NOTHING;

COMMIT;
