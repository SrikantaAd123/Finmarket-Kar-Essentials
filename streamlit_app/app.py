"""FINMARKET Kart Essentials - Amazon-inspired Streamlit storefront.

Uses the supplied FINMARKET FastAPI API as the source of truth:
  catalog, account, cart, orders, payments and Razorpay signature verification.
Authentication is native Streamlit OIDC against ZITADEL. Configure Google as an
external identity provider in ZITADEL to offer Google sign-in on the ZITADEL page.
"""
from __future__ import annotations

import html
import json
import os
import re
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx
import streamlit as st
import streamlit.components.v1 as components


# ============================================================
# RAZORPAY CONFIGURATION
# TEST MODE / LIVE MODE
# SECRETS VALIDATION
# PAYMENT CLIENT INITIALIZATION
# ============================================================

import os
import streamlit as st
import razorpay


# ------------------------------------------------------------
# 1. SAFE SECRETS ACCESS
# ------------------------------------------------------------

def get_secret_value(key: str, default=None):
    """
    Read a configuration value from Streamlit secrets
    or environment variables.

    Supports both top-level and [razorpay] TOML settings.
    """

    # First check top-level Streamlit secrets.
    try:
        value = st.secrets.get(key)

        if value is not None and str(value).strip():
            return value

    except Exception:
        pass

    # Then check nested [razorpay] section.
    try:
        razorpay_section = st.secrets.get("razorpay", {})

        if hasattr(razorpay_section, "get"):
            value = razorpay_section.get(key)

            if value is not None and str(value).strip():
                return value

    except Exception:
        pass

    # Finally check environment variables.
    value = os.getenv(key)

    if value is not None and str(value).strip():
        return value

    return default


# ------------------------------------------------------------
# 2. RAZORPAY CREDENTIAL LOADER
# ------------------------------------------------------------

def get_razorpay_credentials():
    """
    Load Razorpay credentials according to selected mode.

    Supported modes:
        test
        live

    Supported configuration formats:

    Generic:
        RAZORPAY_MODE = "test"
        RAZORPAY_KEY_ID = "..."
        RAZORPAY_KEY_SECRET = "..."

    Mode-specific:
        RAZORPAY_TEST_KEY_ID = "..."
        RAZORPAY_TEST_KEY_SECRET = "..."

        RAZORPAY_LIVE_KEY_ID = "..."
        RAZORPAY_LIVE_KEY_SECRET = "..."
    """

    mode = str(
        get_secret_value("RAZORPAY_MODE", "test")
    ).strip().lower()

    if mode not in ("test", "live"):
        raise RuntimeError(
            "Invalid RAZORPAY_MODE. "
            "Set it to either 'test' or 'live'."
        )

    mode_prefix = f"RAZORPAY_{mode.upper()}"

    # Mode-specific credentials take priority.
    key_id = (
        get_secret_value(f"{mode_prefix}_KEY_ID")
        or get_secret_value("RAZORPAY_KEY_ID")
    )

    key_secret = (
        get_secret_value(f"{mode_prefix}_KEY_SECRET")
        or get_secret_value("RAZORPAY_KEY_SECRET")
    )

    if not key_id:
        raise RuntimeError(
            f"Razorpay {mode.upper()} Key ID is missing. "
            "Check your secrets.toml configuration."
        )

    if not key_secret:
        raise RuntimeError(
            f"Razorpay {mode.upper()} Key Secret is missing. "
            "Check your secrets.toml configuration."
        )

    return (
        mode,
        str(key_id).strip(),
        str(key_secret).strip()
    )




