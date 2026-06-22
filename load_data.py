import pandas as pd
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

def get_engine():
    user = os.getenv('POSTGRES_USER')
    password = os.getenv('POSTGRES_PASSWORD')
    db_name = os.getenv('POSTGRES_DB')
    db_url = f'postgresql://{user}:{password}@localhost:5435/{db_name}'
    return create_engine(db_url)

def process_customers(df):
    df = df.drop_duplicates(subset=['customer_id'])
    return df

def process_orders(df):
    date_cols = ['order_purchase_timestamp', 'order_approved_at', 'order_delivered_customer_date']
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors='coerce')
    return df

if __name__ == '__main__':
    engine = get_engine()
    customers = pd.read_csv('data_raw/olist_customers_dataset.csv')
    orders = pd.read_csv('data_raw/olist_orders_dataset.csv')
    items = pd.read_csv('data_raw/olist_order_items_dataset.csv')

    customers_clean = process_customers(customers)
    orders_clean = process_orders(orders)

    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE order_items RESTART IDENTITY CASCADE;"))
        conn.execute(text("TRUNCATE TABLE orders RESTART IDENTITY CASCADE;"))
        conn.execute(text("TRUNCATE TABLE customers RESTART IDENTITY CASCADE;"))
        conn.commit()
        print("Таблицы очищены.")

    customers.to_sql('customers', engine, if_exists='append', index=False)
    orders.to_sql('orders', engine, if_exists='append', index=False)
    items.to_sql('order_items', engine, if_exists='append', index=False)
    print("Данные успешно залиты в базу!")



