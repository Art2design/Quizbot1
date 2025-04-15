import logging
from config import config

def setup_logger():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.ERROR,
        filename=config.log_file
    )
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    logger = logging.getLogger(__name__)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logger()
