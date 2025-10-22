# base/static_data.py

import pickle
from pathlib import Path
from datetime import datetime
from django.db.models import Value
from django.db import connection

CACHE_FILE = Path(__file__).resolve().parent / "policy_cache.pkl"

# In-memory caches
POLICY_MASTER_CACHE = {}
POLICY_HISTORY_CACHE = {}
RISK_CACHE = {}
TRANSACTION_TYPE_CACHE = {}

# -------------------------
# Save cache to disk
# -------------------------
def save_static_cache():
    """Save all caches to disk."""
    with open(CACHE_FILE, "wb") as f:
        pickle.dump({
            "POLICY_MASTER_CACHE": POLICY_MASTER_CACHE,
            "POLICY_HISTORY_CACHE": POLICY_HISTORY_CACHE,
            "RISK_CACHE": RISK_CACHE,
            "TRANSACTION_TYPE_CACHE": TRANSACTION_TYPE_CACHE,
        }, f)
    print(f"✅ Saved cache to {CACHE_FILE}")

# -------------------------
# Load cache from disk
# -------------------------
def load_static_cache():
    """Load all caches from disk (no DB contact)."""
    global POLICY_MASTER_CACHE, POLICY_HISTORY_CACHE, RISK_CACHE, TRANSACTION_TYPE_CACHE
    if CACHE_FILE.exists():
        with open(CACHE_FILE, "rb") as f:
            data = pickle.load(f)
            POLICY_MASTER_CACHE = data["POLICY_MASTER_CACHE"]
            POLICY_HISTORY_CACHE = data["POLICY_HISTORY_CACHE"]
            RISK_CACHE = data.get("RISK_CACHE", {})
            TRANSACTION_TYPE_CACHE = data.get("TRANSACTION_TYPE_CACHE", {})
        print(f"✅ Loaded cache from {CACHE_FILE}")
    else:
        print("⚠️ No cache file found — run refresh_static_cache() once first.")

# -------------------------
# Load from DB (initial load)
# -------------------------
def load_static_data():
    """
    Load caches from database.
    All caches are stored in a consistent flat format (dicts keyed by ID)
    so they can be easily converted to DataFrames.
    """
    from base.models import PolicyMaster, PolicyHistory, Risk, TransactionType
    print("🔄 Loading static data from database...")

    global POLICY_MASTER_CACHE, POLICY_HISTORY_CACHE, RISK_CACHE, TRANSACTION_TYPE_CACHE

    # 1️⃣ Load lookup tables (flat dict keyed by ID)
    RISK_CACHE = {r.riskid: r for r in Risk.objects.using("default").all()}
    TRANSACTION_TYPE_CACHE = {t.transactiontypeid: t for t in TransactionType.objects.using("default").all()}

    # 2️⃣ Load all PolicyHistory
    POLICY_HISTORY_CACHE = {}
    for ph in PolicyHistory.objects.using("default").all():
        # attach related objects for convenience
        ph.risk_obj = RISK_CACHE.get(ph.riskid)
        ph.transaction_type_obj = TRANSACTION_TYPE_CACHE.get(ph.transactiontypeid)
        # store as a flat list for each policy master
        POLICY_HISTORY_CACHE.setdefault(ph.policymasterid, []).append(ph)

    # 3️⃣ Load PolicyMaster
    qs_policies = PolicyMaster.objects.using("default").all()
    POLICY_MASTER_CACHE = {}
    for p in qs_policies:
        # attach its histories as a flat list
        p.histories = POLICY_HISTORY_CACHE.get(p.policymasterid, [])
        POLICY_MASTER_CACHE[p.policymasterid] = p

    print(f"✅ Loaded {len(POLICY_MASTER_CACHE)} PolicyMaster records with histories")
    print(f"✅ Loaded {sum(len(v) for v in POLICY_HISTORY_CACHE.values())} PolicyHistory records")
