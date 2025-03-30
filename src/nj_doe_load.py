from sqlalchemy import create_engine
import polars as pl

import logging
import json
import os

from settings import nj_doe_data_dir

logging.getLogger()

MYSQL_USER = os.getenv("MYSQL_USER", "")
MYSQL_PWD = os.getenv("MYSQL_PWD", "")
MYSQL_HOST = os.getenv("MYSQL_HOST", "")
MYSQL_PORT = os.getenv("MYSQL_PORT", "")
MYSQL_DB_NAME = os.getenv("MYSQL_DB_NAME", "")
MYSQL_TABLE_NAME = os.getenv("MYSQL_TABLE_NAME", "")

mysql_uri = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PWD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB_NAME}"

try:
    mysql_engine = create_engine(mysql_uri)

    with open(f"{nj_doe_data_dir}/merged_data_schema.json", "r") as file:
        schema: dict = json.load(file)
    schema_dict = {a:getattr(pl,b) for a,b in schema.items()}

    df = pl.read_csv(f"{nj_doe_data_dir}/merged_data_export.csv", infer_schema_length=0, schema=schema_dict)
    logging.info("------- writing data to MySQL database -------")
    
    nrows = df.write_database(MYSQL_TABLE_NAME, connection=mysql_engine, if_table_exists='replace')
    assert nrows == df.shape[0], f"Only {nrows}/{df.shape[0]} rows are inserted"
    
    logging.info(f"{nrows} rows inserted into {MYSQL_DB_NAME}.{MYSQL_TABLE_NAME} table")
except Exception as e:
    logging.error(e)
    raise(e)

