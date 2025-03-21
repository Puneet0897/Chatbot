
import logging
from logging.handlers import RotatingFileHandler
LOG_LEVEL = 20
LOG_PATH = "smartcapture_chatgpt.log"

logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)
#handler = logging.FileHandler(filename=LOG_PATH, mode='w', encoding='utf-8')
handler = RotatingFileHandler(LOG_PATH,  mode='w',maxBytes=20*1024*1024, backupCount=5, encoding="utf-8", delay=0)
handler.setLevel(LOG_LEVEL)
formatter = logging.Formatter('%(asctime)s : %(filename)s : %(lineno)d : %(levelname)s : %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)