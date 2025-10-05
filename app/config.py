import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/auto").strip()

APP_SECRET_KEY = os.getenv("APP_SECRET_KEY") or "auto-" + os.urandom(8).hex()
MIN_TRANSFER_SLACK_SECONDS = int(os.getenv("MIN_TRANSFER_SLACK_SECONDS", "300"))
ROUTER_MAX_TRANSFERS = int(os.getenv("ROUTER_MAX_TRANSFERS", "2"))
ROUTER_DEPARTURE_WINDOW_MIN = int(os.getenv("ROUTER_DEPARTURE_WINDOW_MIN", "45"))

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
GTFS_DIR = os.path.join(DATA_DIR, "gtfs")
GTFS_ZIP = os.path.join(GTFS_DIR, "il_gtfs.zip")
LATENESS_STORE = os.path.join(DATA_DIR, "lateness_store.json")

CURLBUS_API_BASE = os.getenv("CURLBUS_API_BASE", "https://curlbus.app/api").strip()
CURLBUS_TIMEOUT = float(os.getenv("CURLBUS_TIMEOUT", "5"))
