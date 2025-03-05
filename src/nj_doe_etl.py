from polars.datatypes import String, Float64
from polars import col
import polars as pl

import logging
import json
import os

from settings import nj_doe_data_dir, nj_doe_required_sheets, non_string_dtype_cols

logging.getLogger()

data_dir = {dir: f"{nj_doe_data_dir}/{dir}" for dir in os.listdir(nj_doe_data_dir) if os.path.isdir(f"{nj_doe_data_dir}/{dir}")}
data_dir = dict(sorted(data_dir.items()))

year_merged_lfs: list[pl.LazyFrame] = []

try:
    for key, value in data_dir.items():
        logging.info(f"------- extracting {key}-{int(key)+1} academic year data -------")
        year_lfs: list[pl.LazyFrame] = []
        file_path = [f"{value}/{file}" for file in os.listdir(value) if file.split(".")[-1] == "xlsx"][0]
        for sheet, schema in nj_doe_required_sheets.items():
            logging.info(f"------- extracting sheet '{sheet}' -------")
            assert len(schema["input"]) == len(schema["output"]), f"Miss match in number of columns in sheet '{sheet}' input/output schemas"
            schema_map = {i:o for i,o in zip(schema["input"], schema["output"])}
            lf = pl.read_excel(file_path, sheet_name=sheet, columns=schema["input"]).lazy()
            lf = lf.rename(schema_map)
            bytesio = None
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
            year_lfs += [lf]
        logging.info("------- joining the sheets -------")
        merged_lf = year_lfs[0]
        for lf in year_lfs[1:]:
            merged_lf = merged_lf.join(lf, on="county_district_school_code",)
        merged_lf = merged_lf.with_columns(pl.lit(f"{key}-{int(key)+1}").alias("academic_year"))
        year_merged_lfs += [merged_lf]

    logging.info("------- merging all academic years data -------")
    final_lf = pl.concat(year_merged_lfs)
    final_schema = final_lf.collect_schema()
    logging.info(f"merged data schema: {final_schema}")
    final_schema = {a:b.__name__ for a,b in final_schema.to_python().items()}
    with open(f"{nj_doe_data_dir}/merged_data_schema.json", 'w') as file:
        json.dump(final_schema, file, indent=4)
    logging.info(f"------- exported merged data schema to '{nj_doe_data_dir}/merged_data_schema.json' -------")
    final_lf.collect().write_csv(f"{nj_doe_data_dir}/merged_data_export.csv")
    logging.info(f"------- all academic years data is exported to '{nj_doe_data_dir}/merged_data_export.csv' -------")
except Exception as e:
    logging.error(e)
    raise(e)
