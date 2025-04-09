from sqlalchemy import create_engine
import polars as pl

import logging
import json
import os

from settings import nj_doe_data_dir

logging.getLogger()

def merge_export_data(yearly_lfs: list[pl.LazyFrame], fname: str, dedup: bool = False):
    lf = pl.concat(yearly_lfs)
    
    if dedup:
        logging.info(f"------- de-duplicating {fname} table -------")
        lf = lf.unique(subset="county_district_school_code")
    
    final_schema = lf.collect_schema()
    
    final_schema = {a:b.__repr__() for a,b in final_schema.items()}
    with open(f"{nj_doe_data_dir}/{fname}_schema.json", 'w') as file:
        json.dump(final_schema, file, indent=4)
    logging.info(f"------- exported merged data schema to '{nj_doe_data_dir}/{fname}_schema.json' -------")
    
    lf.collect().write_csv(f"{nj_doe_data_dir}/{fname}.csv")
    logging.info(f"------- all academic years data is exported to '{nj_doe_data_dir}/{fname}.csv' -------")
    return lf

def load_mysql_db(lf: pl.LazyFrame, table_name: str):
    MYSQL_USER = os.getenv("MYSQL_USER", "")
    MYSQL_PWD = os.getenv("MYSQL_PWD", "")
    MYSQL_HOST = os.getenv("MYSQL_HOST", "")
    MYSQL_PORT = os.getenv("MYSQL_PORT", "")
    MYSQL_DB_NAME = os.getenv("MYSQL_DB_NAME", "")
    
    mysql_uri = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PWD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB_NAME}"

    try:
        mysql_engine = create_engine(mysql_uri)

        df = lf.collect()
        logging.info("------- writing data to MySQL database -------")
        
        nrows = df.write_database(table_name, connection=mysql_engine, if_table_exists='replace')
        assert nrows == df.shape[0], f"only {nrows}/{df.shape[0]} rows are inserted"
        
        logging.info(f"{nrows} rows inserted into {MYSQL_DB_NAME}.{table_name} table")
    except Exception as e:
        logging.error(e)
        raise(e)
