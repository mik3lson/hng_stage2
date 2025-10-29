from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import httpx
import random
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from db import SessionLocal, Country, get_db
from sqlalchemy import func, desc
import matplotlib.pyplot as plt
from fastapi.responses import FileResponse, JSONResponse
import os
from pathlib import Path

app = FastAPI()


class CountryRequest(BaseModel):
    Country: str


def generate_summary_image():
    """Generate a summary image of total countries and top 5 GDPs."""
    db = SessionLocal()
    total_countries = db.query(func.count(Country.id)).scalar()
    top_countries = (
        db.query(Country.name, Country.estimated_gdp)
        .order_by(desc(Country.estimated_gdp))
        .limit(5)
        .all()
    )
    last_refreshed = db.query(func.max(Country.last_refreshed_at)).scalar()
    db.close()

    # Prepare data for plotting
    names = [c[0] for c in top_countries]
    gdps = [c[1] for c in top_countries]

    # Create figure
    plt.figure(figsize=(8, 5))
    plt.barh(names, gdps, color="skyblue")
    plt.gca().invert_yaxis()
    plt.title("Top 5 Countries by Estimated GDP")
    plt.xlabel("Estimated GDP")
    plt.tight_layout()

    # Add annotation
    plt.figtext(0.02, 0.02,
        f"Total Countries: {total_countries}\nLast Refreshed: {last_refreshed.isoformat() if last_refreshed else 'N/A'}",
        fontsize=8,
        ha="left"
    )

    # Ensure cache directory exists
    os.makedirs("cache", exist_ok=True)
    filepath = os.path.join("cache", "summary.png")
    plt.savefig(filepath)
    plt.close()

@app.get("/")
async def read_root():
    return {"Hello": "Welcome to my country currency & exchange api"}

@app.post("/countries/refresh", status_code=201)
async def refresh(request: CountryRequest):
    country_url = "https://restcountries.com/v2/all?fields=name,capital,region,population,flag,currencies"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(country_url)
            response.raise_for_status()
            countries = response.json()
    except httpx.RequestError as exc:
        raise HTTPException(status_code=503, detail=f"Could not fetch data from {exc.request.url!r}.") from exc
    
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail=f"Request to Rest Countries timed out.") from exc
    
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=f"Error response {exc.response.status_code} while requesting {exc.request.url!r}.") from exc


    #check if the country is present in the api response
    match = next(
        (c for c in countries if c["name"].lower() == request.Country.lower()), 
        None
    )

    if not match:
        raise HTTPException(status_code=404, detail=f"Country not found")
    

    population = match['population']
    currencies = match.get("currencies", [])
    currency_code = currencies[0]["code"] if currencies else None

    exchange_url = "https://open.er-api.com/v6/latest/USD"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(exchange_url)
            response.raise_for_status()
            exchange_data = response.json().get("rates")

            exchange_match = exchange_data.get(currency_code) if exchange_data else None
    except httpx.RequestError as exc:
        raise HTTPException(status_code=500, detail=f"Could not fetch data from  {exc.request.url!r}.") from exc
    
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail=f"Request to exchange api timed out.") from exc
    
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=f"Error response {exc.response.status_code} while requesting {exc.request.url!r}.") from exc
    if not exchange_match:
        raise HTTPException(status_code=404, detail=f"Exchange rate for currency '{currency_code}' not found")
    if not currency_code:
        currency_code = "null"
        exchange_match = None
        estimated_gdp = 0

    else:
        estimated_gdp = population * random.uniform(1000, 2000) / exchange_match

    name = match["name"]
    capital = match["capital"]
    region = match["region"]
    population = match["population"]
    currency_code = currency_code
    exchange_rate = exchange_match
    flag = match["flag"]
    estimated_gdp = estimated_gdp
    timestamp = datetime.utcnow()
    

    db: Session = SessionLocal()
    try:
        # try to find existing row by name
        existing = db.query(Country).filter(Country.name == name).first()

        if existing:
            # update fields
            existing.capital = capital
            existing.region = region
            existing.population = population
            existing.currency_code = currency_code
            existing.exchange_rate = exchange_rate
            existing.flag = flag
            existing.estimated_gdp = estimated_gdp
            existing.last_refreshed_at = timestamp
            db.add(existing)
            updated = True
        else:
            # create new record
            new_country = Country(
                name=name,
                capital=capital,
                region=region,
                population=population,
                currency_code=currency_code,
                exchange_rate=exchange_rate,
                flag=flag,
                estimated_gdp=estimated_gdp,
                last_refreshed_at= timestamp
            )
            db.add(new_country)
            updated = False

        db.commit()
        generate_summary_image()

    
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database integrity error")
    finally:
        db.close()


    #return saved record summary
    return {
        "message": "cached",
        "name": name,
        "currency_code": currency_code,
        "updated": updated,
        "last_refreshed_at": timestamp.isoformat()
    }


