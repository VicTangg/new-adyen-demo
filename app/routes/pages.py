"""Page routes — server-rendered with Jinja2."""
import hmac
import time
from collections import OrderedDict
from functools import lru_cache, wraps
from threading import RLock
from urllib.parse import urlparse

import requests
from flask import Blueprint, Response, abort, current_app, redirect, render_template, request, session, url_for

pages_bp = Blueprint("pages", __name__)

# Demo cart: 2 items with total for Adyen (amount in minor units)
CHECKOUT_ITEMS = [
    {"id": "1", "name": "Wireless Headphones", "price_cents": 5999, "quantity": 1, "image": "images/headphones.svg"},
    {"id": "2", "name": "USB-C Hub", "price_cents": 3499, "quantity": 1, "image": "images/hub.svg"},
]
CHECKOUT_CURRENCY = "EUR"
HANA_GALLERIES = (
    {
        "title": "Harry Potter",
        "api_url": "https://warnerbros.fandom.com/api.php",
        "page_title": "Harry_Potter_(character)/Gallery",
        "source_name": "Warner Bros. Entertainment Wiki",
        "source_url": "https://warnerbros.fandom.com/wiki/Harry_Potter_(character)/Gallery",
    },
    {
        "title": "HUNTR/X",
        "api_url": "https://kpop-demon-hunters.fandom.com/api.php",
        "page_title": "HUNTRIX/Gallery",
        "source_name": "KPop Demon Hunters Wiki",
        "source_url": "https://kpop-demon-hunters.fandom.com/wiki/HUNTRIX/Gallery",
    },
)
HANA_SESSION_KEY = "hana_authenticated"
HANA_IMAGE_WIDTH = 640
HANA_REQUEST_RETRIES = 2
HANA_REQUEST_TIMEOUT = (2, 5)
HANA_MAX_IMAGE_BYTES = 2 * 1024 * 1024
HANA_IMAGE_CACHE_SIZE = 24
HANA_IMAGE_CACHE_TTL = 60 * 60
HANA_IMAGE_CACHE = OrderedDict()
HANA_IMAGE_CACHE_LOCK = RLock()


def get_checkout_total_cents():
    return sum(item["price_cents"] * item["quantity"] for item in CHECKOUT_ITEMS)


def hana_access_required(view):
    """Require a valid Hana session before serving protected content."""
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get(HANA_SESSION_KEY):
            return redirect(url_for("pages.hana_login"))
        return view(*args, **kwargs)

    return wrapped_view


def fetch_hana_url(url, **kwargs):
    """Fetch a Fandom resource with brief retries for transient failures."""
    for attempt in range(HANA_REQUEST_RETRIES + 1):
        try:
            response = requests.get(url, timeout=HANA_REQUEST_TIMEOUT, **kwargs)
            if response.status_code not in {429, 500, 502, 503, 504}:
                response.raise_for_status()
                return response
            response.close()
        except requests.RequestException as error:
            if getattr(error, "response", None) is not None:
                error.response.close()

        if attempt < HANA_REQUEST_RETRIES:
            time.sleep(0.25 * (attempt + 1))

    return None


@lru_cache(maxsize=len(HANA_GALLERIES))
def get_hana_gallery_images(api_url, page_title, source_name, source_url):
    """Fetch a limited set of images from a public Fandom gallery."""
    try:
        response = fetch_hana_url(
            api_url,
            params={
                "action": "query",
                "format": "json",
                "generator": "images",
                "gimlimit": 24,
                "iiprop": "url|mime",
                "iiurlwidth": HANA_IMAGE_WIDTH,
                "prop": "imageinfo",
                "titles": page_title,
            },
            headers={"User-Agent": "hana-gallery/1.0"},
        )
        if response is None:
            return ()
        try:
            pages = response.json().get("query", {}).get("pages", {}).values()
        finally:
            response.close()
    except (requests.RequestException, ValueError):
        return ()

    images = []
    seen_urls = set()
    for page in pages:
        image_info = page.get("imageinfo", ())
        if not image_info:
            continue
        image = image_info[0]
        url = image.get("thumburl") or image.get("url", "")
        if not url.startswith("https://") or url in seen_urls:
            continue
        if not image.get("mime", "").startswith("image/"):
            continue
        seen_urls.add(url)
        image_title = page.get("title", "gallery image")
        if image_title.startswith("File:"):
            image_title = image_title[5:]
        images.append(
            {
                "alt": f"{source_name}: {image_title}",
                "source_name": source_name,
                "source_url": source_url,
                "url": url,
            }
        )

    return tuple(images[:12])


