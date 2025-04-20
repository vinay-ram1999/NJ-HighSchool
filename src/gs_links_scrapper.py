from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium import webdriver
import pandas as pd

from collections import defaultdict
from settings import gs_data_dir
import logging
import time

options = Options()
options.add_argument('--headless')
options.add_argument('--disable-gpu')
options.add_argument('--no-sandbox')

driver = webdriver.Chrome(options=options)

# base_url = lambda page: f"https://www.greatschools.org/best-schools/new-jersey/?gradeLevels%5B%5D=m&gradeLevels%5B%5D=h&gradeLevels%5B%5D=e&page={page}&view=table"
base_url = lambda page: f"https://www.greatschools.org/best-schools/new-jersey/?page={page}&view=table"

schools_dict = defaultdict(list)

try:
    page = 1
    logging.info(f"------- base url set to: '{base_url(page)}' -------")
    while True:
        url = base_url(page)
        logging.info(f"------- fetching page no: '{page}' -------")
        
        driver.get(url)
        time.sleep(2)

        schools = driver.find_elements(By.CSS_SELECTOR, "td.school")

        if schools:
            for school in schools:
                name_list = school.find_elements(By.CSS_SELECTOR, ".name")
                address_list = school.find_elements(By.CSS_SELECTOR, ".address")

                schools_dict["gs_school_name"] += [name_list[0].text] if name_list else [None]
                schools_dict["gs_school_address"] += [address_list[0].text] if address_list else [None]
                schools_dict["gs_school_link"] += [name_list[0].get_attribute("href")] if name_list else [None]
        else:
            logging.info("------- no more schools found -------")
            break
        # break
        page += 1
    
    gs_schools = pd.DataFrame(schools_dict)
    logging.info(f"------- extracted {gs_schools.shape[0]} schools data -------")

    gs_schools.to_csv(f"{gs_data_dir}/gs_school_links.csv", index=False)
    logging.info(f"------- data exported to '{gs_data_dir}/gs_school_links.csv' -------")

    driver.quit()
except Exception as e:
    logging.error(e)
    raise(e)
