-- CloudMart Complete Relational E-Commerce Schema
-- Preserves products table and adds full relational support

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    phone_number VARCHAR(20),
    role VARCHAR(20) DEFAULT 'customer',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price NUMERIC(10, 2) NOT NULL CHECK (price >= 0),
    stock INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    category VARCHAR(100) NOT NULL DEFAULT 'General',
    image_url TEXT,
    rating NUMERIC(2, 1) DEFAULT 4.5,
    rating_count INTEGER DEFAULT 120,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE RESTRICT,
    total_amount NUMERIC(10, 2) NOT NULL CHECK (total_amount >= 0),
    shipping_address TEXT NOT NULL,
    shipping_city VARCHAR(100) NOT NULL,
    shipping_postal_code VARCHAR(20) NOT NULL,
    status VARCHAR(50) DEFAULT 'PENDING',
    payment_method VARCHAR(50) DEFAULT 'SIMULATED_CARD',
    idempotency_key VARCHAR(100) UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id) ON DELETE RESTRICT,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(10, 2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS shipments (
    id SERIAL PRIMARY KEY,
    order_id INTEGER UNIQUE REFERENCES orders(id) ON DELETE CASCADE,
    current_status VARCHAR(50) DEFAULT 'ORDERED',
    warehouse_name VARCHAR(100) DEFAULT 'Chennai Central Fulfillment Center',
    current_location VARCHAR(150) DEFAULT 'Warehouse Processing Bay 4',
    latitude NUMERIC(9, 6) DEFAULT 13.0827,
    longitude NUMERIC(9, 6) DEFAULT 80.2707,
    estimated_delivery TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP + INTERVAL '2 days'),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS delivery_otps (
    id SERIAL PRIMARY KEY,
    order_id INTEGER UNIQUE REFERENCES orders(id) ON DELETE CASCADE,
    otp_code_hash VARCHAR(255) NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    is_verified BOOLEAN DEFAULT FALSE,
    attempts INTEGER DEFAULT 0,
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP + INTERVAL '24 hours'),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_price ON products(price);
CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_shipments_order_id ON shipments(order_id);

-- Seed Rich Catalog Data
INSERT INTO products (name, description, price, stock, category, image_url, rating, rating_count) VALUES
('Echo Wave Smart Speaker with Alexa', 'Rich HD audio smart speaker with voice control, temperature sensor, and smart home hub integration.', 49.99, 50, 'Electronics', 'https://images.unsplash.com/photo-1543512214-318c7553f230?w=600&auto=format&fit=crop&q=80', 4.7, 342),
('Kindle Paperwhite 16GB Display', 'Now with a 6.8 inch display, adjustable warm light, up to 10 weeks of battery life, and glare-free 300 ppi screen.', 139.99, 35, 'Electronics', 'https://images.unsplash.com/photo-1592496431122-2349e0fbc666?w=600&auto=format&fit=crop&q=80', 4.8, 890),
('CloudSonic Noise Cancelling Headphones', 'Over-ear Bluetooth wireless headphones with active noise cancelling and 40-hour playback.', 89.99, 40, 'Electronics', 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&auto=format&fit=crop&q=80', 4.6, 520),
('Stainless Steel Insulated Water Bottle 1L', 'Double-wall vacuum insulated flask keeps beverages cold for 24 hours or hot for 12 hours.', 24.99, 120, 'Home & Kitchen', 'https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=600&auto=format&fit=crop&q=80', 4.5, 215),
('Barista Touch Espresso Coffee Maker', 'Automatic micro-foam milk texturing with intuitive touch screen display and 15 bar pressure pump.', 299.99, 15, 'Home & Kitchen', 'https://images.unsplash.com/photo-1517668808822-9ebb02f2a0e6?w=600&auto=format&fit=crop&q=80', 4.9, 145),
('Ergonomic Memory Foam Office Chair Cushion', 'Orthopedic seat cushion designed to relieve lower back and tailbone sciatica pain during long work hours.', 34.50, 75, 'Office', 'https://images.unsplash.com/photo-1580481077195-c3a9927b798b?w=600&auto=format&fit=crop&q=80', 4.4, 430),
('CloudTech Pro Mechanical Keyboard', 'RGB backlit mechanical gaming and coding keyboard with tactile brown switches and USB-C detachable cable.', 69.99, 60, 'Electronics', 'https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=600&auto=format&fit=crop&q=80', 4.7, 610),
('Organic Cotton Breathable Crewneck T-Shirt', 'Premium 100% ring-spun combed cotton t-shirt with modern tailored fit and pre-shrunk fabric.', 19.99, 150, 'Fashion', 'https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=600&auto=format&fit=crop&q=80', 4.3, 180),
('Waterproof Outdoor Trail Hiking Backpack 40L', 'Lightweight ripstop nylon trekking bag with built-in rain cover and ergonomic shoulder straps.', 54.99, 45, 'Sports & Outdoors', 'https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=600&auto=format&fit=crop&q=80', 4.6, 290),
('Designing Data-Intensive Applications Book', 'The definitive guide to the architecture, storage engines, transactions, and distributed data systems.', 42.00, 80, 'Books', 'https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=600&auto=format&fit=crop&q=80', 4.9, 1250);
INSERT INTO public.users VALUES (1, 'Shankar', 'sankar@example.com', '$2b$12$GMfJi.HmUZjiTxjyLVEtXuAcr.nkTveHN6HfTQlecctGiBjqizOXu', '+919876543210', 'customer', '2026-10-26 19:00:55.798014+00');
INSERT INTO public.users VALUES (2, 'CloudMart Seller', 'seller@example.com', '$2b$12$ZbIZGViyuXhK/qaUxlWpAe2nNfO.8yjyPyXL1rhBRUbQRggwbhQ.C', '+919876543210', 'seller', '2026-10-26 19:04:16.687714+00');
