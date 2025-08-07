import os
import requests
import json
import argparse
import logging
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

MOUSER_API_URL = "https://api.mouser.com/api/v1/search/keyword"

def get_mouser_data(api_key: str, part_number: str) -> dict | None:
    """
    เรียกใช้ Mouser API เพื่อค้นหาข้อมูลของ Part Number ที่กำหนด
    และคืนค่าเป็น Raw JSON ที่ได้รับกลับมา
    """
    if not api_key:
        logging.error("Mouser API key is not set. Please set the MOUSER_API_KEY environment variable.")
        return None

    # Create a URL and Body for sending the Request.
    endpoint = f"{MOUSER_API_URL}?apiKey={api_key}"
    headers = {'Content-Type': 'application/json'}
    body = {
        "SearchByKeywordRequest": {
            "keyword": part_number,
            "records": 1,  # Fetch 1 data item
            "startingRecord": 0
        }
    }

    logging.info(f"Calling Mouser Keyword API for '{part_number}'...")

    try:
        # Send POST request to API
        response = requests.post(endpoint, headers=headers, json=body)
        response.raise_for_status()  # If there is an Error (e.g. 4xx, 5xx), an Exception will be thrown.
        
        results = response.json()
        
        # Check if the data is returned.
        if results.get("Errors"):
            logging.error(f"API returned errors: {results['Errors']}")
            return None
            
        return results

    except requests.exceptions.RequestException as e:
        logging.error(f"Mouser API call failed: {e}")
        return None

def main():
    """
    Main function for running scripts from the command line
    """
    # Set arguments to receive from the command line
    parser = argparse.ArgumentParser(description="Fetch raw component data from the Mouser API.")
    parser.add_argument(
        "-p", "--part-number",
        required=True,
        help="The manufacturer part number to search for."
    )
    args = parser.parse_args()

    # Read API Key from Environment Variable
    mouser_api_key = os.getenv("MOUSER_API_KEY")

    # Call a function to retrieve data.
    raw_data = get_mouser_data(mouser_api_key, args.part_number)

    if raw_data:
        logging.info("Successfully received data from Mouser. Raw response:")
        # Print all results out beautifully (Pretty Print)
        print(json.dumps(raw_data, indent=4))
    else:
        logging.warning("Could not retrieve any data from Mouser.")


if __name__ == "__main__":
    main()