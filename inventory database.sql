CREATE DATABASE IF NOT EXISTS inventory_db;
USE inventory_db;

-- Drop tables if exist (clean start)
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS inventory;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS suppliers;

-- TABLE 1: products
CREATE TABLE products (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    Productname VARCHAR(100) NOT NULL,
    HSNcode     VARCHAR(50)  UNIQUE,
    price       DECIMAL(10,2),
    category    VARCHAR(50)
);

-- TABLE 2: inventory
CREATE TABLE inventory (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    product_id  INT,
    quantity    INT DEFAULT 0,
    updated_at  DATETIME DEFAULT NOW(),
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

-- TABLE 3: suppliers
CREATE TABLE suppliers (
    id    INT AUTO_INCREMENT PRIMARY KEY,
    name  VARCHAR(100),
    email VARCHAR(100),
    phone VARCHAR(20)
);

-- TABLE 4: orders
CREATE TABLE orders (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT,
    quantity   INT,
    type       ENUM('IN','OUT'),
    created_at DATETIME DEFAULT NOW(),
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

-- ============================================================
-- SAMPLE DATA
-- ============================================================

INSERT INTO products (Productname, HSNcode, price, category) VALUES
('Masala',          'SKB0001', 50.00,  'Grocery'),
('Curd',            'SKB0002', 25.00,  'Grocery'),
('Rice 1kg',        'SKB0003', 80.00,  'Grocery'),
('USB Pen Drive',   'SKB0004', 450.00, 'Electronics'),
('Wireless Mouse',  'SKB0005', 599.00, 'Electronics'),
('A4 Paper Box',    'SKB0006', 250.00, 'Stationery'),
('Ball Pen',        'SKB0007', 10.00,  'Stationery'),
('Notebook',        'SKB0008', 80.00,  'Stationery');

INSERT INTO inventory (product_id, quantity) VALUES
(1, 100),
(2, 50),
(3, 30),
(4, 25),
(5, 8),
(6, 15),
(7, 3),
(8, 60);

INSERT INTO suppliers (name, email, phone) VALUES
('ABC Traders',    'abc@traders.com',   '9876543210'),
('XYZ Wholesale',  'xyz@wholesale.com', '9123456789'),
('Fast Suppliers', 'fast@supply.com',   '9000001111');

INSERT INTO orders (product_id, quantity, type) VALUES
(1, 100, 'IN'),
(2, 50,  'IN'),
(3, 30,  'IN'),
(4, 25,  'IN'),
(5, 10,  'IN'),
(5, 2,   'OUT'),
(7, 5,   'IN'),
(7, 2,   'OUT'),
(1, 20,  'OUT'),
(2, 10,  'OUT');