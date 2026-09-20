import requests
import xml.etree.ElementTree as ET
import pandas as pd

API_KEY = "579b464db66ec23bdd00000159647412d4f5498a7be337075af22cda"

def get_mandi_prices(state, commodity):
    """Fetches live crop prices from api.data.gov.in"""
    url = "https://api.data.gov.in/resource/35985678-0d79-46b4-9ed6-6f13308a1d24"

    params = {
        "api-key": API_KEY,
        "format": "xml",
        "filters[State]": state,
        "filters[Commodity]": commodity,
        "sort[Arrival_Date]": "desc",
        "limit": 10
    }

    headers = {
        "accept": "application/xml",
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()

        root = ET.fromstring(response.text)
        records = []

        for item in root.findall(".//records/item"):
            row = {}
            for child in item:
                row[child.tag] = child.text
            records.append(row)

        df = pd.DataFrame(records)
        return df

    except Exception as e:
        print(f"Error fetching mandi data: {e}")
        return pd.DataFrame()
