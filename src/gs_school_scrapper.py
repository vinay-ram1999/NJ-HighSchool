from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium import webdriver
import pandas as pd

from settings import gs_data_dir
import logging
import time
import sys
import os

options = Options()
options.add_argument('--headless')
options.add_argument('--disable-gpu')
options.add_argument('--no-sandbox')

driver = webdriver.Chrome(options=options)

fname = f"{gs_data_dir}/gs_school_ratings.csv"
flag = True if os.path.exists(fname) else False

gs_schools = pd.read_csv(f"{gs_data_dir}/gs_school_ratings.csv", dtype=str)

rows = []

try:
    gs_school_ratings_old = pd.read_csv(fname) if flag else None
    
    for _, row in gs_schools.iterrows():
        start_idx = gs_school_ratings_old.shape[0] if flag else 0

        if _ >= start_idx:
            new_row = {**row.to_dict()}

            url = row["gs_school_link"]
            logging.info(f"----- fetching '{url}' -----")

            driver.get(url)
            time.sleep(2)

            summary = driver.find_elements(By.CSS_SELECTOR, ".summary-rating-container")

            if summary:
                children = summary[0].find_elements(By.XPATH, "./div")
                
                rating = children[0].text.split("\n/")
                new_row["rating"] = int(rating[0])
                logging.info(f"----- rating: {new_row['rating']} extracted -----")
            else:
                new_row["rating"] = None
                logging.info(f"----- summary rating not found -----")
            rows.append(new_row)
    
    driver.quit()
except Exception as e:
    logging.error(e)
    raise(e)
except KeyboardInterrupt:
    logging.info("exiting gracefully...")
finally:
    gs_school_ratings = pd.DataFrame(rows)
    if flag:
        gs_school_ratings = pd.concat([gs_school_ratings_old, gs_school_ratings], ignore_index=True)
    gs_school_ratings.to_csv(f"{gs_data_dir}/gs_school_ratings.csv", index=False)
    logging.info(f"----- ratings data exported to '{gs_data_dir}/gs_school_ratings.csv' -----")

