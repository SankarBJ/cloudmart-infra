CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    price NUMERIC(10,2) NOT NULL,
    description TEXT
);

INSERT INTO products (name, price, description)
VALUES
('CloudMart Laptop', 59999.00, 'High-performance cloud-ready laptop'),
('CloudMart Smartphone', 24999.00, 'Modern Android smartphone'),
('CloudMart Headphones', 3999.00, 'Wireless noise-cancelling headphones'),
('CloudMart Keyboard', 1999.00, 'Mechanical wireless keyboard')
ON CONFLICT DO NOTHING;
