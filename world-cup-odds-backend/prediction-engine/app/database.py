"""
Database connection module for Prediction Engine.
Connects to the same PostgreSQL (Supabase) database as NestJS backend.
On Windows, psycopg2 must connect via TCP — not Unix socket.
"""
import os
import re
from urllib.parse import urlparse, parse_qs
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")
DIRECT_URL   = os.getenv("DIRECT_URL", "")

if not DATABASE_URL and not DIRECT_URL:
    raise ValueError("DATABASE_URL or DIRECT_URL environment variable is required")

# Prefer DIRECT_URL (port 5432) for Python engine — avoids pgbouncer pooler quirks.
raw_url = DIRECT_URL if DIRECT_URL else DATABASE_URL

# Strip pgbouncer params that confuse SQLAlchemy
for param in ["?pgbouncer=true", "&pgbouncer=true"]:
    raw_url = raw_url.replace(param, "")

# -----------------------------------------------------------------------
# WINDOWS FIX: psycopg2 on Windows interprets hostnames starting with '@'
# or containing '/' as Unix socket paths, raising "Invalid argument".
# Supabase DIRECT_URL format is:
#   postgresql://postgres.PROJECT:PASS@@HOST:PORT/DB
# Note the double-'@' — one is a literal '@' in the hostname.
# We must parse the URL manually and rebuild it using explicit host/port.
# -----------------------------------------------------------------------
def build_safe_url(url: str) -> str:
    """
    Parse the Supabase connection URL and rebuild it as a plain TCP URL
    that psycopg2 on Windows can handle.
    """
    # Remove scheme prefix temporarily for easier parsing
    scheme_match = re.match(r'^(postgresql\+?\w*|postgres)://', url)
    if not scheme_match:
        return url
    scheme = scheme_match.group(0)
    rest = url[len(scheme):]

    # Split userinfo from host part: rest = "user:pass@host:port/db"
    # Supabase sometimes has '@@' (double-at) — split on LAST '@' before host
    at_idx = rest.rfind('@')
    if at_idx == -1:
        return url

    userinfo = rest[:at_idx]        # "postgres.PROJECT:PASS@"  (may contain @)
    hostpart = rest[at_idx + 1:]    # "HOST:PORT/DB?options"

    # Parse host, port, dbname from hostpart
    host_match = re.match(r'^([^:/]+)(?::(\d+))?(/[^?]*)?(\?.*)?$', hostpart)
    if not host_match:
        return url

    host     = host_match.group(1)
    port     = host_match.group(2) or "5432"
    dbname   = (host_match.group(3) or "/postgres").lstrip("/")
    qs       = host_match.group(4) or ""

    # Rebuild userinfo: replace any remaining '@' in the password part with '%40' to prevent psycopg2 from failing
    if '@' in userinfo:
        userinfo = userinfo.replace('@', '%40')

    # Ensure sslmode=require is present for Supabase
    if "sslmode" not in qs:
        qs = qs + ("&" if qs else "?") + "sslmode=require"

    safe = f"{scheme}{userinfo}@{host}:{port}/{dbname}{qs}"
    return safe


connect_url = build_safe_url(raw_url)

engine = create_engine(
    connect_url,
    pool_pre_ping=True,
    pool_size=5,
    connect_args={"sslmode": "require"},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency for FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
