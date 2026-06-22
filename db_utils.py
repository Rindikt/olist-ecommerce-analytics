import os
import pandas as pd
from sqlalchemy import create_engine

_engine = None

def get_engine():
    global _engine
    if _engine is not None:
        return _engine

    if os.getenv('POSTGRES_USER'):
        _engine = create_engine(f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@localhost:5435/{os.getenv('POSTGRES_DB')}")
    else:
        _engine = create_engine('sqlite:///:memory:')
        pd.read_csv('data_raw/olist_orders_dataset.csv').to_sql('orders', _engine, index=False)
        pd.read_csv('data_raw/olist_order_items_dataset.csv').to_sql('order_items', _engine, index=False)
        pd.read_csv('data_raw/olist_customers_dataset.csv').to_sql('customers', _engine, index=False)

    return _engine