# ------------------------------ configuration ------------------------------
APP_FILE = Path(__file__).resolve()
APP_DIR = APP_FILE.parent
PROJECT_ROOT = APP_DIR.parent
CLONE_ASSETS = APP_DIR / "assets" / "amazon_clone"
CLONE_PRODUCTS = CLONE_ASSETS / "products"
CLONE_BACKGROUND = CLONE_ASSETS / "background"
API_ROOT = os.getenv("FINMARKET_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
API_PREFIX = os.getenv("FINMARKET_API_PREFIX", "/api/v1").strip()
if not API_PREFIX.startswith("/"):
    API_PREFIX = "/" + API_PREFIX
API_PREFIX = API_PREFIX.rstrip("/")
API_TIMEOUT = float(os.getenv("FINMARKET_API_TIMEOUT", "25"))
IMAGES = PROJECT_ROOT / "frontend" / "static" / "images"
CATEGORIES_DIR = IMAGES / "categories"
PRODUCTS_DIR = IMAGES / "products"
BANNERS_DIR = IMAGES / "banners"
LOGO_DIR = IMAGES / "logo"

st.set_page_config(page_title="FINMARKET Kart Essentials", page_icon="🛒", layout="wide", initial_sidebar_state="expanded")

# ------------------------------ session state ------------------------------
DEFAULTS: dict[str, Any] = {
    "fm_page": "Home", "fm_search": "", "fm_category_id": None,
    "fm_category_name": "All departments", "fm_guest_token": uuid.uuid4().hex + uuid.uuid4().hex,
    "fm_categories": [], "fm_products": [], "fm_cart": {}, "fm_last_error": "",
    "fm_order_id": None, "fm_payment_message": "", "fm_last_catalog_query": None,
    "fm_guest_merged": False, "fm_selected_product": None,
    "fm_checkout_method": "cod", "fm_order_confirmation": None,
    "fm_language": "English", "fm_theme": "Light",
}
for _key, _value in DEFAULTS.items():
    if _key not in st.session_state:
        st.session_state[_key] = _value

# ------------------------------ visual design ------------------------------
st.markdown(r"""
<style>
:root{--bg:#080a0f;--panel:#111722;--panel2:#172131;--line:#2b3749;--muted:#aab5c6;--white:#f6f8fc}
html,body,[data-testid="stAppViewContainer"],[data-testid="stMain"]{background:var(--bg)!important;color:var(--white)!important}
[data-testid="stHeader"]{background:rgba(8,10,15,.94)!important}[data-testid="stSidebar"]{background:#0c111a!important;border-right:1px solid var(--line)}
[data-testid="stSidebar"] *{color:var(--white)}.block-container{max-width:1540px;padding-top:1rem;padding-bottom:3rem}
.fm-spectrum{height:4px;border-radius:99px;background:linear-gradient(90deg,#ff3158,#ff8b38,#f5d54a,#3ed58c,#39d5e6,#4b83ff,#a66cff);margin:10px 0 18px}
.fm-nav{background:#111925;border:1px solid #29384b;border-radius:14px;padding:12px 16px;display:flex;gap:16px;align-items:center;flex-wrap:wrap}
.fm-brand{font-size:25px;font-weight:950;letter-spacing:-1px;background:linear-gradient(90deg,#ff4267,#ff9d43,#f5d547,#42d392,#42d9e8,#528bff,#a879ff);-webkit-background-clip:text;background-clip:text;color:transparent}
.fm-muted{color:var(--muted);font-size:12px}.fm-hero{border:1px solid #35435a;border-radius:22px;padding:34px;background:radial-gradient(circle at 83% 15%,#263c68 0,transparent 32%),linear-gradient(120deg,#131d30,#21172e 60%,#101722);margin:14px 0 22px;min-height:220px}
.fm-hero h1{font-size:clamp(32px,4.5vw,56px);line-height:1.02;font-weight:950;margin:10px 0}.fm-hero p{color:#c7d0df;max-width:720px;font-size:16px}
.fm-chip{display:inline-block;padding:6px 10px;border:1px solid #43536b;border-radius:99px;background:#1b293b;color:#dce7f8;font-size:12px;margin:3px}
.fm-heading{font-size:24px;font-weight:900;margin:22px 0 12px}.fm-category{background:#131b27;border:1px solid #2c394c;border-radius:15px;padding:9px;height:100%}.fm-category img{height:112px;width:100%;object-fit:cover;border-radius:9px}.fm-category-name{font-size:13px;font-weight:800;margin:8px 0 2px}
.fm-product{background:linear-gradient(180deg,#151d29,#101620);border:1px solid #2b394d;border-radius:15px;padding:12px;height:100%}.fm-product img{width:100%;height:170px;object-fit:contain;background:#f7f8fa;border-radius:9px}.fm-product-name{font-size:14px;font-weight:800;line-height:1.35;min-height:40px;margin:8px 0}.fm-price{font-size:22px;font-weight:950}.fm-old{font-size:12px;color:#aab5c6;text-decoration:line-through}.fm-panel{background:#111925;border:1px solid #2b394c;border-radius:16px;padding:18px}.fm-banner{background:#131e2d;border:1px solid #34455f;border-radius:13px;padding:14px}
div.stButton>button{border-radius:9px!important;font-weight:750!important;background:#1b2a40!important;border:1px solid #425875!important;color:#fff!important}div.stButton>button[kind="primary"]{background:linear-gradient(90deg,#315fba,#7043b8)!important;border:0!important}
input,textarea,[data-baseweb="select"]>div{background:#111925!important;color:#f5f7fb!important;border-color:#344155!important}[data-testid="stMetric"]{background:#121b28;border:1px solid #2c394c;padding:12px;border-radius:12px}
[data-testid="stImage"] img{border-radius:10px}hr{border-color:#2b3749!important}a{color:#8abaff!important}

/* Amazon-clone inspired marketplace skin, rebranded for FINMARKET. */
:root{--bg:#eaeded;--panel:#fff;--panel2:#f3f3f3;--line:#d5d9d9;--muted:#565959;--white:#0f1111}
html,body,[data-testid="stAppViewContainer"],[data-testid="stMain"]{background:#eaeded!important;color:#0f1111!important}
[data-testid="stHeader"]{background:#232f3e!important;height:3.1rem!important;min-height:3.1rem!important;z-index:1000!important}
[data-testid="stSidebar"]{background:#232f3e!important;border-right:1px solid #394b5d}
[data-testid="stSidebar"] *{color:#fff!important}
/* Keep sidebar navigation readable on FINMARKET yellow/orange buttons. */
[data-testid="stSidebar"] div.stButton>button,
[data-testid="stSidebar"] div.stButton>button *,
[data-testid="stSidebar"] div.stButton>button p,
[data-testid="stSidebar"] div.stButton>button span{color:#111!important;-webkit-text-fill-color:#111!important}
.block-container{max-width:1600px;padding-top:3.7rem!important;padding-bottom:2.5rem}
.fm-spectrum{height:3px;border-radius:0;background:#ff9900;margin:8px 0 14px}
.fm-brand{font-size:25px;font-weight:950;letter-spacing:-1px;color:#fff!important;background:none;-webkit-text-fill-color:#fff}
.fm-hero{border:0;border-radius:0;padding:28px 34px;background:linear-gradient(110deg,#17283b,#263f57 55%,#e7a13c);margin:8px 0 16px;min-height:190px;color:white}
.fm-hero h1{color:#fff!important;font-size:clamp(30px,4vw,48px);margin:12px 0}.fm-hero p{color:#f5f5f5;max-width:760px}
.fm-chip{display:inline-block;padding:6px 10px;border:1px solid #e0ad00;border-radius:4px;background:#ffd814;color:#111!important;font-size:12px;font-weight:800}
.fm-heading{font-size:22px;font-weight:850;color:#0f1111;margin:20px 0 10px}
.fm-category{background:#fff;border:1px solid #d5d9d9;border-radius:2px;padding:10px;height:100%;box-shadow:0 1px 2px #00000012}
.fm-category img{height:125px;width:100%;object-fit:contain;border-radius:0;background:#fff}
.fm-category-name{font-size:14px;font-weight:800;color:#0f1111;margin:8px 0 4px}
.fm-product{background:#fff;border:1px solid #d5d9d9;border-radius:2px;padding:12px;height:100%;box-shadow:0 1px 2px #00000010}
.fm-product img{width:100%;height:185px;object-fit:contain;background:#fff;border-radius:0}
.fm-product-name{font-size:14px;font-weight:600;color:#0f1111;line-height:1.35;min-height:40px;margin:8px 0}
.fm-price{font-size:22px;font-weight:850;color:#b12704}.fm-old{font-size:12px;color:#565959;text-decoration:line-through}
.fm-panel{background:#fff;border:1px solid #d5d9d9;border-radius:3px;padding:18px;color:#0f1111}
.fm-banner{background:#fff;border:1px solid #d5d9d9;border-radius:3px;padding:14px}
div.stButton>button{border-radius:3px!important;font-weight:650!important;background:#ffd814!important;border:1px solid #fcd200!important;color:#0f1111!important}
div.stButton>button:hover{background:#f7ca00!important;border-color:#f2c200!important}
div.stButton>button[kind="primary"]{background:#ff9900!important;border:1px solid #e47911!important;color:#111!important}
input,textarea,[data-baseweb="select"]>div{background:#fff!important;color:#0f1111!important;border-color:#888c8c!important}
[data-testid="stMetric"]{background:#fff;border:1px solid #d5d9d9;padding:12px;border-radius:3px;color:#0f1111}
[data-testid="stImage"] img{border-radius:0}hr{border-color:#d5d9d9!important}a{color:#007185!important}
[data-testid="stMarkdownContainer"] h1,[data-testid="stMarkdownContainer"] h2,[data-testid="stMarkdownContainer"] h3{color:#0f1111}
/* Keep the marketplace header clear of Streamlit's top toolbar. */
.st-key-fm_topbar{background:#131921;border:1px solid #34465a;border-radius:8px;padding:12px 14px;margin:0 0 8px;color:#fff}
.st-key-fm_topbar [data-testid="stMarkdownContainer"] p{color:#fff!important;margin:0}
.fm-greeting{color:#fff;font-size:14px;font-weight:800;line-height:1.35;text-align:right}
.fm-identity{color:#d7e3ef;font-size:11px;text-align:right;margin-top:3px}
.fm-cart-count{color:#ffd814;font-size:12px;font-weight:700;text-align:right}
/* FINMARKET home categories and promotional artwork */
.fm-home-section-title{font-size:30px!important;font-weight:900!important;color:#111!important;margin:18px 0 8px!important;letter-spacing:-.4px}
.fm-home-subtitle{font-size:22px!important;font-weight:850!important;color:#17212d!important;margin:10px 0 14px!important}
.fm-promo-wrap{max-width:1180px;margin:12px auto 24px;padding:10px;background:#fff;border:1px solid #d5d9d9;border-radius:10px;box-shadow:0 3px 12px #00000012}
.fm-promo-wrap img{width:100%;max-height:250px;object-fit:contain;border-radius:8px}
.fm-visual-card{background:#fff;border:1px solid #d5d9d9;border-radius:9px;padding:7px;box-shadow:0 2px 7px #00000010}
.fm-visual-card img{width:100%;height:145px;object-fit:cover;border-radius:6px}
.fm-category{background:#fff;border:1px solid #d5d9d9;border-radius:9px;padding:12px;height:100%;box-shadow:0 2px 7px #00000010;text-align:center}
.fm-category img{height:178px!important;width:100%!important;object-fit:contain!important;border-radius:6px!important;background:#fff}
.fm-category-name{font-size:15px;font-weight:850;color:#111;margin:10px 0 8px;min-height:38px}
.fm-grocery-mark{background:#fff8e8;border:1px solid #ff9900;border-radius:9px;padding:8px;text-align:center;color:#17212d;font-size:12px;line-height:1.35}
.fm-grocery-promo-fallback{min-height:130px;background:linear-gradient(110deg,#fff1c7,#ffe0a3 48%,#fff8e8);border:1px solid #ff9900;border-radius:9px;padding:26px 18px;color:#111;font-size:20px;line-height:1.4;text-align:center}
.fm-grocery-promo-fallback span{font-size:13px;color:#333}
 .fm-search-label{font-size:11px;color:#d7e3ef;margin-bottom:4px}
.fm-marketplace-tagline{max-width:1180px;margin:18px auto;padding:15px 20px;border-radius:9px;text-align:center;font-weight:800;line-height:1.55;color:#17351f;background:linear-gradient(100deg,#f1f9e9,#fff8df 52%,#edf8e9);border:1px solid #b8d69a;box-shadow:0 2px 8px #0000000d}
.fm-marketplace-tagline-top{font-size:clamp(15px,1.6vw,19px);margin-top:18px}
.fm-marketplace-tagline-bottom{font-size:15px;margin-top:12px}
.fm-brand-artwork-fallback{max-width:900px;margin:16px auto;padding:35px 20px;text-align:center;background:#fff;border:1px solid #d5d9d9;border-radius:10px}
.fm-brand-mark{display:block;font-size:clamp(28px,4vw,48px);font-weight:950;color:#07502a;letter-spacing:-1px}
.fm-brand-subtitle{display:block;margin-top:8px;color:#315b3a;font-size:16px;font-style:italic}
.fm-visual-gallery-title{font-size:20px;font-weight:850;color:#17212d;margin:20px 0 10px}
[class*="st-key-fm_category_card"] [data-testid="stImage"] img{height:190px!important;max-height:190px!important;width:100%!important;object-fit:contain!important;background:#fff!important}
.st-key-fm_topbar [data-testid="stTextInput"] input{min-height:42px!important;font-size:15px!important;border:2px solid #ff9900!important;border-radius:5px!important}
.st-key-fm_topbar div.stButton>button{min-height:42px!important;font-size:15px!important;border-radius:5px!important}


/* Home hero: keep the marketplace collage subtle and aligned beside the headline. */
.st-key-fm_home_hero{
    background:linear-gradient(110deg,#17283b 0%,#263f57 58%,#d99a3b 100%);
    border:0!important;border-radius:0!important;padding:10px 18px!important;
    margin:8px 0 16px!important;
}
.st-key-fm_home_hero [data-testid="stMarkdownContainer"] .fm-hero{
    background:transparent!important;border:0!important;margin:0!important;
    padding:22px 18px!important;min-height:0!important;
}
.st-key-fm_home_hero [data-testid="stImage"] img{
    width:100%!important;height:215px!important;max-height:215px!important;object-fit:contain!important;
    border-radius:10px!important;background:rgba(255,255,255,.04)!important;
}
.fm-hero-art-placeholder{
    min-height:185px;display:flex;flex-direction:column;align-items:center;
    justify-content:center;text-align:center;color:#fff;font-size:38px;
    font-weight:900;background:rgba(10,20,35,.24);border:1px solid #ffffff55;
    border-radius:10px;padding:18px;
}
.fm-hero-art-placeholder span{font-size:12px;font-weight:600;margin-top:8px;color:#fff}
</style>
""", unsafe_allow_html=True)

# User-selectable theme. The default retains the existing marketplace light skin.
if st.session_state.get("fm_theme", "Light") == "Dark":
    st.markdown("""<style>
    html,body,[data-testid="stAppViewContainer"],[data-testid="stMain"]{background:#10151d!important;color:#eef3f8!important}
    [data-testid="stHeader"]{background:#172231!important}
    [data-testid="stSidebar"]{background:#172231!important}
    [data-testid="stMarkdownContainer"] h1,[data-testid="stMarkdownContainer"] h2,[data-testid="stMarkdownContainer"] h3,
    [data-testid="stMarkdownContainer"] p,[data-testid="stMarkdownContainer"] li{color:#eef3f8!important}
    .fm-category,.fm-product,.fm-panel,.fm-banner,[data-testid="stMetric"]{background:#1b2635!important;color:#eef3f8!important;border-color:#39485b!important}
    .fm-category-name,.fm-product-name{color:#eef3f8!important}
    input,textarea,[data-baseweb="select"]>div{background:#202c3c!important;color:#fff!important;border-color:#53647a!important}
    [data-testid="stExpander"]{background:#1b2635!important;color:#eef3f8!important}
    </style>""", unsafe_allow_html=True)

# Lightweight translations for the main navigation, settings and checkout controls.
TRANSLATIONS = {
    "English": {},
    "Hindi": {
        "Home": "होम", "Shop": "दुकान", "Cart": "कार्ट", "Checkout": "चेकआउट",
        "Orders": "मेरे ऑर्डर", "Account": "खाता", "Settings": "सेटिंग्स", "Sign in": "साइन इन",
        "Search products or categories": "उत्पाद या श्रेणी खोजें", "Search": "खोजें",
        "Your Shopping Cart": "आपकी शॉपिंग कार्ट", "Secure Checkout": "सुरक्षित चेकआउट",
        "Order Summary": "ऑर्डर सारांश", "Select Payment Method": "भुगतान का तरीका चुनें",
        "Cash on Delivery": "कैश ऑन डिलीवरी", "Razorpay (UPI / Cards / Netbanking)": "Razorpay (UPI / कार्ड / नेटबैंकिंग)",
        "Settings & Preferences": "सेटिंग्स और प्राथमिकताएँ", "Language": "भाषा", "Theme": "थीम",
        "Account Details": "खाते का विवरण", "Saved Delivery Addresses": "सहेजे गए डिलीवरी पते",
        "Add a New Delivery Address": "नया डिलीवरी पता जोड़ें",
    },
    "Telugu": {
        "Home": "హోమ్", "Shop": "షాప్", "Cart": "కార్ట్", "Checkout": "చెకౌట్",
        "Orders": "నా ఆర్డర్లు", "Account": "ఖాతా", "Settings": "సెట్టింగ్స్", "Sign in": "సైన్ ఇన్",
        "Search products or categories": "ఉత్పత్తులు లేదా వర్గాలను వెతకండి", "Search": "వెతకండి",
        "Your Shopping Cart": "మీ షాపింగ్ కార్ట్", "Secure Checkout": "సురక్షిత చెకౌట్",
        "Order Summary": "ఆర్డర్ సారాంశం", "Select Payment Method": "చెల్లింపు విధానాన్ని ఎంచుకోండి",
        "Cash on Delivery": "క్యాష్ ఆన్ డెలివరీ", "Razorpay (UPI / Cards / Netbanking)": "Razorpay (UPI / కార్డులు / నెట్‌బ్యాంకింగ్)",
        "Settings & Preferences": "సెట్టింగ్స్ మరియు ప్రాధాన్యతలు", "Language": "భాష", "Theme": "థీమ్",
        "Account Details": "ఖాతా వివరాలు", "Saved Delivery Addresses": "సేవ్ చేసిన డెలివరీ చిరునామాలు",
        "Add a New Delivery Address": "కొత్త డెలివరీ చిరునామా జోడించండి",
    },
}

def tr(text: str) -> str:
    return TRANSLATIONS.get(st.session_state.get("fm_language", "English"), {}).get(text, text)

# -------------------------------- helpers -----------------------------------
def dct(x: Any) -> dict[str, Any]:
    return x if isinstance(x, dict) else {}

def rows(payload: Any, *keys: str) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [dct(x) for x in payload if isinstance(x, dict)]
    obj = dct(payload)
    for key in keys:
        if isinstance(obj.get(key), list):
            return [dct(x) for x in obj[key] if isinstance(x, dict)]
    if isinstance(obj.get("data"), (dict, list)):
        return rows(obj["data"], *keys)
    return []

def pick(obj: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if obj.get(key) not in (None, ""):
            return obj[key]
    return default

def safe_int(v: Any, default: int = 0) -> int:
    try: return int(v)
    except (TypeError, ValueError): return default

def money(v: Any, currency: str = "INR") -> str:
    try: n = float(v)
    except (TypeError, ValueError): return "Price unavailable"
    return f"₹{n:,.2f}" if currency.upper() == "INR" else f"{currency} {n:,.2f}"

def api_url(path: str) -> str:
    return f"{API_ROOT}{API_PREFIX}/{path.strip('/')}"

def current_user() -> dict[str, Any]:
    try:
        u = st.user
        if not bool(u.is_logged_in): return {}
        return {"name": getattr(u, "name", "Customer"), "email": getattr(u, "email", ""), "picture": getattr(u, "picture", "")}
    except Exception: return {}

def token() -> str | None:
    try:
        t = st.user.tokens.get("access")
        return t if isinstance(t, str) and t else None
    except Exception: return None

def logged_in() -> bool:
    return bool(current_user()) and bool(token())

def api(method: str, path: str, *, body: dict[str, Any] | None = None, params: dict[str, Any] | None = None, auth: bool = False, guest: bool = False) -> tuple[Any | None, str | None, int | None]:
    headers: dict[str, str] = {"Accept": "application/json"}
    if auth:
        bearer = token()
        if not bearer: return None, "Please sign in again. No ZITADEL access token is exposed to Streamlit.", 401
        headers["Authorization"] = f"Bearer {bearer}"
    if guest: headers["X-Guest-Cart-Token"] = str(st.session_state.fm_guest_token)
    try:
        res = httpx.request(method, api_url(path), headers=headers, json=body, params=params, timeout=API_TIMEOUT)
        try: data = res.json()
        except ValueError: data = {"detail": res.text[:600]}
        if res.is_success: return data, None, res.status_code
        detail = pick(dct(data), "detail", "message", default=f"HTTP {res.status_code}")
        return data, str(detail), res.status_code
    except httpx.ConnectError: return None, f"Cannot connect to FastAPI at {API_ROOT}. Start backend on port 8000.", None
    except httpx.TimeoutException: return None, "The API request timed out. Please retry.", None
    except httpx.RequestError as exc: return None, f"API request failed: {exc}", None

def local_image(folder: Path, candidates: list[str]) -> str | None:
    for name in candidates:
        if not name: continue
        p = folder / name
        if p.is_file(): return str(p)
    return None

def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")

def image_url(value: Any) -> str | None:
    if isinstance(value, dict): value = pick(value, "image_url", "url", "src")
    if not isinstance(value, str) or not value.strip(): return None
    value = value.strip()
    if value.startswith(("http://", "https://")): return value
    # FINMARKET seed data stores image paths as /images/... while FastAPI
    # mounts the frontend static directory at /static.
    if value.startswith("/images/"):
        value = "/static" + value
    if value.startswith("/"): return urljoin(API_ROOT + "/", value.lstrip("/"))
    p = PROJECT_ROOT / value
    return str(p) if p.is_file() else urljoin(API_ROOT + "/", value)

def category_image(cat: dict[str, Any]) -> str | None:
    """Use category-specific photography for supported marketplace departments."""
    name = str(pick(cat, "name", "slug", default=""))
    slug = slugify(str(pick(cat, "slug", default=name)))

    # Use dedicated, category-relevant Unsplash photographs for the four
    # marketplace departments. These take priority over stale API thumbnails.
    department_aliases = {
        "mobile-gadgets": "mobile-gadgets",
        "mobiles-gadgets": "mobile-gadgets",
        "mobile": "mobile-gadgets",
        "accessories": "accessories",
        "electronics": "electronics",
        "sports": "sports",
        "clothes-fashion": "clothes-fashion",
        "clothes": "clothes-fashion",
        "fashion": "clothes-fashion",
        "medicines-healthcare": "medicines-healthcare",
        "medicines": "medicines-healthcare",
        "healthcare": "medicines-healthcare",
    }
    department_images = {
        "mobile-gadgets": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=1000&q=85",
        "accessories": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=1000&q=85",
        "electronics": "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?auto=format&fit=crop&w=1000&q=85",
        "sports": "https://images.unsplash.com/photo-1461896836934-ffe607ba8211?auto=format&fit=crop&w=1000&q=85",
        "clothes-fashion": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRBVeI4CSYStz7ipYebx0OitA-iz7VAg4aGST4MYtecBw&s=10",
        "medicines-healthcare": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcT17ju1TvcC2AP6USaDXJs0wwSxYfwDcbYbFKDd-AWhkw&s=10",
    }
    department_key = department_aliases.get(slug)
    if not department_key:
        normalized_name = slugify(name)
        department_key = department_aliases.get(normalized_name)
    if department_key:
        return department_images[department_key]

    aliases = {
        "bakery": ["bread.jpg", "dairy-breakfast.jpg"],
        "beverages": ["tea.jpg", "snacks-beverages.jpg"],
        "cooking-essentials": ["cooking-oil.jpg", "food-grains.jpg"],
        "dairy-eggs": ["milk.jpg", "eggs.jpg", "dairy-breakfast.jpg"],
        "dairy-and-eggs": ["milk.jpg", "eggs.jpg", "dairy-breakfast.jpg"],
        "fruits-vegetables": ["fruits-vegetables.jpg", "apple.jpg", "tomato.jpg"],
        "household-essentials": ["household-essentials.jpg", "home-kitchen-living.jpg"],
        "personal-care": ["beauty-personal-care.jpg", "personal-care.jpg"],
        "pulses-lentils": ["toor-dal.jpg", "moong-dal.jpg", "food-grains.jpg"],
        "rice-grains": ["rice.jpg", "food-grains.jpg"],
        "snacks-munchies": ["snacks-beverages.jpg"],
        "snacks": ["snacks-beverages.jpg"],
        "household": ["household-essentials.jpg", "home-kitchen-living.jpg"],
        "grocery-essentials": ["grocery-essentials.jpg", "grocery-essentials-banner.jpg"],
        "beauty-personal-care": ["beauty-personal-care.jpg", "personal-care.jpg"],
        "home-kitchen-living": ["home-kitchen-living.jpg", "home-kitchen-banner.jpg"],
        "mobiles-gadgets": ["mobiles-gadgets.jpg", "mobiles-gadgets-banner.jpg"],
        "tv-audio-wearables": ["tv-audio-wearables.jpg", "tv-audio-wearables-banner.jpg"],
        "laptops-computers": ["laptops-computers.jpg", "computers-laptops-banner.jpg"],
        "home-appliances": ["home-appliances.jpg", "home-appliances-banner.jpg"],
        "fashion-accessories": ["fashion-accessories.jpg", "fashion-accessories-banner.jpg"],
        "toys-sports-outdoors": ["toys-sports-outdoors.jpg", "toys-sports-outdoors-banner.jpg"],
    }
    candidates = aliases.get(slug, [slug + ".jpg"])
    local = (
        local_image(CATEGORIES_DIR, candidates)
        or local_image(BANNERS_DIR, candidates)
        or local_image(PRODUCTS_DIR, candidates)
    )
    if local:
        return local
    return image_url(pick(cat, "image_url", "image"))



def product_image(product: dict[str, Any]) -> str | None:
    """
    Resolve product images.

    Priority:
    1. Primary image URL returned by FastAPI
    2. Product image URL returned by FastAPI
    3. Matching local product photograph
    4. Category fallback photograph
    """

    # 1. Use database/API product image FIRST.
    api_image = image_url(
        pick(
            product,
            "primary_image_url",
            "image_url",
            "image",
        )
    )

    if api_image:
        return api_image

    # 2. Try a matching local product image.
    name = str(
        pick(product, "slug", "name", default="")
    )

    slug = slugify(name)

    for folder in (PRODUCTS_DIR, CLONE_PRODUCTS):
        if not folder.exists():
            continue

        for file_path in folder.glob("*"):
            if not file_path.is_file():
                continue

            filename = file_path.stem.lower()

            if (
                slug == filename
                or filename in slug
                or slug in filename
            ):
                return str(file_path)

    # 3. Category fallback only when no product image exists.
    category = slugify(
        str(product.get("category_name") or "")
    )

    fallback = {
        "bakery": ["bread.jpg"],
        "beverages": ["tea.jpg"],
        "cooking-essentials": ["cooking-oil.jpg"],
        "dairy-eggs": ["milk.jpg", "eggs.jpg"],
        "dairy-and-eggs": ["milk.jpg", "eggs.jpg"],
        "fruits-vegetables": ["apple.jpg", "tomato.jpg"],
        "household-essentials": ["household-essentials.jpg"],
        "personal-care": ["personal-care.jpg"],
        "pulses-lentils": ["toor-dal.jpg", "moong-dal.jpg"],
        "rice-grains": ["rice.jpg"],
        "snacks-munchies": ["snacks-beverages.jpg"],
        "snacks": ["snacks-beverages.jpg"],
        "household": [
            "household-essentials.jpg",
            "home-kitchen-living.jpg",
        ],
    }.get(category, ["grocery-essentials.jpg"])

    return (
        local_image(PRODUCTS_DIR, fallback)
        or local_image(CATEGORIES_DIR, fallback)
        or local_image(BANNERS_DIR, fallback)
        or local_image(CLONE_PRODUCTS, ["iphone.png"])
    )

def ensure_customer() -> bool:
    if not logged_in(): return False
    data, err, status = api("POST", "account/bootstrap", body={}, auth=True)
    if err:
        st.error(f"Your identity is signed in, but FINMARKET could not provision your customer account: {err}")
        return False
    # Preserve this browser session's guest cart after the first successful login.
    if not st.session_state.fm_guest_merged:
        guest_data, guest_error, _ = api("GET", "cart/guest", guest=True)
        guest_cart = dct(guest_data).get("cart", dct(guest_data))
        for line in rows(guest_cart, "items", "cart_items"):
            product_id = safe_int(line.get("product_id"))
            quantity = max(1, safe_int(line.get("quantity"), 1))
            if product_id:
                _, merge_error, _ = api("POST", "cart/items", body={"product_id": product_id, "quantity": quantity}, auth=True)
                if merge_error:
                    st.warning(f"Could not move one guest-cart item into your account: {merge_error}")
        # Mark the merge attempt once. Do not duplicate items on each rerun.
        st.session_state.fm_guest_merged = True
    return True

# ----------------------------- authentication ------------------------------

def sign_in_panel() -> None:
    st.markdown(
        """
        <div class="fm-hero">
            <span class="fm-chip">SECURE CUSTOMER ACCOUNT</span>
            <h1>Welcome to FINMARKET</h1>
            <p>
                Sign in to save addresses, manage your cart,
                pay securely and track orders.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="fm-panel">', unsafe_allow_html=True)
    st.subheader("Continue with your account")

    try:
        auth_config = st.secrets.get("auth", {})
        zitadel_config = auth_config.get("zitadel", {})

        required_shared = ["redirect_uri", "cookie_secret"]
        required_provider = [
            "client_id",
            "client_secret",
            "server_metadata_url",
        ]

        missing = [
            key for key in required_shared
            if not auth_config.get(key)
        ]

        missing += [
            key for key in required_provider
            if not zitadel_config.get(key)
        ]

        if missing:
            st.error(
                "ZITADEL configuration is incomplete. "
                "Missing: " + ", ".join(missing)
            )
            st.caption(
                "Check streamlit_app/.streamlit/secrets.toml."
            )
            st.markdown("</div>", unsafe_allow_html=True)
            return

        if not logged_in():
            if st.button(
                "🔐 Continue with ZITADEL / Google",
                type="primary",
                use_container_width=True,
            ):
                st.login("zitadel")
        else:
            user = current_user()
            st.success(
                f"Signed in as {user.get('email') or user.get('name')}"
            )

            if st.button("Sign out", use_container_width=True):
                st.logout()

    except Exception as exc:
        st.error(f"Authentication error: {exc}")
        st.info(
            "Verify your ZITADEL client credentials, "
            "OIDC discovery URL and redirect URI."
        )

    st.caption(
        "Google sign-in is available through ZITADEL "
        "when Google is configured as an external identity provider."
    )

    st.markdown("</div>", unsafe_allow_html=True)

def logout() -> None:
    try: st.logout()
    except Exception: st.rerun()

# ------------------------------- catalogue ---------------------------------


HOME_CATEGORY_NAMES = {
    "bakery",
    "beverages",
    "cooking essentials",
    "dairy & eggs",
    "fruits & vegetables",
    "household essentials",
    "personal care",
    "pulses & lentils",
    "rice & grains",
    "snacks & munchies",

    # NEW CATEGORIES
    "mobile gadgets",
    "accessories",
    "electronics",
    "sports",
    "clothes & fashion",
    "medicines & healthcare",
}



@st.cache_data(ttl=60, show_spinner=False)
def fetch_categories() -> list[dict[str, Any]]:
    data, err, status = api("GET", "catalog/categories")

    if err:
        st.session_state.fm_last_error = f"Categories: {err}"
        return []

    categories = rows(data, "categories", "items")

    # Only allow genuine category names on the Home page.
    valid_categories = []

    for category in categories:
        name = str(category.get("name", "")).strip()
        normalized_name = name.casefold()

        if normalized_name not in HOME_CATEGORY_NAMES:
            continue

        if category.get("is_active") is False:
            continue

        valid_categories.append(category)

    return valid_categories



def fetch_products(
    search: str = "",
    category_id: Any = None,
    sort: str = "created_at",
    order: str = "desc"
) -> list[dict[str, Any]]:
    """Fetch up to 300 products; Clothes & Fashion includes unpublished catalogue rows for display."""
    query = str(search or "").strip()

    PAGE_SIZE = 100
    MAX_PRODUCTS = 300

    base_params: dict[str, Any] = {
        "page_size": PAGE_SIZE,
        "sort_by": sort,
        "sort_order": order,
    }

    if query:
        base_params["search"] = query

    if category_id not in (None, "", "all"):
        base_params["category_id"] = category_id

    collected: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    # Fetch three pages of 100 products each.
    for page_number in range(1, 4):
        params = dict(base_params)
        params["page"] = page_number

        # Category 15 uses its category endpoint. The backend endpoint is
        # configured to return all active Clothes & Fashion catalogue rows,
        # including unpublished items, so the storefront can display the full
        # CF-001–CF-170 catalogue. Other departments remain published-only.
        endpoint = (
            f"catalog/products/category/{category_id}"
            if str(category_id) == "15"
            else "catalog/products"
        )
        data, err, _ = api(
            "GET",
            endpoint,
            params=params
        )

        if err:
            st.session_state.fm_last_error = f"Products: {err}"

            # Preserve products already fetched from the first page.
            if not collected:
                return []
            break

        page_products = rows(data, "products", "items")

        if not page_products:
            break

        for product in page_products:
            product_id = str(
                pick(product, "id", "product_id", default="")
            )

            # Avoid duplicate products across pages.
            if product_id and product_id in seen_ids:
                continue

            if product_id:
                seen_ids.add(product_id)

            is_active = product.get("is_active", True) not in (False, 0, "0")
            is_published = product.get("is_published", True) not in (False, 0, "0")
            is_clothes_fashion = str(category_id) == "15"

            # Category 15 intentionally displays all active catalogue records,
            # even when publication is pending. Other categories stay public-only.
            if is_active and (is_published or is_clothes_fashion):
                collected.append(product)

        if len(page_products) < PAGE_SIZE:
            break

    products = collected

    # Apply dependable local search.
    if query:
        q = query.casefold()

        def matches(product: dict[str, Any]) -> bool:
            category = dct(product.get("category"))

            fields = (
                product.get("name"),
                product.get("description"),
                product.get("short_description"),
                product.get("sku"),
                product.get("category_name"),
                category.get("name"),
                product.get("brand"),
            )

            return any(
                q in str(value or "").casefold()
                for value in fields
            )

        products = [
            product for product in products
            if matches(product)
        ]

    # Apply category filtering locally.
    if category_id not in (None, "", "all"):
        products = [
            product for product in products
            if str(product.get("category_id")) == str(category_id)
        ]

    return products[:MAX_PRODUCTS]

def get_cart() -> dict[str, Any]:
    auth = logged_in()
    data, err, _ = api("GET", "cart" if auth else "cart/guest", auth=auth, guest=not auth)
    if err:
        st.session_state.fm_last_error = f"Cart: {err}"
        return {}
    cart = dct(data)
    if isinstance(cart.get("cart"), dict): cart = cart["cart"]
    st.session_state.fm_cart = cart
    return cart

def cart_items(cart: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    return rows(cart if cart is not None else dct(st.session_state.fm_cart), "items", "cart_items")

def cart_count() -> int:
    return sum(safe_int(i.get("quantity"), 1) for i in cart_items())

def mutate_cart(action: str, *, item_id: Any = None, product_id: Any = None, quantity: int = 1) -> bool:
    auth = logged_in(); guest = not auth
    if action == "add": method, path, body = "POST", "cart/items" if auth else "cart/guest/items", {"product_id": safe_int(product_id), "quantity": quantity}
    elif action == "update": method, path, body = "PATCH", f"cart/items/{item_id}" if auth else f"cart/guest/items/{item_id}", {"quantity": quantity}
    elif action == "remove": method, path, body = "DELETE", f"cart/items/{item_id}" if auth else f"cart/guest/items/{item_id}", None
    else: return False
    data, err, _ = api(method, path, body=body, auth=auth, guest=guest)
    if err: st.error(f"Cart update failed: {err}"); return False
    st.session_state.fm_cart = dct(data).get("cart", dct(data))
    get_cart()
    return True

# -------------------------------- header ------------------------------------
def perform_header_search() -> None:
    """Resolve a category name first, otherwise search the product catalogue."""
    query = str(st.session_state.get("fm_search_box", "")).strip()
    if not query:
        st.session_state.fm_search = ""
        st.session_state.fm_category_id = None
        st.session_state.fm_category_name = "All departments"
        st.session_state.fm_page = "Shop"
        return

    categories = fetch_categories()
    category_match = next(
        (c for c in categories
         if query.casefold() in str(c.get("name", "")).strip().casefold()),
        None,
    )
    if category_match:
        st.session_state.fm_category_id = category_match.get("id")
        st.session_state.fm_category_name = str(category_match.get("name", "All departments"))
        st.session_state.fm_search = ""
        st.session_state.fm_search_box = ""
    else:
        st.session_state.fm_category_id = None
        st.session_state.fm_category_name = "All departments"
        st.session_state.fm_search = query
    st.session_state.fm_page = "Shop"


def header() -> None:
    user = current_user()
    logo = local_image(
        LOGO_DIR,
        ["finmarket-kart-essentials-logo-white.jpg", "finmarket-kart-essentials-logo.png", "finmarket-logo.png"],
    )
    with st.container(key="fm_topbar"):
        left, middle, search_btn, account, cart_col = st.columns(
            [1.25, 4.0, 0.62, 1.55, 0.9], vertical_alignment="center", gap="small"
        )
        with left:
            if logo:
                st.image(logo, width=175)
            else:
                st.markdown('<div class="fm-brand">FINMARKET</div>', unsafe_allow_html=True)
        with middle:
            st.text_input(
                tr("Search products or categories"),
                value=st.session_state.fm_search,
                placeholder="Search for a product or category…",
                label_visibility="collapsed",
                key="fm_search_box",
                on_change=perform_header_search,
            )
        with search_btn:
            st.markdown(f'<div class="fm-search-label">{html.escape(tr("Search"))}</div>', unsafe_allow_html=True)
            st.button(
                "🔍", key="fm_header_search", help="Search products and categories",
                use_container_width=True, on_click=perform_header_search,
            )
        with account:
            display_name = str(user.get("name") or user.get("email") or "Guest")
            greeting = f"Hello, {display_name}"
            st.markdown(
                f'<div class="fm-greeting">{html.escape(greeting)}</div>'
                f'<div class="fm-identity">{"ZITADEL account" if user else "Sign in to your account"}</div>',
                unsafe_allow_html=True,
            )
        with cart_col:
            st.markdown('<div class="fm-search-label">YOUR CART</div>', unsafe_allow_html=True)
            if st.button(f"🛒 {cart_count()}", key="fm_header_cart", help="Open your shopping cart", use_container_width=True):
                st.session_state.fm_page = "Cart"
                st.rerun()
    st.markdown('<div class="fm-spectrum"></div>', unsafe_allow_html=True)

# --------------------------------- pages ------------------------------------

def department_caption(name: str) -> str:
    """Short customer-facing caption shown below each department logo."""
    key = slugify(name)
    captions = {
        "grocery": "Daily pantry and grocery needs",
        "grocery-essentials": "Everyday pantry essentials",
        "bakery": "Fresh bakery favourites",
        "beverages": "Drinks for every day",
        "cooking-essentials": "Oils, spices and cooking needs",
        "dairy-eggs": "Milk, dairy and fresh eggs",
        "fruits-vegetables": "Fresh fruits and vegetables",
        "household-essentials": "Essentials for a happy home",
        "personal-care": "Everyday personal care",
        "pulses-lentils": "Wholesome pulses and lentils",
        "rice-grains": "Rice, grains and staples",
        "snacks-munchies": "Tasty snacks and treats",
        "mobile-gadgets": "Mobiles and smart gadgets",
        "accessories": "Useful everyday accessories",
        "electronics": "Electronics and technology",
        "sports": "Sports and outdoor essentials",
        "clothes-fashion": "Clothing, fashion wear, footwear and blankets",
        "medicines-healthcare": "Medicines, first aid and healthcare essentials",
    }
    return captions.get(key, f"Explore {name.lower()} at FINMARKET")


def find_finmarket_visual_asset(filename: str) -> str | None:
    """Find a named FINMARKET image in the known frontend asset locations."""
    roots = [
        IMAGES,
        BANNERS_DIR,
        LOGO_DIR,
        PROJECT_ROOT,
        APP_DIR,
        APP_DIR / "finmarket_grocery_visual_set",
        PROJECT_ROOT / "finmarket_grocery_visual_set",
        APP_DIR / "assets" / "finmarket_grocery_visual_set",
        PROJECT_ROOT / "frontend" / "static" / "images" / "finmarket_grocery_visual_set",
    ]
    for root in roots:
        candidate = root / filename
        if candidate.is_file():
            return str(candidate)
    # The visual-set folder may be nested one level differently in the supplied project.
    for root in (APP_DIR, PROJECT_ROOT / "frontend" / "static" / "images"):
        if root.is_dir():
            try:
                match = next((item for item in root.rglob(filename) if item.is_file()), None)
            except (OSError, PermissionError):
                match = None
            if match:
                return str(match)
    return None


def finmarket_visual_set_images() -> list[str]:
    """Return a few optional images from finmarket_grocery_visual_set."""
    folders = [
        APP_DIR / "finmarket_grocery_visual_set",
        PROJECT_ROOT / "finmarket_grocery_visual_set",
        APP_DIR / "assets" / "finmarket_grocery_visual_set",
        PROJECT_ROOT / "frontend" / "static" / "images" / "finmarket_grocery_visual_set",
        IMAGES / "finmarket_grocery_visual_set",
    ]
    found: list[str] = []
    for folder in folders:
        if not folder.is_dir():
            continue
        try:
            files = sorted(
                item for item in folder.iterdir()
                if item.is_file() and item.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
            )
        except (OSError, PermissionError):
            files = []
        for item in files:
            if item.name.casefold() in {"finmarket-logo.png", "finmarket-logo.webp", "finmarket-logo.jpg", "finmarket-grocery-promo.jpg", "finmarket-grocery-promo.png", "finmarket-grocery-promo.webp"}:
                continue
            path = str(item)
            if path not in found:
                found.append(path)
            if len(found) >= 4:
                return found
    return found


def render_home_promotions() -> None:
    """Show the supplied FINMARKET brand artwork below categories, with marketplace messaging."""
    logo = (
        find_finmarket_visual_asset("finmarket-logo.png")
        or find_finmarket_visual_asset("finmarket-logo.webp")
        or find_finmarket_visual_asset("finmarket-logo.jpg")
        or find_finmarket_visual_asset("image.webp")
    )
    promo = (
        find_finmarket_visual_asset("finmarket-grocery-promo.jpg")
        or find_finmarket_visual_asset("finmarket-grocery-promo.png")
        or find_finmarket_visual_asset("finmarket-grocery-promo.webp")
    )
    visual_images = finmarket_visual_set_images()

    st.markdown(
        "<div class='fm-marketplace-tagline fm-marketplace-tagline-top'>"
        "More than groceries — discover electronics, mobile gadgets, sports essentials, "
        "accessories and everyday products, all in one marketplace.</div>",
        unsafe_allow_html=True,
    )

    # The supplied FINMARKET.IN artwork is displayed prominently and centered below categories.
    if logo:
        left, center, right = st.columns([1, 8, 1], gap="small")
        with center:
            with st.container(key="fm_home_brand_artwork", border=True):
                st.image(logo, width=760)
    else:
        st.markdown(
            "<div class='fm-brand-artwork-fallback'><span class='fm-brand-mark'>🛒 FINMARKET.IN</span>"
            "<span class='fm-brand-subtitle'>Your everyday marketplace — groceries, electronics, sports and more</span></div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        "<div class='fm-marketplace-tagline fm-marketplace-tagline-bottom'>"
        "One destination for fresh groceries, smart technology, sports and lifestyle essentials. "
        "Explore more categories as our product range grows.</div>",
        unsafe_allow_html=True,
    )

    # Optional grocery campaign banner remains secondary to the all-products marketplace message.
    if promo:
        left, center, right = st.columns([1, 8, 1], gap="small")
        with center:
            with st.container(key="fm_home_grocery_campaign", border=True):
                st.image(promo, use_container_width=True)

    if visual_images:
        st.markdown("<div class='fm-visual-gallery-title'>Discover FINMARKET</div>", unsafe_allow_html=True)
        gallery_items = visual_images[:4]
        gallery_cols = st.columns(len(gallery_items), gap="medium")
        for col, image_path in zip(gallery_cols, gallery_items):
            with col:
                with st.container(key=f"fm_promo_visual_{slugify(Path(image_path).stem)}", border=True):
                    st.image(image_path, use_container_width=True)


def render_categories(categories: list[dict[str, Any]]) -> None:
    """Render category cards with medium-sized category photography."""
    valid_categories: list[dict[str, Any]] = []
    seen: set[str] = set()
    for category in categories:
        name = str(category.get("name", "")).strip()
        key = name.casefold()
        if not name or key not in HOME_CATEGORY_NAMES or key in seen:
            continue
        if category.get("is_active") is False:
            continue
        seen.add(key)
        valid_categories.append(category)

    if not valid_categories:
        st.warning(
            "No valid categories were returned by FastAPI. "
            "Check GET /api/v1/catalog/categories."
        )
        return

    columns_per_row = 4
    for start in range(0, len(valid_categories), columns_per_row):
        cols = st.columns(columns_per_row, gap="medium")
        for col, cat in zip(cols, valid_categories[start:start + columns_per_row]):
            name = str(cat.get("name", "Category")).strip()
            cid = cat.get("id")
            with col:
                with st.container(key=f"fm_category_card_{slugify(name)}_{start}", border=True):
                    img = category_image(cat)
                    if img:
                        try:
                            st.image(img, use_container_width=True)
                        except Exception:
                            st.markdown(
                                "<div style='height:178px;display:flex;align-items:center;justify-content:center;"
                                "background:#fff8e8;color:#111;font-size:42px;border-radius:6px'>🛍️</div>",
                                unsafe_allow_html=True,
                            )
                    else:
                        st.markdown(
                            "<div style='height:178px;display:flex;align-items:center;justify-content:center;"
                            "background:#fff8e8;color:#111;font-size:42px;border-radius:6px'>🛍️</div>",
                            unsafe_allow_html=True,
                        )
                    st.markdown(
                        f"<div class='fm-category-name'>{html.escape(name)}</div>",
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        "Explore category",
                        key=f"cat_{cid}_{start}_{slugify(name)}",
                        use_container_width=True,
                    ):
                        st.session_state.fm_category_id = cid
                        st.session_state.fm_category_name = name
                        st.session_state.fm_search = ""
                        st.session_state.fm_page = "Shop"
                        st.rerun()


def render_products(products: list[dict[str, Any]]) -> None:
    if not products:
        st.warning("The catalogue API returned zero visible products. Check the API response and product publication status in MySQL.")
        with st.expander("Catalogue diagnostics", expanded=True):
            st.code(f"GET {api_url('catalog/products')}\\nAPI: {API_ROOT}\\nLast error: {st.session_state.fm_last_error or 'No HTTP error'}")
            if st.button("Test catalogue API now", key="catalog_test"):
                cdata, cerr, cstatus = api("GET", "catalog/products", params={"page": 1, "page_size": 5})
                st.write({"http_status": cstatus, "error": cerr, "response_keys": list(dct(cdata).keys()) if isinstance(cdata, dict) else type(cdata).__name__, "product_count": len(rows(cdata, "products", "items"))})
                if cdata is not None:
                    st.json(cdata)
        return
    for start in range(0, len(products), 4):
        cols = st.columns(4, gap="medium")
        for col, product in zip(cols, products[start:start+4]):
            pid = pick(product, "id", "product_id"); name = str(pick(product, "name", default="Product")); img = product_image(product)
            price = pick(product, "price", default=0); old = pick(product, "compare_at_price")
            with col:
                st.markdown('<div class="fm-product">', unsafe_allow_html=True)
                if img:
                    try: st.image(img, use_container_width=True)
                    except Exception: st.markdown("<div style='height:170px;background:#f3f4f6;color:#111;text-align:center;padding-top:65px'>FINMARKET</div>", unsafe_allow_html=True)
                else: st.markdown("<div style='height:170px;background:#f3f4f6;color:#111;text-align:center;padding-top:65px'>FINMARKET</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='fm-product-name'>{html.escape(name[:90])}</div><div class='fm-price'>{money(price, str(product.get('currency') or 'INR'))}</div>", unsafe_allow_html=True)
                if old: st.markdown(f"<span class='fm-old'>{money(old)}</span>", unsafe_allow_html=True)
                stock = safe_int(product.get("stock_quantity"), 0)
                st.caption("In stock" if stock > 0 else "Availability checked at checkout")
                qty = st.number_input("Quantity", min_value=1, max_value=20, value=1, key=f"qty_{pid}", label_visibility="collapsed")
                if st.button("View details", key=f"view_{pid}", use_container_width=True):
                    st.session_state.fm_selected_product = product
                    st.session_state.fm_page = "Product"
                    st.rerun()
                if st.button("＋ Add to Cart", key=f"add_{pid}", type="primary", use_container_width=True):
                    if mutate_cart("add", product_id=pid, quantity=int(qty)):
                        st.success(f"Added {name} to your cart."); st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)




def find_marketplace_hero_art() -> str | None:
    """Locate the supplied marketplace collage used on the home hero banner."""
    candidates = [
        "finmarket-home-hero.png",
        "finmarket-home-hero.webp",
        "finmarket-home-hero.jpg",
        "finmarket-marketplace-banner.webp",
        "finmarket-marketplace-banner.png",
        "finmarket-marketplace-banner.jpg",
        "marketplace-banner.webp",
        "marketplace-banner.png",
        "marketplace-banner.jpg",
    ]
    # First check beside the Streamlit entry-point so the supplied hero asset
    # works even when the app is launched from a different working directory.
    for filename in candidates:
        beside_app = APP_DIR / filename
        if beside_app.is_file():
            return str(beside_app)
        found = find_finmarket_visual_asset(filename)
        if found:
            return found
    return None



def home_page() -> None:
    """FINMARKET home page with marketplace collage integrated into the hero banner."""
    banner_art = find_marketplace_hero_art()

    with st.container(key="fm_home_hero"):
        hero_left, hero_right = st.columns([2.25, 1], vertical_alignment="center", gap="large")
        with hero_left:
            st.markdown(
                """
                <div class='fm-hero fm-hero-copy'>
                    <span class='fm-chip'>FINMARKET KART ESSENTIALS</span>
                    <h1>Shop everything you need.</h1>
                    <p>Your everyday marketplace for groceries, fresh produce, household essentials, personal care, mobile gadgets, electronics and more.</p>
                    <span class='fm-chip'>Fast shopping</span>
                    <span class='fm-chip'>Secure Razorpay checkout</span>
                    <span class='fm-chip'>Track your orders</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with hero_right:
            if banner_art:
                st.image(banner_art, use_container_width=True)
            else:
                st.markdown(
                    "<div class='fm-hero-art-placeholder'>🛒<br><b>FINMARKET</b><br>"
                    "<span>Groceries · Gadgets · Electronics · Sports</span></div>",
                    unsafe_allow_html=True,
                )

    categories = fetch_categories()

    st.markdown(
        "<h2 class='fm-home-section-title'>Explore FINMARKET Essentials</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<h3 class='fm-home-subtitle'>Categories</h3>",
        unsafe_allow_html=True,
    )
    render_categories(categories)
    render_home_promotions()


def shop_page() -> None:
    st.markdown(
        f"## Shop · {html.escape(str(st.session_state.fm_category_name))}"
    )

    # Only genuine department categories.
    
    valid_categories = {
        "bakery",
        "beverages",
        "cooking essentials",
        "dairy & eggs",
        "fruits & vegetables",
        "household essentials",
        "personal care",
        "pulses & lentils",
        "rice & grains",
        "snacks & munchies",

        # NEW CATEGORIES
        "mobile gadgets",
        "accessories",
        "electronics",
        "sports",
        "clothes & fashion",
        }

    cats = fetch_categories()

    # Remove incorrectly created product-name category records.
    cats = [
        c for c in cats
        if str(c.get("name") or "").strip().casefold()
        in valid_categories
        and c.get("is_active", True) not in (False, 0, "0")
    ]

    # Build department dropdown using real category IDs.
    labels = {"All departments": None}

    for category in cats:
        category_name = str(category.get("name") or "").strip()
        category_id = category.get("id")

        if category_id is not None:
            labels[category_name] = category_id

    keys = list(labels)

    current_category = st.session_state.get(
        "fm_category_name", "All departments"
    )

    default = (
        current_category
        if current_category in labels
        else "All departments"
    )

    a, b = st.columns([2, 1])

    with a:
        selected = st.selectbox(
            "Department",
            keys,
            index=keys.index(default),
            key="shop_department_select",
        )

    with b:
        sort = st.selectbox(
            "Sort by",
            [
                "Newest",
                "Price: low to high",
                "Price: high to low",
                "Name",
            ],
            key="shop_sort_select",
        )

    selected_category_id = labels[selected]

    st.session_state.fm_category_id = selected_category_id
    st.session_state.fm_category_name = selected

    sort_key, direction = {
        "Newest": ("created_at", "desc"),
        "Price: low to high": ("price", "asc"),
        "Price: high to low": ("price", "desc"),
        "Name": ("name", "asc"),
    }[sort]

    # Fetch products belonging to the selected category.
    products = fetch_products(
        search=st.session_state.get("fm_search", ""),
        category_id=selected_category_id,
        sort=sort_key,
        order=direction,
    )

    # Defensive client-side category filtering.
    if selected_category_id is not None:
        products = [
            product for product in products
            if str(product.get("category_id"))
            == str(selected_category_id)
        ]

    st.caption(f"{len(products)} products")

    if products:
        render_products(products)
    else:
        st.info(
            f"No products are currently available under {selected}."
        )

def product_page() -> None:
    product = dct(st.session_state.fm_selected_product)

    if not product:
        st.info("Choose a product from the Shop page.")
        if st.button("Back to shop"):
            st.session_state.fm_page = "Shop"
            st.rerun()
        return

    if st.button("← Back to shopping"):
        st.session_state.fm_page = "Shop"
        st.rerun()

    name = str(pick(product, "name", default="Product"))

    # Get the full product description from the catalogue JSON
    description = str(
        pick(
            product,
            "description",
            "short_description",
            default=""
        ) or ""
    ).strip()

    left, right = st.columns([1, 1.4], gap="large")

    with left:
        img = product_image(product)
        if img:
            st.image(img, use_container_width=True)

    with right:
        st.markdown(f"## {html.escape(name)}")

        st.markdown(
            f"<div class='fm-price'>{money(product.get('price', 0), str(product.get('currency') or 'INR'))}</div>",
            unsafe_allow_html=True
        )

        if product.get("compare_at_price"):
            st.caption(
                f"MRP: {money(product.get('compare_at_price'))}"
            )

        # Display the product description for every product
        st.markdown("### Product Description")

        if description:
            st.write(description)
        else:
            st.info("Product description is not available.")

        st.caption(
            f"SKU: {product.get('sku', '—')} · "
            f"Category: {product.get('category_name', '—')}"
        )

        stock = safe_int(product.get("stock_quantity"), 0)

        if stock > 0:
            st.success(f"In stock: {stock}")
        else:
            st.info("Stock availability is confirmed at checkout.")

        qty = st.number_input(
            "Quantity",
            min_value=1,
            max_value=20,
            value=1,
            key=f"detail_qty_{product.get('id')}"
        )

        if st.button(
            "Add to Cart",
            type="primary",
            use_container_width=True
        ):
            if mutate_cart(
                "add",
                product_id=product.get("id"),
                quantity=int(qty)
            ):
                st.success("Product added to cart.")
                st.session_state.fm_page = "Cart"
                st.rerun()


def cart_page() -> None:
    st.markdown(f"## {tr('Your Shopping Cart')}")
    cart = get_cart(); items = cart_items(cart)
    if not items:
        st.info("Your cart is empty.")
        if st.button("Continue shopping", type="primary"): st.session_state.fm_page="Shop"; st.rerun()
        return
    subtotal = pick(cart, "subtotal", default=0)
    for item in items:
        p = dct(item.get("product")); name = str(pick(p,"name",default=f"Product {item.get('product_id')}")); img=product_image(p)
        iid=item.get("id"); qty=safe_int(item.get("quantity"),1); c=st.columns([1,4,1,1,1])
        with c[0]:
            if img: st.image(img, width=95)
        with c[1]: st.markdown(f"**{html.escape(name)}**"); st.caption(f"SKU: {p.get('sku','—')}")
        with c[2]:
            newq=st.number_input("Qty",1,99,qty,key=f"cartqty_{iid}")
            if newq != qty and st.button("Update",key=f"update_{iid}"):
                if mutate_cart("update",item_id=iid,quantity=int(newq)): st.rerun()
        with c[3]: st.markdown(f"**{money(item.get('line_total',0))}**")
        with c[4]:
            if st.button("Remove",key=f"remove_{iid}"):
                if mutate_cart("remove",item_id=iid): st.rerun()
        st.divider()
    st.markdown(f"### Subtotal: {money(subtotal)}")
    if logged_in():
        if st.button("Proceed to checkout",type="primary",use_container_width=True): st.session_state.fm_page="Checkout"; st.rerun()
    else:
        st.info("Guest cart is supported. Sign in to checkout and attach orders to your account.")
        if st.button("Sign in to checkout",type="primary"): st.session_state.fm_page="Sign in"; st.rerun()

def load_addresses() -> list[dict[str,Any]]:
    data,err,_=api("GET","account/addresses",auth=True)
    if err: st.error(f"Could not load addresses: {err}"); return []
    return rows(data,"items","addresses")


def checkout_page() -> None:
    st.markdown(f"## {tr('Secure Checkout')}")

    if not logged_in():
        st.warning("Sign in before checkout.")
        sign_in_panel()
        return

    if not ensure_customer():
        return

    cart = get_cart()
    items = cart_items(cart)

    if not items:
        st.info("Your cart is empty.")
        return

    addresses = load_addresses()
    address_id = None

    # --------------------------------------------------------
    # DELIVERY ADDRESS SELECTION
    # --------------------------------------------------------

    if addresses:
        opts = {
            (
                f"{a.get('recipient_name', 'Customer')} · "
                f"{a.get('address_line1', '')} · "
                f"{a.get('city', '')} · "
                f"{a.get('postal_code', '')}"
            ): safe_int(a.get("id"))
            for a in addresses
        }

        choice = st.selectbox(
            "Choose delivery address",
            list(opts),
            key="checkout_address_select"
        )

        address_id = opts[choice]

    # --------------------------------------------------------
    # ADD NEW DELIVERY ADDRESS
    # --------------------------------------------------------

    with st.expander(
        "➕ Add a New Delivery Address",
        expanded=not bool(addresses)
    ):

        st.markdown("""
        <style>
        .address-intro {
            color: #333333 !important;
            font-size: 14px !important;
            font-weight: 500 !important;
            margin-bottom: 16px !important;
        }

        .address-field-label {
            color: #222222 !important;
            font-weight: 700 !important;
            font-size: 14px !important;
            margin-bottom: 5px !important;
        }

        div[data-testid="stTextInput"] input::placeholder {
            color: #666666 !important;
            -webkit-text-fill-color: #666666 !important;
            opacity: 1 !important;
        }

        div[data-testid="stTextInput"] input {
            color: #222222 !important;
            -webkit-text-fill-color: #222222 !important;
            background-color: #FFFFFF !important;
            border: 1px solid #999999 !important;
        }

        div[data-testid="stTextInput"] input:focus {
            border: 1px solid #555555 !important;
            box-shadow: 0 0 0 1px #777777 !important;
        }

        .address-help {
            color: #555555 !important;
            font-size: 13px !important;
            font-weight: 500 !important;
        }

        div[data-testid="stCaptionContainer"] p {
            color: #555555 !important;
        }

        div[data-testid="stForm"] {
            border-color: #BBBBBB !important;
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="address-intro">
            Enter your complete delivery address.
            Fields marked * are mandatory.
        </div>
        """, unsafe_allow_html=True)

        with st.form(key="checkout_delivery_address_form_v2"):

            st.markdown(
                '<p class="address-field-label">1. Recipient Details</p>',
                unsafe_allow_html=True
            )

            st.markdown(
                '<p class="address-field-label">Full Name *</p>',
                unsafe_allow_html=True
            )

            name = st.text_input(
                "Full Name",
                placeholder="Enter your full name",
                label_visibility="collapsed",
                key="delivery_recipient_name"
            )

            st.markdown(
                '<p class="address-field-label">Mobile Number *</p>',
                unsafe_allow_html=True
            )

            phone = st.text_input(
                "Mobile Number",
                placeholder="Enter 10-digit mobile number",
                label_visibility="collapsed",
                key="delivery_phone"
            )

            st.divider()

            st.markdown(
                '<p class="address-field-label">2. Address Details</p>',
                unsafe_allow_html=True
            )

            st.markdown(
                '<p class="address-field-label">House / Flat / Building Number *</p>',
                unsafe_allow_html=True
            )

            line1 = st.text_input(
                "House / Flat / Building Number",
                placeholder="Example: Flat 302, Sai Residency",
                label_visibility="collapsed",
                key="delivery_address_line1"
            )

            st.markdown(
                '<p class="address-field-label">Street / Area / Locality</p>',
                unsafe_allow_html=True
            )

            line2 = st.text_input(
                "Street / Area / Locality",
                placeholder="Example: Madhapur, Hitech City",
                label_visibility="collapsed",
                key="delivery_address_line2"
            )

            st.markdown(
                '<p class="address-field-label">Nearby Landmark</p>',
                unsafe_allow_html=True
            )

            landmark = st.text_input(
                "Nearby Landmark",
                placeholder="Example: Near Metro Station",
                label_visibility="collapsed",
                key="delivery_landmark"
            )

            st.divider()

            st.markdown(
                '<p class="address-field-label">3. City and Location Details</p>',
                unsafe_allow_html=True
            )

            col1, col2 = st.columns(2)

            with col1:

                st.markdown(
                    '<p class="address-field-label">City *</p>',
                    unsafe_allow_html=True
                )

                city = st.text_input(
                    "City",
                    placeholder="Example: Hyderabad",
                    label_visibility="collapsed",
                    key="delivery_city"
                )

                st.markdown(
                    '<p class="address-field-label">State *</p>',
                    unsafe_allow_html=True
                )

                state = st.text_input(
                    "State",
                    placeholder="Example: Telangana",
                    label_visibility="collapsed",
                    key="delivery_state"
                )

            with col2:

                st.markdown(
                    '<p class="address-field-label">PIN Code *</p>',
                    unsafe_allow_html=True
                )

                pin = st.text_input(
                    "PIN Code",
                    placeholder="Enter 6-digit PIN code",
                    label_visibility="collapsed",
                    key="delivery_pin"
                )

                st.markdown(
                    '<p class="address-field-label">Country *</p>',
                    unsafe_allow_html=True
                )

                country = st.text_input(
                    "Country",
                    value="India",
                    label_visibility="collapsed",
                    key="delivery_country"
                )

            st.divider()

            st.markdown(
                '<p class="address-help">* Mandatory fields</p>',
                unsafe_allow_html=True
            )

            save = st.form_submit_button(
                "Save Delivery Address",
                type="primary",
                use_container_width=True
            )

            if save:

                name = name.strip()
                phone = phone.strip()
                line1 = line1.strip()
                line2 = line2.strip()
                landmark = landmark.strip()
                city = city.strip()
                state = state.strip()
                pin = pin.strip()
                country = country.strip()

                if not all([
                    name,
                    phone,
                    line1,
                    city,
                    state,
                    pin,
                    country
                ]):

                    st.error(
                        "Please complete all mandatory address fields."
                    )

                elif not phone.isdigit() or len(phone) != 10:

                    st.error(
                        "Enter a valid 10-digit mobile number."
                    )

                elif not pin.isdigit() or len(pin) != 6:

                    st.error(
                        "Enter a valid 6-digit PIN code."
                    )

                else:

                    address_data, address_error, _ = api(
                        "POST",
                        "account/addresses",
                        auth=True,
                        body={
                            "label": "Home",
                            "recipient_name": name,
                            "phone": phone,
                            "address_line1": line1,
                            "address_line2": line2,
                            "landmark": landmark,
                            "city": city,
                            "state": state,
                            "postal_code": pin,
                            "country": country,
                            "is_default": not bool(addresses)
                        }
                    )

                    if address_error:

                        st.error(
                            f"Could not save address: {address_error}"
                        )

                    else:

                        st.success(
                            "Delivery address saved successfully!"
                        )

                        st.rerun()

    # --------------------------------------------------------
    # ORDER SUMMARY — rendered exactly once
    # --------------------------------------------------------

    st.markdown(f"### {tr('Order Summary')}")

    for item in items:
        product = dct(item.get("product"))
        st.write(
            f"{pick(product, 'name', default='Product')} "
            f"× {item.get('quantity', 1)} — "
            f"{money(item.get('line_total', 0))}"
        )

    subtotal = cart.get("subtotal", 0)
    st.markdown(f"**Subtotal: {money(subtotal)}**")

    # --------------------------------------------------------
    # PAYMENT METHOD — one selector, two selectable methods
    # COD is selected by default; Razorpay remains selectable.
    # --------------------------------------------------------

    st.markdown(f"### {tr('Select Payment Method')}")

    if st.session_state.get("fm_checkout_method") not in ("cod", "razorpay"):
        st.session_state.fm_checkout_method = "cod"
    pay_cod, pay_razorpay = st.columns(2, gap="medium")
    with pay_cod:
        st.markdown("<div class='fm-panel' style='min-height:94px'>💵 <b>Cash on Delivery</b><br><small>Pay when your order arrives</small></div>", unsafe_allow_html=True)
        if st.button(
            ("✓  " if st.session_state.fm_checkout_method == "cod" else "　") + tr("Cash on Delivery"),
            key="checkout_tab_cod", use_container_width=True,
            type="primary" if st.session_state.fm_checkout_method == "cod" else "secondary",
        ):
            st.session_state.fm_checkout_method = "cod"
            st.rerun()
    with pay_razorpay:
        st.markdown("<div class='fm-panel' style='min-height:94px'>🔒 <b>Razorpay</b><br><small>UPI · Credit/Debit Cards · Netbanking</small></div>", unsafe_allow_html=True)
        if st.button(
            ("✓  " if st.session_state.fm_checkout_method == "razorpay" else "　") + "Razorpay (UPI / Cards / Netbanking)",
            key="checkout_tab_razorpay", use_container_width=True,
            type="primary" if st.session_state.fm_checkout_method == "razorpay" else "secondary",
        ):
            st.session_state.fm_checkout_method = "razorpay"
            st.rerun()
    method = st.session_state.fm_checkout_method

    notes = st.text_area(
        "Delivery instructions (optional)",
        key="checkout_delivery_notes",
    )

    button_label = (
        "Place Order – Cash on Delivery"
        if method == "cod"
        else "Place Order and Continue to Razorpay"
    )

    if st.button(
        button_label,
        type="primary",
        use_container_width=True,
        disabled=address_id is None,
        key="checkout_place_order",
    ):
        with st.spinner("Creating your order…"):
            order_response, order_error, _ = api(
                "POST",
                "orders/checkout",
                auth=True,
                body={
                    "shipping_address_id": address_id,
                    "payment_method": method,
                    "customer_notes": notes.strip() or None,
                },
            )

        if order_error:
            st.error(f"Order creation failed: {order_error}")
            return

        order = dct(order_response)
        order_id = safe_int(order.get("id"))

        if not order_id:
            st.error("Order was created, but the order ID is missing.")
            return

        st.session_state.fm_order_id = order_id

        if method == "cod":
            order_number = order.get("order_number", order_id)
            st.session_state.fm_order_confirmation = {
                "order_id": order_id,
                "order_number": str(order_number),
                "payment_method": "Cash on Delivery",
                "total": subtotal,
            }
            st.session_state.fm_payment_message = (
                f"Order {order_number} placed successfully using Cash on Delivery."
            )
            st.session_state.fm_page = "Order Success"
            st.rerun()
            return

        # ----------------------------------------------------
        # RAZORPAY — runs only when Razorpay is selected
        # ----------------------------------------------------

        with st.spinner("Connecting to Razorpay…"):
            payment_response, payment_error, _ = api(
                "POST",
                f"payments/orders/{order_id}/initiate",
                auth=True,
                body={"idempotency_key": uuid.uuid4().hex},
            )

        if payment_error:
            st.error(
                "Razorpay initiation failed: "
                f"{payment_error}. Your order exists, but payment is not complete."
            )
            return

        payment = dct(payment_response).get(
            "payment",
            dct(payment_response),
        )

        razorpay_key = pick(payment, "razorpay_key_id")
        razorpay_order_id = pick(payment, "razorpay_order_id")
        amount_paise = pick(payment, "amount_paise")
        currency = pick(payment, "currency", default="INR")

        if not all([razorpay_key, razorpay_order_id, amount_paise]):
            st.error(
                "The backend payment response is missing the Razorpay key, "
                "order ID, or amount. Check POST "
                "/payments/orders/{order_id}/initiate."
            )
            return

        checkout_html = f'''<!doctype html>
<html>
<head>
    <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
</head>
<body style="font:14px Arial;padding:15px;margin:0;">
    <button id="pay"
        style="background:#5b67e8;color:white;border:0;padding:13px 22px;border-radius:8px;font-weight:bold;cursor:pointer">
        Pay securely with Razorpay
    </button>
    <p id="status">Order {order_id} · Amount {html.escape(str(amount_paise))} paise</p>
    <script>
        const options = {{
            key: {json.dumps(str(razorpay_key))},
            amount: {json.dumps(str(amount_paise))},
            currency: {json.dumps(str(currency))},
            name: "FINMARKET Kart Essentials",
            description: "Order payment #{order_id}",
            order_id: {json.dumps(str(razorpay_order_id))},
            handler: async function(response) {{
                document.getElementById("status").textContent = "Verifying payment securely…";
                try {{
                    const result = await fetch(
                        {json.dumps(api_url(f"payments/orders/{order_id}/verify"))},
                        {{
                            method: "POST",
                            headers: {{
                                "Content-Type": "application/json",
                                "Authorization": "Bearer " + {json.dumps(token() or "")}
                            }},
                            body: JSON.stringify({{
                                razorpay_order_id: response.razorpay_order_id,
                                razorpay_payment_id: response.razorpay_payment_id,
                                razorpay_signature: response.razorpay_signature
                            }})
                        }}
                    );
                    const data = await result.json();
                    if (!result.ok) throw new Error(data.detail || "Verification failed");
                    document.getElementById("status").textContent =
                        "Payment verified. Returning to FINMARKET…";
                    window.parent.location.href =
                        window.parent.location.origin +
                        window.parent.location.pathname +
                        "?payment_verified={order_id}";
                }} catch (error) {{
                    document.getElementById("status").textContent =
                        "Payment verification failed: " + error.message;
                }}
            }},
            modal: {{
                ondismiss: function() {{
                    document.getElementById("status").textContent =
                        "Checkout closed. Order remains unpaid; you can retry from Orders.";
                }}
            }},
            theme: {{color: "#6758e8"}}
        }};

        const razorpayCheckout = new Razorpay(options);
        document.getElementById("pay").onclick = () => razorpayCheckout.open();
    </script>
</body>
</html>'''

        components.html(
            checkout_html,
            height=300,
            scrolling=True,
        )
        st.info(
            "Your order remains pending payment until Razorpay verification succeeds."
        )


def orders_page() -> None:
    st.markdown("## Your Orders")
    if not logged_in(): sign_in_panel(); return
    if not ensure_customer(): return
    data,err,_=api("GET","orders",auth=True,params={"page":1,"page_size":50})
    if err: st.error(f"Could not load orders: {err}"); return
    orders=rows(data,"items","orders")
    if not orders: st.info("You have not placed any orders yet."); return
    for o in orders:
        number=pick(o,"order_number","id"); total=pick(o,"total_amount","grand_total",default=0); status=str(o.get("status","pending")); payment=str(o.get("payment_status","pending"))
        with st.expander(f"{number} · {status.upper()} · {money(total)} · Payment {payment}"):
            st.write("Placed:",o.get("created_at","—")); st.write("Payment method:",o.get("payment_method","—"));
            for item in rows(o,"items"):
                st.write(f"{item.get('product_name','Product')} × {item.get('quantity',1)} — {money(item.get('line_total',0))}")
            if o.get("payment_method")=="razorpay" and payment!="paid": st.warning("Payment is not confirmed yet. Contact support if the amount was debited.")

def account_page() -> None:
    st.markdown("## Your FINMARKET Account")
    user=current_user()
    if not user: sign_in_panel(); return
    a,b=st.columns([1,3])
    with a:
        pic=user.get("picture")
        if isinstance(pic,str) and pic.startswith("https://"): st.image(pic,width=110)
        else: st.markdown("## 👤")
    with b:
        st.markdown(f"### {html.escape(str(user.get('name') or 'Customer'))}"); st.write(user.get("email") or "Verified identity"); st.success("Signed in through ZITADEL")
        if st.button("Sign out"): logout()
    ensure_customer()
    addresses=load_addresses()
    st.markdown("### Saved delivery addresses")
    if addresses:
        for a in addresses: st.markdown(f"**{a.get('recipient_name','')}** · {a.get('address_line1','')}, {a.get('city','')} {a.get('postal_code','')}")
    else: st.caption("No saved addresses yet.")


def order_success_page() -> None:
    """Show a persistent, animated order confirmation after COD checkout."""
    confirmation = dct(st.session_state.get("fm_order_confirmation"))
    if not confirmation:
        st.info("No recent order confirmation is available.")
        if st.button("Go to Orders", type="primary"):
            st.session_state.fm_page = "Orders"
            st.rerun()
        return

    st.markdown("""
    <style>
    .fm-success-wrap{max-width:720px;margin:32px auto;background:#fff;border:1px solid #d5d9d9;
      border-radius:14px;padding:34px 24px;text-align:center;box-shadow:0 8px 28px #00000012}
    .fm-check-circle{width:104px;height:104px;margin:0 auto 18px;border-radius:50%;background:#e8f8ef;
      display:flex;align-items:center;justify-content:center;animation:fm-pop .55s cubic-bezier(.2,.8,.2,1) both}
    .fm-check{font-size:62px;line-height:1;color:#159447;animation:fm-tick .45s .25s ease both}
    .fm-success-title{font-size:30px;font-weight:850;color:#147a3d;margin:8px 0}
    .fm-success-copy{color:#424b57;font-size:15px}
    @keyframes fm-pop{0%{transform:scale(.25);opacity:0}75%{transform:scale(1.12);opacity:1}100%{transform:scale(1)}}
    @keyframes fm-tick{0%{transform:scale(.2) rotate(-25deg);opacity:0}100%{transform:scale(1) rotate(0);opacity:1}}
    </style>
    <div class="fm-success-wrap">
      <div class="fm-check-circle"><div class="fm-check">✓</div></div>
      <div class="fm-success-title">Order placed successfully!</div>
      <p class="fm-success-copy">Thank you for shopping with FINMARKET Kart Essentials.</p>
      <p class="fm-success-copy"><b>Cash on Delivery</b> selected · Your order is confirmed.</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(f"### Order: {html.escape(str(confirmation.get('order_number', confirmation.get('order_id', '—'))))}")
    st.markdown(f"**Order total: {money(confirmation.get('total', 0))}**")
    st.success("A confirmation has been recorded. You can track its status in Your Orders.")
    left, right = st.columns(2)
    with left:
        if st.button("View My Orders", type="primary", use_container_width=True):
            st.session_state.fm_page = "Orders"
            st.rerun()
    with right:
        if st.button("Continue Shopping", use_container_width=True):
            st.session_state.fm_page = "Shop"
            st.rerun()


def settings_page() -> None:
    """Session preferences, ZITADEL account summary, and address creation."""
    st.markdown(f"## {tr('Settings & Preferences')}")
    st.caption("Preferences apply to this Streamlit browser session.")

    pref_col1, pref_col2 = st.columns(2)
    with pref_col1:
        language_options = ["English", "Hindi", "Telugu"]
        current_language = st.session_state.get("fm_language", "English")
        language_index = language_options.index(current_language) if current_language in language_options else 0
        language = st.selectbox(
            tr("Language"), language_options, index=language_index,
            key="settings_language_select",
        )
        if language != st.session_state.get("fm_language"):
            st.session_state.fm_language = language
            st.rerun()
    with pref_col2:
        theme_options = ["Light", "Dark"]
        current_theme = st.session_state.get("fm_theme", "Light")
        theme_index = theme_options.index(current_theme) if current_theme in theme_options else 0
        theme = st.selectbox(
            tr("Theme"), theme_options, index=theme_index,
            key="settings_theme_select",
        )
        if theme != st.session_state.get("fm_theme"):
            st.session_state.fm_theme = theme
            st.rerun()

    st.divider()
    st.markdown(f"### {tr('Account Details')}")
    user = current_user()
    if user:
        account_left, account_right = st.columns([1, 3])
        with account_left:
            if user.get("picture"):
                st.image(user["picture"], width=90)
            else:
                st.markdown("## 👤")
        with account_right:
            st.write(f"**{html.escape(str(user.get('name') or 'Customer'))}**")
            st.write(user.get("email") or "Verified ZITADEL account")
            st.caption("Identity and sign-in credentials are managed by ZITADEL.")
            if st.button("Open Account Page", key="settings_account_page"):
                st.session_state.fm_page = "Account"
                st.rerun()
            if st.button("Sign Out", key="settings_sign_out"):
                logout()
    else:
        st.info("You are browsing as a guest. Sign in to manage your account and saved addresses.")
        if st.button("Sign In", key="settings_sign_in"):
            st.session_state.fm_page = "Sign in"
            st.rerun()

    st.divider()
    st.markdown(f"### {tr('Saved Delivery Addresses')}")
    if not logged_in():
        st.info("Sign in to view and add saved delivery addresses.")
        return
    if not ensure_customer():
        return
    addresses = load_addresses()
    if addresses:
        for address in addresses:
            label = "Default address" if address.get("is_default") else "Saved address"
            with st.container(border=True):
                st.markdown(f"**{html.escape(str(address.get('recipient_name') or 'Customer'))}** · {label}")
                st.write(", ".join(str(v) for v in [address.get("address_line1"), address.get("address_line2"), address.get("landmark"), address.get("city"), address.get("state"), address.get("postal_code"), address.get("country")] if v))
                st.caption(str(address.get("phone") or ""))
    else:
        st.info("No saved delivery addresses yet.")

    with st.expander(tr("Add a New Delivery Address"), expanded=False):
        with st.form("settings_add_address_form", clear_on_submit=True):
            name = st.text_input("Recipient name *")
            phone = st.text_input("10-digit mobile number *", max_chars=10)
            line1 = st.text_input("House / Flat / Building *")
            line2 = st.text_input("Street / Area / Locality")
            landmark = st.text_input("Landmark")
            city = st.text_input("City *")
            state = st.text_input("State *")
            pin = st.text_input("6-digit PIN code *", max_chars=6)
            country = st.text_input("Country *", value="India")
            # Automatically make the first saved address the default.
            # The optional checkbox has been removed from the form.
            make_default = not bool(addresses)
            submitted = st.form_submit_button("Save Address", type="primary", use_container_width=True)
        if submitted:
            values = [name.strip(), phone.strip(), line1.strip(), city.strip(), state.strip(), pin.strip(), country.strip()]
            if not all(values):
                st.error("Complete all mandatory address fields.")
            elif not phone.strip().isdigit() or len(phone.strip()) != 10:
                st.error("Enter a valid 10-digit mobile number.")
            elif not pin.strip().isdigit() or len(pin.strip()) != 6:
                st.error("Enter a valid 6-digit PIN code.")
            else:
                _, address_error, _ = api(
                    "POST", "account/addresses", auth=True,
                    body={
                        "label": "Home", "recipient_name": name.strip(), "phone": phone.strip(),
                        "address_line1": line1.strip(), "address_line2": line2.strip(),
                        "landmark": landmark.strip(), "city": city.strip(), "state": state.strip(),
                        "postal_code": pin.strip(), "country": country.strip(),
                        "is_default": bool(make_default),
                    },
                )
                if address_error:
                    st.error(f"Could not save address: {address_error}")
                else:
                    st.success("Delivery address saved successfully.")
                    st.rerun()
    st.caption("Existing address editing/deletion is not enabled here because the current app source does not define verified update/delete API routes. Adding and viewing saved addresses uses the existing FastAPI address API.")

def signin_page() -> None:
    if logged_in():
        u=current_user(); st.success(f"Signed in as {u.get('email') or u.get('name')}")
        ensure_customer()
        if st.button("Sign out"): logout()
    else: sign_in_panel()

# ----------------------------- navigation / app ----------------------------
def sidebar() -> None:
    user=current_user()
    with st.sidebar:
        logo=local_image(LOGO_DIR,["finmarket-kart-essentials-logo-white.jpg","finmarket-kart-essentials-logo.png","finmarket-logo.png"])
        if logo: st.image(logo,use_container_width=True)
        else: st.markdown("## FINMARKET")
        st.markdown('<div class="fm-spectrum"></div>',unsafe_allow_html=True)
        st.caption(f"Hello, {user.get('name') if user else 'Guest'}")
        for label in ["Home", "Shop", "Cart", "Checkout", "Orders", "Account", "Settings", "Sign in"]:
            if st.button(tr(label), key=f"nav_{label}", use_container_width=True,
                         type="primary" if st.session_state.fm_page == label else "secondary"):
                st.session_state.fm_page = label
                st.rerun()
        st.divider()
        
        
        if st.button("↻ Refresh catalogue", use_container_width=True):
            fetch_categories.clear()

            st.session_state.fm_categories = []
            st.session_state.fm_products = []
            st.session_state.fm_last_error = ""

            st.session_state.fm_page = "Home"

            st.rerun()



def main() -> None:
    sidebar(); header()
    # Payment callback URL is only a navigation hint. The actual payment was
    # already verified by FastAPI; read the persisted order status from API.
    try:
        verified=st.query_params.get("payment_verified")
        if verified:
            order,err,_=api("GET",f"orders/{safe_int(verified)}",auth=True)
            if not err and dct(order).get("payment_status")=="paid": st.success("Razorpay payment verified successfully. Your order is paid.")
            elif err: st.warning(f"Could not refresh payment status: {err}")
            else: st.warning("Payment verification is not yet reflected on the order. Refresh in a moment.")
            st.query_params.clear()
    except Exception: pass
    page=st.session_state.fm_page
    if page=="Home": home_page()
    elif page=="Shop": shop_page()
    elif page=="Cart": cart_page()
    elif page=="Product": product_page()
    elif page=="Checkout": checkout_page()
    elif page=="Orders": orders_page()
    elif page=="Account": account_page()
    elif page=="Settings": settings_page()
    elif page=="Order Success": order_success_page()
    elif page=="Sign in": signin_page()
    else: st.session_state.fm_page="Home"; home_page()
    st.markdown('<div class="fm-spectrum"></div>',unsafe_allow_html=True)
    st.caption("© FINMARKET Kart Essentials · FastAPI · MySQL · ZITADEL · Razorpay · SMTP")

if __name__ == "__main__":
    main()
