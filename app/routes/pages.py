"""Page routes — server-rendered with Jinja2."""
from flask import Blueprint, render_template, current_app

pages_bp = Blueprint("pages", __name__)

# Demo cart: 2 items with total for Adyen (amount in minor units)
CHECKOUT_ITEMS = [
    {"id": "1", "name": "Wireless Headphones", "price_cents": 5999, "quantity": 1},
    {"id": "2", "name": "USB-C Hub", "price_cents": 3499, "quantity": 1},
]
CHECKOUT_CURRENCY = "EUR"


def get_checkout_total_cents():
    return sum(item["price_cents"] * item["quantity"] for item in CHECKOUT_ITEMS)


@pages_bp.route("/")
def index():
    """Home page."""
    return render_template("index.html", title="Home")


@pages_bp.route("/about")
def about():
    """About page."""
    return render_template("about.html", title="About")


@pages_bp.route("/checkout")
def checkout():
    """Checkout page: cart (2 items) + Adyen Drop-in (advanced flow)."""
    total_cents = get_checkout_total_cents()
    client_key = current_app.config.get("ADYEN_CLIENT_KEY") or ""
    environment = current_app.config.get("ADYEN_ENVIRONMENT", "test")
    return render_template(
        "checkout.html",
        title="Checkout",
        items=CHECKOUT_ITEMS,
        total_cents=total_cents,
        currency=CHECKOUT_CURRENCY,
        client_key=client_key,
        environment=environment,
    )


@pages_bp.route("/checkout/return", methods=["GET", "POST"])
def checkout_return():
    """Render return page; client-side JS reads redirectResult/payload and paymentData (sessionStorage), calls payments/details, then redirects to success/failed."""
    return render_template("checkout_return.html", title="Completing payment")


@pages_bp.route("/checkout/success")
def checkout_success():
    """Payment success page."""
    return render_template("checkout_success.html", title="Payment successful")


@pages_bp.route("/checkout/failed")
def checkout_failed():
    """Payment failed or error page."""
    return render_template("checkout_failed.html", title="Payment failed")


@pages_bp.route("/api-logs")
def api_logs():
    """API Logs page: server-side Adyen API request/response logs."""
    return render_template("api_logs.html", title="API Logs")
