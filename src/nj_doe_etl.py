import polars as pl
import pandas as pd

import logging
import os

from settings import nj_doe_data_dir

logging.getLogger()

data_dir = {dir: f"{nj_doe_data_dir}/{dir}" for dir in os.listdir(nj_doe_data_dir) if os.path.isdir(f"{nj_doe_data_dir}/{dir}")}
data_dir = dict(sorted(data_dir.items()))

for key, value in data_dir.items():
    year_sheet_cols = {'year':[], 'sheet':[], 'columns':[], 'n_columns':[]}
    file_path = [f"{value}/{file}" for file in os.listdir(value) if file.split(".")[-1] == "xlsx"][0]
    frames = pl.read_excel(file_path, sheet_id=0)
    for name, sheet in frames.items():
        if not "Important " in name:
            cols = sheet.columns
            year_sheet_cols['year'] += [f"{key}-{int(key)+1}"]
            year_sheet_cols['sheet'] += [name]
            year_sheet_cols['columns'] += [", ".join(sorted(cols))]
            year_sheet_cols['n_columns'] += [len(cols)]
    df = pd.DataFrame(year_sheet_cols)
    df.to_csv(f"{nj_doe_data_dir}/{key}-{int(key)+1}_metadata.csv")

