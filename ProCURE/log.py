import logging
from datetime import datetime
  
def setup_logging_all():  
    logger = logging.getLogger('COUNTER_FACTUAL_LOGGER')  
    if not logger.hasHandlers():  
        logger.setLevel(logging.DEBUG)  
          
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_filename = f'fuzzing_{timestamp}.log'
        file_handler = logging.FileHandler(log_filename)
        
        file_handler.setLevel(logging.DEBUG)  
        file_handler.setFormatter(formatter)  
        logger.addHandler(file_handler)   
         
        console_handler = logging.StreamHandler()  
        console_handler.setLevel(logging.DEBUG)  
        console_handler.setFormatter(formatter)  
        logger.addHandler(console_handler) 

def setup_logging_console():  
    logger = logging.getLogger('COUNTER_FACTUAL_LOGGER')  
    if not logger.hasHandlers():  
        logger.setLevel(logging.DEBUG)  
          
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
         
        console_handler = logging.StreamHandler()  
        console_handler.setLevel(logging.DEBUG)  
        console_handler.setFormatter(formatter)  
        logger.addHandler(console_handler) 


def setup_logging_file():  
    logger = logging.getLogger('COUNTER_FACTUAL_LOGGER')  
    if not logger.hasHandlers():  
        logger.setLevel(logging.DEBUG)
          
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_filename = f'fuzzing_{timestamp}.log'
        file_handler = logging.FileHandler(log_filename)

        file_handler.setLevel(logging.DEBUG)  
        file_handler.setFormatter(formatter)  
        logger.addHandler(file_handler)   
        
          

# setup_logging_all()
# setup_logging_console()
setup_logging_file()

logger = logging.getLogger('COUNTER_FACTUAL_LOGGER')