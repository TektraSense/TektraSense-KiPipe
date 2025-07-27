"""
API Client for external component suppliers.

This module contains functions dedicated to calling the Digi-Key and
Mouser APIs and returning the raw JSON response.
"""
import os
import requests
import logging
from typing import Optional, Dict, Any
import config  # Import the entire config module

log = logging.getLogger(__name__)

def call_digikey_api(part_number: str) -> Optional[Dict[str, Any]]:
    client_id = os.getenv("DIGIKEY_CLIENT_ID")
    client_secret = os.getenv("DIGIKEY_CLIENT_SECRET")
    if not all([client_id, client_secret]):
        log.error("Digi-Key API credentials are not set.")
        return None
    try:
        auth_resp = requests.post(config.DIGIKEY_TOKEN_URL, data={"client_id": client_id, "client_secret": client_secret, "grant_type": "client_credentials"})
        auth_resp.raise_for_status()
        access_token = auth_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}", "X-DIGIKEY-Client-Id": client_id, "Content-Type": "application/json", "X-DIGIKEY-Locale-Site": "US", "X-DIGIKEY-Locale-Language": "en"}
        search_body = {"Keywords": part_number, "RecordCount": 1}
        log.info(f"Calling Digi-Key KeywordSearch API for '{part_number}'...")
        search_resp = requests.post(config.DIGIKEY_SEARCH_URL, headers=headers, json=search_body)
        if search_resp.status_code == 404: return None
        search_resp.raise_for_status()
        results = search_resp.json()
        return results.get('Products')[0] if results.get('Products') else None
    except (requests.exceptions.RequestException, KeyError, IndexError) as e:
        log.error(f"Digi-Key API call failed: {e}")
        return None

def call_mouser_api(part_number: str) -> Optional[Dict[str, Any]]:
    api_key = os.getenv("MOUSER_API_KEY")
    if not api_key:
        log.error("Mouser API key is not set.")
        return None
    endpoint = f"{config.MOUSER_API_URL}?apiKey={api_key}"
    headers = {'Content-Type': 'application/json'}
    body = {"SearchByKeywordRequest": {"keyword": part_number, "records": 1}}
    try:
        log.info(f"Calling Mouser Keyword API for '{part_number}'...")
        response = requests.post(endpoint, headers=headers, json=body)
        response.raise_for_status()
        results = response.json()
        parts = results.get('SearchResults', {}).get('Parts', [])
        if not parts: return None
        part = parts[0]
        if part.get("ManufacturerPartNumber", "").upper() == part_number.upper():
            return part
        return None
    except (requests.exceptions.RequestException, KeyError, IndexError) as e:
        log.error(f"Mouser API call failed: {e}")
        return None