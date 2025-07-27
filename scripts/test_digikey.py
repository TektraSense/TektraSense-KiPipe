import requests
import json

# --- Configuration ---
# IMPORTANT: Replace these with your actual credentials
CLIENT_ID = "CY3TGfg1Em41YrDXDpwYtpk2k7bez5oByOSGvNqo7WY4m91B"
CLIENT_SECRET = "2HtLPznwLWewQWCdW5zyo6tNCnVVNaiXfMtCXU7vgXpN9myjlSKDI2HGbDKGXBRn"
# PART_NUMBER = "STM32U53\5NEY6QTR" # The part number you want to look up
PART_NUMBER = "LDK130PU-R"

# --- API Endpoints ---
BASE_URL = "https://api.digikey.com"
TOKEN_ENDPOINT = f"{BASE_URL}/v1/oauth2/token"
API_ENDPOINT = f"{BASE_URL}/products/v4/search/{PART_NUMBER}/productdetails"

def get_api_data():
    """
    Fetches all available data for a single part number from the Digi-Key API.
    """
    # --- Step 1: Get Access Token ---
    print("Requesting Access Token...")
    auth_body = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials"
    }
    try:
        token_response = requests.post(TOKEN_ENDPOINT, data=auth_body)
        token_response.raise_for_status()
        access_token = token_response.json().get("access_token")
        if not access_token:
            print("Failed to get access token.")
            print(token_response.json())
            return
        print("Successfully obtained access token.")
    except requests.exceptions.RequestException as e:
        print(f"Error getting access token: {e}")
        if e.response:
            print(f"--> Error Response: {e.response.text}")
        return

    # --- Step 2: Use Access Token to Get Product Data ---
    print(f"\nFetching data for part number: {PART_NUMBER}...")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-DIGIKEY-Client-Id": CLIENT_ID,
        "X-DIGIKEY-Locale-Site": "US",
        "X-DIGIKEY-Locale-Language": "en"
    }
    try:
        response = requests.get(API_ENDPOINT, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # --- Step 3: Print the Full Response ---
        print("\n--- Full API Response ---")
        # Use json.dumps for pretty printing the JSON data
        print(json.dumps(data, indent=2))
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching product data: {e}")
        if e.response:
            print(f"--> Error Response: {e.response.text}")
        return

if __name__ == "__main__":
    get_api_data()