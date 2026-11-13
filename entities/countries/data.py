import asyncio
import os
from dotenv import load_dotenv
import json

import httpx

load_dotenv()

API_KEY = os.getenv("API_COUNTRIES_KEY")
API_URL = os.getenv("API_COUNTRIES_URL")


async def fetch_countries():
    countries = []
    offset, limit = 0, 100

    headers = {"Authorization": f"Bearer {API_KEY}"}

    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            response = await client.get(
                API_URL, params={"limit": limit, "offset": offset}, headers=headers
            )

            response.raise_for_status()
            payload = response.json()

            items = payload["data"]["objects"]

            for item in items:
                names = item.get("names", {})
                translations = names.get("translations", {})

                country_name = translations.get("ukr", {}).get("common") or names.get(
                    "common"
                )

                country = {
                    "name": country_name,
                    "code": item["codes"]["alpha_2"],
                    "flag": item.get("flag", {}).get("emoji"),
                }

                countries.append(country)

            if not payload["data"]["meta"]["more"]:
                break

            offset += limit

    return countries


async def main():
    countries = await fetch_countries()

    with open("entities/countries/countries_data.json", "w", encoding="utf-8") as file:
        file.write("countries = ")
        json.dump(countries, file, ensure_ascii=False, indent=4)

    print(f"Successfully fetched {len(countries)} countries")


if __name__ == "__main__":
    asyncio.run(main())
