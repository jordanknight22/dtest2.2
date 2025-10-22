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
PET_RISK_PET_CACHE = {}

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
            "PET_RISK_PET_CACHE": PET_RISK_PET_CACHE,
        }, f)
    print(f"✅ Saved cache to {CACHE_FILE}")

# -------------------------
# Load cache from disk
# -------------------------
def load_static_cache():
    """Load all caches from disk (no DB contact)."""
    global POLICY_MASTER_CACHE, POLICY_HISTORY_CACHE, RISK_CACHE, TRANSACTION_TYPE_CACHE, PET_RISK_PET_CACHE
    if CACHE_FILE.exists():
        with open(CACHE_FILE, "rb") as f:
            data = pickle.load(f)
            POLICY_MASTER_CACHE = data.get("POLICY_MASTER_CACHE", {})
            POLICY_HISTORY_CACHE = data.get("POLICY_HISTORY_CACHE", {})
            RISK_CACHE = data.get("RISK_CACHE", {})
            TRANSACTION_TYPE_CACHE = data.get("TRANSACTION_TYPE_CACHE", {})
            PET_RISK_PET_CACHE = data.get("PET_RISK_PET_CACHE", {})
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
    from base.models import PolicyMaster, PolicyHistory, Risk, TransactionType, PetRiskPet
    print("🔄 Loading static data from database...")

    global POLICY_MASTER_CACHE, POLICY_HISTORY_CACHE, RISK_CACHE, TRANSACTION_TYPE_CACHE, PET_RISK_PET_CACHE

    # Load Tables (flat dict keyed by ID)
    
    POLICY_MASTER_CACHE = {pm.policy_master_id: pm for pm in PolicyMaster.objects.using("default").all()}
    POLICY_HISTORY_CACHE = {ph.policy_history_id: ph for ph in PolicyHistory.objects.using("default").all()}
    RISK_CACHE = {r.risk_id: r for r in Risk.objects.using("default").all()}
    TRANSACTION_TYPE_CACHE = {tt.transaction_type_id: tt for tt in TransactionType.objects.using("default").all()}
    PET_RISK_PET_CACHE = {prp.pet_risk_pet_id: prp for prp in PetRiskPet.objects.using("default").all()}

    print(f"✅ Loaded {len(POLICY_MASTER_CACHE)} PolicyMaster records")
    print(f"✅ Loaded {len(POLICY_HISTORY_CACHE)} PolicyHistory records")
    print(f"✅ Loaded {len(RISK_CACHE)} Risk records")
    print(f"✅ Loaded {len(TRANSACTION_TYPE_CACHE)} TransactionType records")
    print(f"✅ Loaded {len(PET_RISK_PET_CACHE)} PetRiskPet records")
