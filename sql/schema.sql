CREATE TABLE IF NOT EXISTS customers (
        customer_id VARCHAR(50) PRIMARY KEY,
        customer_unique_id VARCHAR(50),
        customer_zip_code_prefix INT,
        customer_city VARCHAR(100),
        customer_state VARCHAR(10)
    );

    CREATE TABLE IF NOT EXISTS orders (
        order_id VARCHAR(50) PRIMARY KEY,
        customer_id VARCHAR(50) REFERENCES customers(customer_id),
        order_status VARCHAR(20),
        order_purchase_timestamp TIMESTAMP,
        order_approved_at TIMESTAMP,
        order_delivered_carrier_date TIMESTAMP,
        order_delivered_customer_date TIMESTAMP,
        order_estimated_delivery_date TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS order_items (
        order_id VARCHAR(50) REFERENCES orders(order_id),
        order_item_id INT,
        product_id VARCHAR(50),
        price DECIMAL(10,2),
        freight_value DECIMAL(10,2)
    );