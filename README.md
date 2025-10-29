# 🌍 Country Currency & Exchange API

A simple RESTful API that fetches global country data and currency exchange rates, caches them in a MySQL database, and exposes endpoints for querying, filtering, and visualizing data — including an auto-generated summary image.
---

## 🚀 Features

✅ Fetch country data from RESTCountries API
✅ Fetch exchange rates from Open Exchange Rate API (base: USD)
✅ Compute estimated_gdp = population × random(1000–2000) ÷ exchange_rate
✅ Cache data in MySQL (update only on refresh)
✅ CRUD operations on country records
✅ Filtering & sorting by region, currency, and GDP
✅ Summary image generation of top 5 countries by GDP
✅ Error-handled async API calls with FastAPI and httpx

---
## 🧰 Tech Stack

FastAPI — API framework

MySQL — Database

SQLAlchemy / PyMySQL — ORM and DB connector

httpx — Async HTTP client

Pillow (PIL) — Image generation

python-dotenv — Environment variable management

cryptography — MySQL authentication support

--

##🧩 Example Folder Structure
```
├── app.py
├── db.py
├── cache/
│   └── summary.png
├── requirements.txt
├── .env
└── README.md
```

## 📦 Installation & Setup
### 1️⃣ Clone the repository
```bash 
 git clone https://github.com/mik3lson/hng_stage2.git
cd hng_stage2
```
---
### 2️⃣ Create a virtual environment
```bash
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
.venv\Scripts\activate      # Windows
```

### 3️⃣ Install dependencies
```bash
pip install -r requirements.txt
```

### 4️⃣ Configure environment variables

Create a .env file in the project root:
--- 
```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=yourpassword
DB_NAME=country_db

Optional:

PORT=8000
```

### 5️⃣ Create the database

Log into MySQL and run:

CREATE DATABASE country_db;

in your terminal run
```bash
python run_create_tables.py
```


### ▶️ Running the App
uvicorn app:app --reload


### Then visit:
📍 http://127.0.0.1:8000/docs
 — interactive Swagger UI

##🌐 External APIs Used
Source	Endpoint	Description
REST Countries	https://restcountries.com/v2/all?fields=name,capital,region,population,flag,currencies	Country info
Exchange Rates	https://open.er-api.com/v6/latest/USD	Currency rates (base USD)
📘 API Endpoints
Method	Endpoint	Description
POST	/countries/refresh	Fetch all countries + exchange rates, store/update DB, and generate summary image
GET	/countries	Get all cached countries (supports filters and sorting)
GET	/countries/{name}	Get one country by name
DELETE	/countries/{name}	Delete one country record
GET	/status	Show total countries and last refresh timestamp
GET	/countries/image	Serve summary image (top 5 GDP countries)
🔍 Query Parameters
GET /countries
Parameter	Description	Example
region	Filter by region	/countries?region=Africa
currency	Filter by currency code	/countries?currency=NGN
sort	Sort by GDP ascending or descending	/countries?sort=gdp_desc
📤 Example Responses
✅ GET /countries?region=Africa

```json
[
  {
    "id": 1,
    "name": "Nigeria",
    "capital": "Abuja",
    "region": "Africa",
    "population": 206139589,
    "currency_code": "NGN",
    "exchange_rate": 1600.23,
    "estimated_gdp": 25767448125.2,
    "flag_url": "https://flagcdn.com/ng.svg",
    "last_refreshed_at": "2025-10-22T18:00:00Z"
  },
  {
    "id": 2,
    "name": "Ghana",
    "capital": "Accra",
    "region": "Africa",
    "population": 31072940,
    "currency_code": "GHS",
    "exchange_rate": 15.34,
    "estimated_gdp": 3029834520.6,
    "flag_url": "https://flagcdn.com/gh.svg",
    "last_refreshed_at": "2025-10-22T18:00:00Z"
  }
]
```

## ✅ GET /status

```json
{
  "total_countries": 250,
  "last_refreshed_at": "2025-10-22T18:00:00Z"
}
```

## ✅ GET /countries/image

Returns an image file (PNG) generated after the last refresh

If not found:

{ "error": "Summary image not found" }
---

⚙️ Business Logic Summary
Case	Behavior
Country has multiple currencies	Store only the first currency code
currencies array empty	Set currency_code=None, exchange_rate=None, estimated_gdp=0
Currency not found in exchange API	Set exchange_rate=None, estimated_gdp=0
Existing country	Update all fields and recalculate GDP
New country	Insert into DB
On refresh	Recalculate estimated_gdp using new random multiplier (1000–2000)
🧮 Computation Formula
estimated_gdp = population * random.uniform(1000, 2000) / exchange_rate

🖼️ Summary Image Generation

After each successful /countries/refresh,
the app generates an image (e.g. cache/summary.png) containing:

Total number of countries

Top 5 countries by estimated GDP

Timestamp of last refresh

Served at /countries/image.

⚠️ Error Handling
Status	Response Example	Meaning
400	{ "error": "Validation failed" }	Missing/invalid input
404	{ "error": "Country not found" }	Country name not in DB
503	{ "error": "External data source unavailable" }	API fetch failed
500	{ "error": "Internal server error" }	Unexpected backend issue
🧑‍💻 Developer Notes


