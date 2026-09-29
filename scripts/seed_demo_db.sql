-- Demo SOURCE database for the Synthetic Data Studio (F8).
--
-- Finance schema: customers -> invoices -> invoice_items, invoices -> payments.
-- ~40 customers, 100 invoices, ~250 items, ~70 payments. Deterministic (no random()).
--
-- Every business rule holds for every row, so "Schema + sample" extraction
-- detects them with aggregate queries:
--   invoices.total  = SUM(invoice_items.quantity * unit_price)
--   invoices.issue_date <= invoices.due_date
--   customers.created_at <= invoices.issue_date        (through the FK)
--   payments.amount <= invoices.total
--   invoices.issue_date <= payments.paid_at            (through the FK)
--   invoices.status IN (draft, sent, paid, overdue, void)
--
-- Natural edge cases: customers without a phone or company, two customers with
-- no invoices, a leap-day invoice (2024-02-29), single-item invoices, void
-- invoices, partial payments, unpaid overdue invoices, a very long company name.
--
-- Run it in the Supabase SQL editor (or psql) as the project owner. It drops
-- and recreates ONLY the four demo tables below. Then run the read-only role
-- section at the bottom after replacing the password placeholder.

BEGIN;

DROP TABLE IF EXISTS payments, invoice_items, invoices, customers CASCADE;

CREATE TABLE customers (
    customer_id  TEXT PRIMARY KEY,
    full_name    TEXT NOT NULL,
    email        TEXT NOT NULL UNIQUE,
    phone        TEXT,
    company      TEXT,
    city         TEXT NOT NULL,
    country      TEXT NOT NULL,
    segment      TEXT NOT NULL,
    created_at   DATE NOT NULL
);

CREATE TABLE invoices (
    invoice_id   TEXT PRIMARY KEY,
    customer_id  TEXT NOT NULL REFERENCES customers (customer_id),
    issue_date   DATE NOT NULL,
    due_date     DATE NOT NULL,
    status       TEXT NOT NULL,
    currency     TEXT NOT NULL DEFAULT 'USD',
    total        NUMERIC(12, 2) NOT NULL DEFAULT 0
);

CREATE TABLE invoice_items (
    item_id      TEXT PRIMARY KEY,
    invoice_id   TEXT NOT NULL REFERENCES invoices (invoice_id),
    description  TEXT NOT NULL,
    quantity     INTEGER NOT NULL,
    unit_price   NUMERIC(10, 2) NOT NULL
);

CREATE TABLE payments (
    payment_id   TEXT PRIMARY KEY,
    invoice_id   TEXT NOT NULL REFERENCES invoices (invoice_id),
    amount       NUMERIC(12, 2) NOT NULL,
    method       TEXT NOT NULL,
    paid_at      DATE NOT NULL
);

-- 40 customers ---------------------------------------------------------------
INSERT INTO customers
SELECT
    'CUS-' || lpad(i::text, 4, '0'),
    (ARRAY['Ayesha', 'Omar', 'Lena', 'Marco', 'Priya', 'James', 'Sofia', 'Hassan', 'Mei', 'Daniel'])[1 + i % 10]
        || ' ' ||
    (ARRAY['Khan', 'Schmidt', 'Rossi', 'Patel', 'Walker', 'Garcia', 'Ahmed', 'Chen', 'Novak', 'Silva'])[1 + (i * 3) % 10],
    lower((ARRAY['ayesha', 'omar', 'lena', 'marco', 'priya', 'james', 'sofia', 'hassan', 'mei', 'daniel'])[1 + i % 10])
        || '.' || i || '@example.com',
    CASE WHEN i % 7 = 0 THEN NULL ELSE '+1 555 01' || lpad((i * 37 % 100)::text, 2, '0') || ' ' || lpad((i * 53 % 10000)::text, 4, '0') END,
    CASE
        WHEN i % 5 = 0 THEN NULL
        WHEN i = 13 THEN 'The International Consolidated Holdings and Logistics Services Company Limited'
        ELSE (ARRAY['Northwind Traders', 'Blue Harbor Ltd', 'Acme Analytics', 'Kestrel Foods', 'Orion Retail', 'Summit Health'])[1 + i % 6]
    END,
    (ARRAY['Lahore', 'Berlin', 'Milan', 'Mumbai', 'London', 'Madrid', 'Karachi', 'Shanghai', 'Prague', 'Lisbon'])[1 + (i * 7) % 10],
    (ARRAY['Pakistan', 'Germany', 'Italy', 'India', 'United Kingdom', 'Spain', 'Pakistan', 'China', 'Czechia', 'Portugal'])[1 + (i * 7) % 10],
    (ARRAY['retail', 'sme', 'enterprise'])[1 + i % 3],
    DATE '2023-01-01' + (i * 11 % 360)
