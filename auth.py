import os
import json
import logging
from fyers_apiv3.fyersModel import FyersModel, SessionModel  # Import both FyersModel and SessionModel
from config import FYERS_APP_ID, FYERS_SECRET_KEY, FYERS_REDIRECT_URI

# Set up logging for authentication
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("logs/fyersAuth.log"),
                        logging.StreamHandler()
                    ])

AUTH_CODE_FILE = "fyers_token.json"


def get_fyers_access_token(app_id, secret_key, redirect_uri):
    """
    Generates and returns the Fyers access token.
    If a valid token exists, it loads it. Otherwise, it initiates the login flow.
    """
    if os.path.exists(AUTH_CODE_FILE):
        try:
            with open(AUTH_CODE_FILE, 'r') as f:
                token_data = json.load(f)
                access_token = token_data.get("access_token")
                if access_token:
                    logging.info("Loaded Fyers access token from file.")
                    return access_token
        except json.JSONDecodeError:
            logging.warning(
                f"Error decoding {AUTH_CODE_FILE}. Will generate new token.")
        except Exception as e:
            logging.error(
                f"An unexpected error occurred while reading token file: {e}")

    logging.info(
        "Fyers access token not found or invalid. Initiating login flow...")

    # Step 1: Generate Authorization URL using SessionModel
    session = SessionModel(
        client_id=app_id,
        secret_key=secret_key,  # secret_key is required for SessionModel init
        redirect_uri=redirect_uri,
        response_type='code',
        grant_type=
        'authorization_code'  # Required for generating the token later
    )

    # This generate_authcode() method from SessionModel returns the URL
    auth_code_url = session.generate_authcode()

    logging.info(
        f"Please visit this URL to get your auth code: {auth_code_url}")

    auth_code = input(
        "After successful login and redirection, copy the 'auth_code' from the URL and paste it here: "
    )

    try:
        # Step 2: Generate Access Token using SessionModel (using the same session object)
        session.set_token(auth_code)  # Set the received auth code
        response = session.generate_token()  # Generate the access token

        if response.get("code") == 200:
            access_token = response["access_token"]
            with open(AUTH_CODE_FILE, 'w') as f:
                json.dump({"access_token": access_token}, f)
            logging.info(
                "Fyers access token generated and saved successfully.")
            return access_token
        else:
            logging.error(f"Failed to generate access token: {response}")
            return None
    except Exception as e:
        logging.error(f"Error during access token generation: {e}")
        return None


if __name__ == "__main__":
    # Ensure the logs directory exists
    if not os.path.exists("logs"):
        os.makedirs("logs")

    access_token = get_fyers_access_token(FYERS_APP_ID, FYERS_SECRET_KEY,
                                          FYERS_REDIRECT_URI)
    if access_token:
        logging.info(f"Fyers API Access Token: {access_token}")
    else:
        logging.error("Failed to retrieve Fyers API Access Token.")
