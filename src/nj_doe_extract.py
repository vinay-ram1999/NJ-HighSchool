from polars.datatypes import String, Float64
from polars import col
import polars as pl

import logging
import os

from settings import nj_doe_data_dir, nj_doe_dim_sheets, nj_doe_one_to_one_fact_sheets, nj_doe_one_to_many_fact_sheets, non_string_dtype_cols
from .utils import merge_export_data, load_mysql_db

logging.getLogger()

data_dir = {dir: f"{nj_doe_data_dir}/{dir}" for dir in os.listdir(nj_doe_data_dir) if os.path.isdir(f"{nj_doe_data_dir}/{dir}")}
data_dir = dict(sorted(data_dir.items()))

dim_yearly_lfs = []
one_to_one_yearly_lfs = []
one_to_many_yearly_lfs = []

try:
    for key, value in data_dir.items():
        logging.info(f"------- extracting {key}-{int(key)+1} academic year data -------")
        
        file_path = [f"{value}/{file}" for file in os.listdir(value) if file.split(".")[-1] == "xlsx"][0]

        for sheet, schema in nj_doe_dim_sheets.items():
            logging.info(f"------- extracting dim sheet '{sheet}' -------")

            assert len(schema["input"]) == len(schema["output"]), f"Miss match in number of columns in sheet '{sheet}' input/output schemas"
            schema_map = {i:o for i,o in zip(schema["input"], schema["output"])}
            
            lf = pl.read_excel(file_path, sheet_name=sheet, columns=schema["input"]).lazy()
            lf = lf.rename(schema_map)
            
            # bytesio = None
            lf_schema = lf.collect_schema()
            logging.info(f"current schema of '{sheet}': {lf_schema}")
            
            if "city_state_zip" in lf_schema.names():
                lf = lf.with_columns(col("city_state_zip").str.split(" NJ ")
                                                          .list.to_struct(n_field_strategy='max_width', fields=["city", "zip"])
                                                          .struct.unnest(),
                                    pl.lit("NJ").alias("state")).drop("city_state_zip")
                
                lf = lf.with_columns(col("zip").str.split("-")
                                               .list.to_struct(n_field_strategy='max_width', fields=["zipcode", "zipcode_extn"])
                                               .struct.unnest()).drop("zip")
            
            lf = lf.with_columns(pl.concat_str([col("county_code"), col("district_code"), col("school_code")], separator="-")
                                    .alias("county_district_school_code")
                                ).drop("county_code", "district_code", "school_code")
            
        dim_yearly_lfs += [lf]
        one_to_one_lfs: list[pl.LazyFrame] = []

        for sheet, schema in (nj_doe_one_to_one_fact_sheets | nj_doe_one_to_many_fact_sheets).items():
            logging.info(f"------- extracting fact sheet '{sheet}' -------")
            
            assert len(schema["input"]) == len(schema["output"]), f"Miss match in number of columns in sheet '{sheet}' input/output schemas"
            schema_map = {i:o for i,o in zip(schema["input"], schema["output"])}
            
            lf = pl.read_excel(file_path, sheet_name=sheet, columns=schema["input"]).lazy()
            lf = lf.rename(schema_map)
            
            # bytesio = None
            lf_schema = lf.collect_schema()
            logging.info(f"current schema of '{sheet}': {lf_schema}")
            
            for name, dtype in lf_schema.items():
                if name in non_string_dtype_cols:
                    if dtype == String:
                        logging.info(f"'{name}' in '{sheet}' is casted as a String; Performing the work around;")
                        
                        lf = lf.with_columns(pl.when(pl.col(name).is_null() | pl.col(name).str.contains(r"[^0-9.\-]"))
                                                .then(None).otherwise(pl.col(name)).alias(name))
                    lf = lf.cast({name: Float64})
            logging.info(f"updated schema of '{sheet}': {lf.collect_schema()}")
            
            lf = lf.with_columns(pl.concat_str([col("county_code"), col("district_code"), col("school_code")], separator="-")
                                    .alias("county_district_school_code")
                                ).drop("county_code", "district_code", "school_code")
            
            if sheet in nj_doe_one_to_many_fact_sheets:
                one_to_many_lf = lf.with_columns(pl.lit(f"{key}-{int(key)+1}").alias("academic_year"))
            else:
                one_to_one_lfs += [lf]
        
        one_to_many_yearly_lfs += [one_to_many_lf]
        logging.info("------- joining one-to-one fact sheets -------")
        
        merged_lf = one_to_one_lfs[0]
        
        for lf in one_to_one_lfs[1:]:
            merged_lf = merged_lf.join(lf, on="county_district_school_code")
        merged_lf = merged_lf.with_columns(pl.lit(f"{key}-{int(key)+1}").alias("academic_year"))
        one_to_one_yearly_lfs += [merged_lf]

    logging.info("------- merging all academic years data for dim table -------")
    name = "dim_schools"
    final_lf = merge_export_data(dim_yearly_lfs, name, dedup=True)
    load_mysql_db(final_lf, name)
    
    logging.info("------- merging all academic years data for one-to-one facts -------")
    name = "fct_enrollments"
    final_lf = merge_export_data(one_to_one_yearly_lfs, name)
    load_mysql_db(final_lf, name)

    logging.info("------- merging all academic years data for one-to-many facts -------")
    name = "fct_homelang_enrollments"
    final_lf = merge_export_data(one_to_many_yearly_lfs, name)
    load_mysql_db(final_lf, name)
except Exception as e:
    logging.error(e)
    raise(e)
