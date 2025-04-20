from rapidfuzz import process, fuzz
import pandas as pd

from settings import nj_doe_data_dir, gs_data_dir
from collections import defaultdict
import logging
import os

NAME_THRESHOLD = 60
ADDRESS_THRESHOLD = 60

schools_dict = defaultdict(list)

nj_doe_schools_dim = pd.read_csv(f"{nj_doe_data_dir}/dim_schools.csv", dtype=str)
logging.info(f"----- nj_doe_schools_dim shape: {nj_doe_schools_dim.shape} -----")

nj_doe_schools_dim["school_address"] = nj_doe_schools_dim[["street_address", "city", "state", "zipcode"]].astype(str).agg(lambda row: ', '.join(row), axis=1)
nj_doe_schools_dim["name_enc"] = nj_doe_schools_dim["school_name"].str.upper().replace(r'[ ,.-]', '', regex=True)
nj_doe_schools_dim["address_enc"] = nj_doe_schools_dim["school_address"].str.upper().replace(r'[ ,.-]', '', regex=True)
nj_doe_schools_dim.drop(["street_address", "city", "state", "zipcode", "zipcode_extn"], axis=1, inplace=True)

gs_schools = pd.read_csv(f"{gs_data_dir}/gs_school_ratings.csv", dtype=str)
logging.info(f"----- gs_schools shape: {gs_schools.shape} -----")

gs_schools.dropna(subset=["rating"], inplace=True)
logging.info(f"----- filtered gs_schools shape: {gs_schools.shape} -----")

gs_schools["gs_name_enc"] = gs_schools["gs_school_name"].str.upper().replace(r'[ ,.-]', '', regex=True)
gs_schools["gs_address_enc"] = gs_schools["gs_school_address"].str.upper().replace(r'[ ,.-]', '', regex=True)

gs_name_enc = gs_schools["gs_name_enc"].tolist()
gs_address_enc = gs_schools["gs_address_enc"].tolist()

logging.info(f"----- NAME_THRESHOLD = {NAME_THRESHOLD}; ADDRESS_THRESHOLD = {ADDRESS_THRESHOLD} -----")

matched_rows = []

for _, row in nj_doe_schools_dim.iterrows():
    name_enc = row["name_enc"]
    address_enc = row["address_enc"]

    name_match = process.extractOne(name_enc, gs_name_enc, scorer=fuzz.token_ratio, score_cutoff=NAME_THRESHOLD)
    address_match = process.extractOne(address_enc, gs_address_enc, scorer=fuzz.token_ratio, score_cutoff=ADDRESS_THRESHOLD)

    if name_match and address_match:
        _, name_score, name_idx = name_match
        _, address_score, address_idx = address_match
        if name_idx == address_idx:
            matched_gs_row = gs_schools.iloc[name_idx]
            merged_row = {**row.to_dict(), **matched_gs_row.to_dict()}
            merged_row["fuzzy_name_score"] = name_score
            merged_row["fuzzy_address_score"] = address_score
            matched_rows.append(merged_row)

common_schools = pd.DataFrame(matched_rows)

common_schools.sort_values(["fuzzy_name_score", "fuzzy_address_score"], ascending=False, inplace=True)
logging.info(f"----- fuzzy merged data shape: {common_schools.shape} -----")

dups_fname = f"{gs_data_dir}/fuzzy_dups.csv"
if os.path.exists(dups_fname):
    os.remove(dups_fname)
dups = common_schools[common_schools.duplicated(subset=["gs_school_link"], keep=False)]
dups = dups[["county_district_school_code", "school_name", "gs_school_name", "school_address", "gs_school_address", "gs_school_link", "fuzzy_name_score", "fuzzy_address_score"]]
dups.sort_values(["gs_school_link", "fuzzy_name_score", "fuzzy_address_score"], ascending=False, inplace=True)

if dups.shape[0] > 0:
    logging.info(f"----- duplicates (inclusive): {dups.shape[0]} -----")
    dups.to_csv(dups_fname, index=False)
    logging.info(f"----- duplicates are exported to '{dups_fname}' -----")

# common_schools.drop_duplicates(subset=["gs_school_link"], inplace=True, keep='first')
logging.info(f"----- duplicates are not dropped (manual check required) -----")

common_schools.to_csv(f"{gs_data_dir}/fuzzy_merged_schools.csv", index=False)
logging.info(f"----- fuzzy merged data exported to '{gs_data_dir}/fuzzy_merged_schools.csv' -----")
