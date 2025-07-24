import logging
import os

def setup_logging(app_log_path, fyers_data_log_path, fyers_req_log_path):
    """
    Sets up logging for the application.
    """
    # Create logs directory if it doesn't exist
    os.makedirs(os.path.dirname(app_log_path), exist_ok=True)

    # Main application logger
    logging.basicConfig(
        level=logging.INFO, # Default level
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(app_log_path),
            logging.StreamHandler() # Output to console as well
        ]
    )
    
    # Configure Fyers data socket logger
    fyers_data_logger = logging.getLogger("FyersWebsocket")
    fyers_data_logger.setLevel(logging.INFO)
    fyers_data_handler = logging.FileHandler(fyers_data_log_path)
    fyers_data_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    fyers_data_logger.addHandler(fyers_data_handler)
    fyers_data_logger.propagate = False # Prevent messages from going to root logger

    # Configure Fyers requests logger (for FyersAPI calls)
    fyers_req_logger = logging.getLogger("FyersAPI")
    fyers_req_logger.setLevel(logging.INFO)
    fyers_req_handler = logging.FileHandler(fyers_req_log_path)
    fyers_req_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    fyers_req_logger.addHandler(fyers_req_handler)
    fyers_req_logger.propagate = False # Prevent messages from going to root logger

    logging.info("Logging setup complete.")