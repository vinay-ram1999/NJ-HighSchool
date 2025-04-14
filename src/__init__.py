from dotenv import load_dotenv

import logging
import sys

logging.basicConfig(filename=f"{__name__}.log", level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

load_dotenv()
logging.info("------- loaded '.env' variables -------")