def get_hana_image_data(gallery_index, image_index):
    """Fetch a curated gallery image for same-origin display."""
    if not 0 <= gallery_index < len(HANA_GALLERIES):
        return None
    cache_key = (gallery_index, image_index)
    now = time.monotonic()
    with HANA_IMAGE_CACHE_LOCK:
        cached_image = HANA_IMAGE_CACHE.get(cache_key)
        if cached_image is not None:
            cached_at, image_data = cached_image
            if now - cached_at < HANA_IMAGE_CACHE_TTL:
                HANA_IMAGE_CACHE.move_to_end(cache_key)
                return image_data
            del HANA_IMAGE_CACHE[cache_key]

    gallery = HANA_GALLERIES[gallery_index]
    images = get_hana_gallery_images(
        gallery["api_url"],
        gallery["page_title"],
        gallery["source_name"],
        gallery["source_url"],
    )
    if not 0 <= image_index < len(images):
        return None

    image_url = images[image_index]["url"]
    hostname = urlparse(image_url).hostname or ""
    if not hostname.endswith(".wikia.nocookie.net"):
        return None

    response = fetch_hana_url(
        image_url,
        headers={"User-Agent": "hana-gallery/1.0"},
    )
    if response is None:
        return None

    try:
        content_type = response.headers.get("content-type", "")
        if not content_type.startswith("image/"):
            return None
        content = response.content
    finally:
        response.close()

    if len(content) > HANA_MAX_IMAGE_BYTES:
        return None

    image_data = content, content_type
    with HANA_IMAGE_CACHE_LOCK:
        HANA_IMAGE_CACHE[cache_key] = (time.monotonic(), image_data)
        HANA_IMAGE_CACHE.move_to_end(cache_key)
        while len(HANA_IMAGE_CACHE) > HANA_IMAGE_CACHE_SIZE:
            HANA_IMAGE_CACHE.popitem(last=False)
    return image_data


@pages_bp.route("/")
def index():
    """Home page."""
    return render_template("index.html", title="Home")


@pages_bp.route("/about")
def about():
    """About page."""
    return render_template("about.html", title="About")


@pages_bp.route("/shopline")
def shopline():
    """Shopline page."""
    return render_template("shopline.html", title="Shopline")


@pages_bp.route("/hana/login", methods=["GET", "POST"])
def hana_login():
    """Render and process the password form for the Hana page."""
    if session.get(HANA_SESSION_KEY):
        return redirect(url_for("pages.hana"))

    error = None
    if request.method == "POST":
        password = request.form.get("password", "")
        expected_password = current_app.config["HANA_PASSWORD"]
        if not expected_password:
            abort(503)
        if hmac.compare_digest(password, expected_password):
            session[HANA_SESSION_KEY] = True
            return redirect(url_for("pages.hana"))
        error = "That password is not correct. Try again."

    return render_template("hana_login.html", title="Unlock Hana", error=error)


@pages_bp.route("/hana")
@hana_access_required
def hana():
    """Hana page."""
    galleries = []
    for gallery_index, gallery in enumerate(HANA_GALLERIES):
        images = get_hana_gallery_images(
            gallery["api_url"],
            gallery["page_title"],
            gallery["source_name"],
            gallery["source_url"],
        )
        galleries.append(
            {
                "images": [
                    {
                        **image,
                        "url": url_for(
                            "pages.hana_image",
                            gallery_index=gallery_index,
                            image_index=image_index,
                        ),
                    }
                    for image_index, image in enumerate(images)
                ],
                "title": gallery["title"],
            }
        )
    return render_template("hana.html", title="Hana", galleries=galleries)


@pages_bp.route("/hana/images/<int:gallery_index>/<int:image_index>")
@hana_access_required
def hana_image(gallery_index, image_index):
    """Serve a curated public gallery image from the app's origin."""
    image_data = get_hana_image_data(gallery_index, image_index)
    if image_data is None:
        abort(404)
    content, content_type = image_data
    return Response(
        content,
        content_type=content_type,
        headers={"Cache-Control": "private, max-age=3600"},
    )


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


@pages_bp.route("/webhook-logs")
def webhook_logs():
    """Webhook Logs page: Adyen webhook events received and verified."""
    return render_template("webhook_logs.html", title="Webhook Logs")


@pages_bp.route("/xendit_checkout")
def xendit_checkout():
    """Xendit Components one-time payment checkout."""
    total_cents = get_checkout_total_cents()
    return render_template(
        "xendit_checkout.html",
        title="Xendit Checkout",
        items=CHECKOUT_ITEMS,
        total_cents=total_cents,
        currency=CHECKOUT_CURRENCY,
    )


@pages_bp.route("/image-host")
def image_host():
    """Temporary image hosting page."""
    return render_template("image_host.html", title="Image Host")
