import logging
import sys

logging.basicConfig(filename=f"{__name__}.log", level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))