FROM generate_series(1, 40) AS i;

-- 100 invoices (customers 39 and 40 have none) --------------------------------
INSERT INTO invoices (invoice_id, customer_id, issue_date, due_date, status, currency)
SELECT
    'INV-' || lpad(i::text, 5, '0'),
    c.customer_id,
    c.created_at + 20 + (i * 17 % 400),
    c.created_at + 20 + (i * 17 % 400) + (ARRAY[15, 30, 45])[1 + i % 3],
    (ARRAY['paid', 'paid', 'sent', 'overdue', 'paid', 'draft', 'paid', 'void'])[1 + i % 8],
    'USD'
FROM generate_series(1, 100) AS i
JOIN customers c ON c.customer_id = 'CUS-' || lpad((1 + (i * 7) % 38)::text, 4, '0');

-- leap-day invoice (its customer was created long before)
UPDATE invoices SET issue_date = DATE '2024-02-29', due_date = DATE '2024-03-30'
WHERE invoice_id = 'INV-00042'
  AND (SELECT created_at FROM customers c WHERE c.customer_id = invoices.customer_id) <= DATE '2024-02-29';

-- 1-4 line items per invoice ---------------------------------------------------
INSERT INTO invoice_items
SELECT
    'ITM-' || lpad(row_number() OVER (ORDER BY v.i, j)::text, 5, '0'),
    'INV-' || lpad(v.i::text, 5, '0'),
    (ARRAY['Consulting hours', 'Cloud hosting (monthly)', 'Software licence', 'Support plan', 'Data migration',
           'Training session', 'Hardware rental', 'Design work'])[1 + (v.i + j * 3) % 8],
    1 + (v.i + j * 5) % 6,
    (19.99 + ((v.i * 31 + j * 47) % 480))::NUMERIC(10, 2)
FROM generate_series(1, 100) AS v(i)
CROSS JOIN LATERAL generate_series(1, 1 + (v.i * 5) % 4) AS j;

-- invoice total = sum of its items (the rule the demo reconciles)
UPDATE invoices i
SET total = COALESCE((SELECT SUM(it.quantity * it.unit_price) FROM invoice_items it WHERE it.invoice_id = i.invoice_id), 0);

-- payments: paid in full, or a partial payment on sent/overdue invoices ----------
INSERT INTO payments
SELECT
    'PAY-' || lpad(row_number() OVER (ORDER BY i.invoice_id)::text, 5, '0'),
    i.invoice_id,
    CASE WHEN i.status = 'paid' THEN i.total ELSE round(i.total * 0.4, 2) END,
    (ARRAY['card', 'bank_transfer', 'paypal', 'cash'])[1 + (substr(i.invoice_id, 5)::int) % 4],
    i.issue_date + (substr(i.invoice_id, 5)::int * 3) % 40
FROM invoices i
WHERE i.status = 'paid' OR (i.status IN ('sent', 'overdue') AND substr(i.invoice_id, 5)::int % 2 = 0);

ANALYZE customers, invoices, invoice_items, payments;

COMMIT;

-- Sanity check: every query must return 0.
-- SELECT COUNT(*) FROM invoices i WHERE i.total <> (SELECT COALESCE(SUM(quantity * unit_price), 0) FROM invoice_items it WHERE it.invoice_id = i.invoice_id);
-- SELECT COUNT(*) FROM payments p JOIN invoices i USING (invoice_id) WHERE p.amount > i.total OR p.paid_at < i.issue_date;
-- SELECT COUNT(*) FROM invoices i JOIN customers c USING (customer_id) WHERE i.issue_date < c.created_at OR i.due_date < i.issue_date;

-- ---------------------------------------------------------------------------
-- Read-only role for the app (run once). Replace CHANGE_ME with a strong
-- password and keep it out of git. On Supabase, connect through the pooler
-- as user `demo_reader.<project-ref>`.
-- ---------------------------------------------------------------------------
-- DO $$
-- BEGIN
--     IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'demo_reader') THEN
--         CREATE ROLE demo_reader LOGIN PASSWORD 'CHANGE_ME';
--     END IF;
-- END $$;
-- ALTER ROLE demo_reader SET default_transaction_read_only = on;
-- GRANT CONNECT ON DATABASE postgres TO demo_reader;
-- GRANT USAGE ON SCHEMA public TO demo_reader;
-- GRANT SELECT ON customers, invoices, invoice_items, payments TO demo_reader;
