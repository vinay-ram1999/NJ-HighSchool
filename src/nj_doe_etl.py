import polars as pl

import os

from settings import nj_doe_data_dir

data_dir = {dir: f"{nj_doe_data_dir}/{dir}" for dir in os.listdir(nj_doe_data_dir) if os.path.isdir(f"{nj_doe_data_dir}/{dir}")}
data_dir = dict(sorted(data_dir.items()))

for key, value in data_dir.items():
    file_path = [f"{value}/{file}" for file in os.listdir(value) if file.split(".")[-1] == "xlsx"][0]
    frames = pl.read_excel(file_path)
    print(frames)