'''
    return {
        "id" : 1,
        "name": match["name"],
        "capital": match["capital"],
        "region": match["region"],
        "population": population,
        "currencies": currency_code,
        "exchange_rate": exchange_match,
        "flag": match["flag"],
        "extimated_gdp": estimated_gdp,
        "last_refreshed_at": timestamp       

    }
'''
@app.get("/countries", status_code=200)
def get_all_countries(
        region: str |None = Query(None),
        currency: str |None = Query(None), 
        sort: float|None = Query(None)
       ):
    try:
        db = SessionLocal()
        query = db.query(Country)

        # --- Filtering ---
        if region:
            query = query.filter(Country.region.ilike(region))
        if currency:
            query = query.filter(Country.currency_code.ilike(currency))

        # --- Sorting ---
        if sort:
            if sort.lower() == "gdp_desc":
                query = query.order_by(Country.estimated_gdp.desc())
            elif sort.lower() == "gdp_asc":
                query = query.order_by(Country.estimated_gdp.asc())

        countries = query.all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
    finally:
        db.close()

    if not countries:
        raise HTTPException(status_code=404, detail="No countries found for given filters")

    return [
        {
            "id": c.id,
            "name": c.name,
            "capital": c.capital,
            "region": c.region,
            "population": c.population,
            "currency_code": c.currency_code,
            "exchange_rate": c.exchange_rate,
            "estimated_gdp": c.estimated_gdp,
            "flag_url": c.flag,
            "last_refreshed_at": c.last_refreshed_at,
        }
        for c in countries
    ]



@app.get("/countries/{name}", status_code=200)
def get_country(name: str):
    try:
        db = SessionLocal()
        # Case-insensitive match
        country = db.query(Country).filter(Country.name.ilike(name)).first()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
    finally:
        db.close()

    if not country:
        raise HTTPException(status_code=404, detail=f"Country '{name}' not found in cache")

    return {
        "id": country.id,
        "name": country.name,
        "capital": country.capital,
        "region": country.region,
        "population": country.population,
        "currency_code": country.currency_code,
        "exchange_rate": country.exchange_rate,
        "flag": country.flag,
        "estimated_gdp": country.estimated_gdp,
        "last_refreshed_at": country.last_refreshed_at,
    }



@app.delete("/countries/{name}")
def delete_country(name: str):
    try:
        db = SessionLocal()
        country = db.query(Country).filter(Country.name == name).first()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


    if not country:
        raise HTTPException(status_code=404, detail="Country not found")

    db.delete(country)
    db.commit()
    db.close()

    return {"message": f"{name} has been deleted successfully"}



@app.get("/status")
def get_status():
    db = next(get_db())  

    total_countries = db.query(func.count(Country.id)).scalar()
    last_refreshed = db.query(func.max(Country.last_refreshed_at)).scalar()

    db.close()

    return {
        "total_countries": total_countries,
        "last_refreshed_at": last_refreshed.isoformat() if last_refreshed else None
    }


@app.get("/countries/image")
def get_country_image():
    # Use absolute path to avoid relative path confusion
    image_path = Path(__file__).parent / "cache" / "summary.png"

    print(f"Looking for image at: {image_path.resolve()}")  # Debug print

    if not image_path.exists():
        print("❌ Image not found.")
        return JSONResponse({"error": "Summary image not found"}, status_code=404)
    
    print("✅ Image found. Returning file...")
    return FileResponse(str(image_path), media_type="image/png")
