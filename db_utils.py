import os
import pandas as pd
from sqlalchemy import create_engine
import sqlite3

def get_engine():
    if os.getenv('POSTGRES_USER'):
        return create_engine(f"postgresql://...")
    else:
        engine = create_engine('sqlite:///:memory:')
        pd.read_csv('data_raw/olist_orders_dataset.csv').to_sql('orders', engine, index=False)
        pd.read_csv('data_raw/olist_order_items_dataset.csv').to_sql('order_items', engine, index=False)
        pd.read_csv('data_raw/olist_customers_dataset.csv').to_sql('customers', engine, index=False)
        return engine