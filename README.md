# Flask + Jinja2 Web Application (Adyen Drop-in Demo)

A web app with a **Flask** backend (API server) and **Jinja2** server-side rendering. Includes an **Adyen Drop-in** checkout using the **Advanced flow** (paymentMethods → payments → payments/details) with support for redirect payment methods and both native and redirect 3DS.

## Structure

- **`app/`** — Application package
  - **`routes/`** — Blueprints: `api.py` (JSON API + Adyen endpoints), `pages.py` (HTML pages + checkout)
  - **`templates/`** — Jinja2 templates (including `checkout.html`, success/failed, return)
  - **`static/`** — CSS and other static assets
- **`run.py`** — Entry point to run the server

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Adyen configuration (required for checkout)

Create a `.env` file in the project root (or set environment variables):

```env
ADYEN_API_KEY=your_adyen_api_key
ADYEN_CLIENT_KEY=your_adyen_client_key
ADYEN_MERCHANT_ACCOUNT=your_merchant_account
ADYEN_ENVIRONMENT=test
```

- Get **API key** and **Client key** from [Adyen Customer Area](https://docs.adyen.com/user-management/how-to-get-the-api-key) → Developers → API credentials.
- **Merchant account**: your test merchant account name.
- In Customer Area, add your origin (e.g. `http://localhost:5000`) to **Allowed origins** for the Client Key.

## Run

```bash
python run.py
```

Then open:

- **Home:** [http://127.0.0.1:5000/](http://127.0.0.1:5000/)
- **Checkout (Adyen Drop-in):** [http://127.0.0.1:5000/checkout](http://127.0.0.1:5000/checkout)
- **API:** [http://127.0.0.1:5000/api/health](http://127.0.0.1:5000/api/health)

## Checkout flow

- **Checkout page** shows a cart of 2 items and the total; the Adyen Drop-in is initialized with that amount (Advanced flow).
- **Payment methods** are loaded via `POST /api/adyen/paymentMethods`; payment is submitted via `POST /api/adyen/payments`; 3DS or redirect details are sent to `POST /api/adyen/payments/details`.
- **Redirect flow** (e.g. iDEAL, 3DS redirect): after the shopper returns to `/checkout/return`, the page completes the payment with `payments/details` and redirects to success or failed.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check (JSON) |
| GET | `/api/items` | List sample items (JSON) |
| POST | `/api/adyen/paymentMethods` | Adyen: get payment methods (body: amount, currency, countryCode, optional browserInfo) |
| POST | `/api/adyen/payments` | Adyen: submit payment (Drop-in payload) |
| POST | `/api/adyen/payments/details` | Adyen: submit details (e.g. after 3DS) |

## Pages

| Path | Description |
|------|-------------|
| `/` | Home (Jinja2-rendered) |
| `/checkout` | Checkout: cart + Adyen Drop-in |
| `/checkout/return` | Return URL for redirect/3DS (completes payment client-side) |
| `/checkout/success` | Payment success |
| `/checkout/failed` | Payment failed |
| `/about` | About (Jinja2-rendered) |
