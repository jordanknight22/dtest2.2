import pickle
from pathlib import Path
from django.db.models import Q
import pandas as pd
from collections import defaultdict
from base.models import (
    PolicyMaster, PolicyHistory, Risk, TransactionType, PetRiskPet,
    DefinedListDetail, PetRisk, PetProposer, Address, SchemeQuoteResultComment, PetRates
)
from .utils import *
import json
import os

# Helper to convert defaultdict -> dict recursively
def convert_defaultdict(d):
    if isinstance(d, defaultdict):
        d = dict(d)
    for k, v in d.items():
        if isinstance(v, defaultdict):
            d[k] = convert_defaultdict(v)
    return d

# Div0 function
def div0(numerator, denominator):
    if isinstance(numerator, pd.Series) or isinstance(denominator, pd.Series):
        # element-wise operation for pandas
        denominator = denominator.replace(0, pd.NA)
        result = numerator / denominator
        return result.fillna(0)
    else:
        # simple scalar case
        try:
            return numerator / denominator if denominator not in (0, None) else 0
        except TypeError:
            return 0


rating_guide =  r'C:\Users\jorda\OneDrive\Desktop\SP Rating Guide v38 - Multiple changes.xlsx'

pet_age_order = ['0','1','2','3','4','5','6','7','8','9','10','11','12','13','14','15','16',
             '17','18','19','20','21','22','23','24–28','29–31','32–34','35–37','38–40',
             '41–43','44–46','47–48','49–54','55–60','61–66','67–72','73–78','79–84',
             '85–90','91–96','97–102','103–108','109–114','115–120','121–126','127–132',
             '133–138','139–144','145–150','151–156','157–162','163–168','169–174','175–180',
             '181–186','187–192','193–204','205–216','217–228','229–240','241+']

ph_age_order = ['0 - 19.999','20 - 29.999','30 - 39.999','40 - 49.999','50 - 59.999','60 - 69.999','70 - 79.999','80 - 89.999','90 and over']

pet_price_order = [ '£0–£75','£76–£150','£151–£300','£301–£600','£601–£1,200','£1,201+']


output_folder = Path(__file__).resolve().parent / "static_data"
CACHE_FILE = output_folder / "policy_cache.pkl"
RE_RATED_FILE = output_folder / "df_merged.parquet"

debugging_folder = Path(__file__).resolve().parent / "debugging"
debug = "Yes"

# -------------------------
# In-memory caches
# -------------------------
POLICY_MASTER_CACHE = {}
POLICY_HISTORY_CACHE = {}
RISK_CACHE = {}
TRANSACTION_TYPE_CACHE = {}
PET_RISK_PET_CACHE = {}
DEFINED_LIST_DETAIL_CACHE = {}
PET_RISK_CACHE = {}
PET_PROPOSER_CACHE = {}
ADDRESS_CACHE = {}
SCHEME_QUOTE_RESULT_COMMENT_CACHE = {}
RE_RATED_CACHE: pd.DataFrame | None = None

# -------------------------
# Load from DB (initial load)
# -------------------------
def load_static_data():
    """
    Load caches from the database.
    """
    global POLICY_MASTER_CACHE, POLICY_HISTORY_CACHE, RISK_CACHE, TRANSACTION_TYPE_CACHE
    global PET_RISK_PET_CACHE, DEFINED_LIST_DETAIL_CACHE, PET_RISK_CACHE, PET_PROPOSER_CACHE
    global ADDRESS_CACHE, SCHEME_QUOTE_RESULT_COMMENT_CACHE

    print("🔄 Loading static data from database...")

    POLICY_MASTER_CACHE = {pm.policy_master_id: pm for pm in PolicyMaster.objects.using("default").all()}
    POLICY_HISTORY_CACHE = {ph.policy_history_id: ph for ph in PolicyHistory.objects.using("default").all()}
    RISK_CACHE = {r.risk_id: r for r in Risk.objects.using("default").all()}
    TRANSACTION_TYPE_CACHE = {tt.transaction_type_id: tt for tt in TransactionType.objects.using("default").all()}
    PET_RISK_PET_CACHE = {prp.pet_risk_pet_id: prp for prp in PetRiskPet.objects.using("default").all()}
    DEFINED_LIST_DETAIL_CACHE = {dld.defined_list_detail_id: dld for dld in DefinedListDetail.objects.using("default").all()}
    PET_RISK_CACHE = {pr.risk_id: pr for pr in PetRisk.objects.using("default").all()}
    PET_PROPOSER_CACHE = {pp.pet_proposer_id: pp for pp in PetProposer.objects.using("default").all()}
    ADDRESS_CACHE = {a.address_id: a for a in Address.objects.using("default").all()}

    # Load filtered SchemeQuoteResultComment cache
    policy_ids = set(PolicyHistory.objects.using("default").values_list('scheme_quote_result_id', flat=True))
    SCHEME_QUOTE_RESULT_COMMENT_CACHE.clear()
    SCHEME_QUOTE_RESULT_COMMENT_CACHE.update({
        sqrc.scheme_quote_result_comment_id: sqrc
        for sqrc in SchemeQuoteResultComment.objects.using("default").filter(
            Q(comment_text__icontains="Belongs to proposer"),
            scheme_quote_result_id__in=policy_ids
        )
    })

    print(f"✅ Loaded {len(POLICY_MASTER_CACHE)} PolicyMaster records")
    print(f"✅ Loaded {len(POLICY_HISTORY_CACHE)} PolicyHistory records")
    print(f"✅ Loaded {len(RISK_CACHE)} Risk records")
    print(f"✅ Loaded {len(TRANSACTION_TYPE_CACHE)} TransactionType records")
    print(f"✅ Loaded {len(PET_RISK_PET_CACHE)} PetRiskPet records")
    print(f"✅ Loaded {len(DEFINED_LIST_DETAIL_CACHE)} DefinedListDetail records")
    print(f"✅ Loaded {len(PET_RISK_CACHE)} PetRisk records")
    print(f"✅ Loaded {len(PET_PROPOSER_CACHE)} PetProposer records")
    print(f"✅ Loaded {len(ADDRESS_CACHE)} Address records")
    print(f"✅ Loaded {len(SCHEME_QUOTE_RESULT_COMMENT_CACHE)} Scheme Quote Result Comment records")

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
            "DEFINED_LIST_DETAIL_CACHE": DEFINED_LIST_DETAIL_CACHE,
            "PET_RISK_CACHE": PET_RISK_CACHE,
            "PET_PROPOSER_CACHE": PET_PROPOSER_CACHE,
            "ADDRESS_CACHE": ADDRESS_CACHE,
            "SCHEME_QUOTE_RESULT_COMMENT_CACHE": SCHEME_QUOTE_RESULT_COMMENT_CACHE,
        }, f)
    print(f"✅ Saved cache to {CACHE_FILE}")

# -------------------------
# Load cache from disk
# -------------------------
def load_static_cache():
    """Load all caches from disk (no DB contact)."""
    global POLICY_MASTER_CACHE, POLICY_HISTORY_CACHE, RISK_CACHE, TRANSACTION_TYPE_CACHE
    global PET_RISK_PET_CACHE, DEFINED_LIST_DETAIL_CACHE, PET_RISK_CACHE, PET_PROPOSER_CACHE
    global ADDRESS_CACHE, SCHEME_QUOTE_RESULT_COMMENT_CACHE, DF_MERGED_CACHE

    if CACHE_FILE.exists():
        with open(CACHE_FILE, "rb") as f:
            data = pickle.load(f)
            POLICY_MASTER_CACHE = data.get("POLICY_MASTER_CACHE", {})
            POLICY_HISTORY_CACHE = data.get("POLICY_HISTORY_CACHE", {})
            RISK_CACHE = data.get("RISK_CACHE", {})
            TRANSACTION_TYPE_CACHE = data.get("TRANSACTION_TYPE_CACHE", {})
            PET_RISK_PET_CACHE = data.get("PET_RISK_PET_CACHE", {})
            DEFINED_LIST_DETAIL_CACHE = data.get("DEFINED_LIST_DETAIL_CACHE", {})
            PET_RISK_CACHE = data.get("PET_RISK_CACHE", {})
            PET_PROPOSER_CACHE = data.get("PET_PROPOSER_CACHE", {})
            ADDRESS_CACHE = data.get("ADDRESS_CACHE", {})
            SCHEME_QUOTE_RESULT_COMMENT_CACHE = data.get("SCHEME_QUOTE_RESULT_COMMENT_CACHE", {})
            DF_MERGED_CACHE = data.get("DF_MERGED_CACHE", None)
        print(f"✅ Loaded cache from {CACHE_FILE}")
    else:
        print("⚠️ No cache file found — run load_static_data() and build_re_rated_policies_cache() first.")

# -------------------------
# Load from Rating Guide (initial load)
# -------------------------
def all_rates():
    combined_nested = {}

    # 🔸 Step 1: Define all rating factors to parse
    factors_to_parse = [
        ("CoverLevel", "Rating Factor 1", None, "base_rate", None),
        ("Multipet", "Multipet Policy", None, "multipet", None),
        ("Voluntary excess - Copay", "Voluntary Excess - Co-Pay", None, "copay", None),
        ("Neutered", "Neutered / Spayed?", "Animal's Gender", "neutered_gender", None),
        ("Chipped", "Chipped?", None, "chipped", None),
        ("Vaccinations", "Are Vaccines up to date?", None, "vaccinations", None),
        ("Pre-existing", "Any pre-existing medical conditions?", None, "pre_existing", None),
        ("Aggressive", "Ever attacked, bitten or shown aggressive tendencies?", None, "aggressive", None),
        ("Is pet yours", "Is the animal your pet?", None, "is_pet_yours", None),
        ("UK resident", "Are you a full time UK resident?", None, "uk_resident", None),
        ("Kept at address", "Is the animal kept at the address given?", None, "kept_at_address", None),
        ("Trade or business", "Ever been used/connected with trade or business?", None, "trade_business", None),
        ("Postcode", "Postcode Area", None, "postcode", None),
        ("Pet Price", "Purchase Price", None, "pet_price", None),
        ("Policyholder Age", "Policyholder Age in Years", None, "ph_age", None),
        ("Age in Months", "Animal Age in months", None, "pet_age", None),
        ("Gender & Age", "Animal Age in Months", "Animal's Gender", "pet_age_gender", None),
    ]

    # 🔸 Step 2: Parse and merge each factor
    for sheet_name, h1, h2, factor_name, pet_filter in factors_to_parse:
        table_rows = parse_rates_excel(rating_guide, sheet_name, h1, h2, factor_name, pet_filter)
        nested = build_nested_structure(table_rows, factor_name)
        merge_nested_structures(combined_nested, nested)

    # 🔸 Step 3: Add Breed Factors
    breed_sheet = "Breed"

    # Dog Breeds
    dog_rows = parse_rates_excel(rating_guide, breed_sheet, "Dog Breed", None, "dog_breed", "dog")
    # Normalize dog breeds
    for row in dog_rows:
        breed_dict = row.get("dog_breed")
        if isinstance(breed_dict, dict):
            normalized_dict = {}
            for k, v in breed_dict.items():
                # Remove extra spaces from keys and values
                new_key = " ".join(k.split())
                new_value = " ".join(v.split()) if isinstance(v, str) else v
                normalized_dict[new_key] = new_value
            row["dog_breed"] = normalized_dict
    dog_nested = build_nested_structure(dog_rows, "dog_breed")
    merge_nested_structures(combined_nested, dog_nested)

    # Cat Breeds
    cat_rows = parse_rates_excel(rating_guide, breed_sheet, "Cat Breed", None, "cat_breed", "cat")
    # Normalize cat breeds
    for row in cat_rows:
        breed_dict = row.get("cat_breed")
        if isinstance(breed_dict, dict):
            normalized_dict = {}
            for k, v in breed_dict.items():
                new_key = " ".join(k.split())
                new_value = " ".join(v.split()) if isinstance(v, str) else v
                normalized_dict[new_key] = new_value
            row["cat_breed"] = normalized_dict
    cat_nested = build_nested_structure(cat_rows, "cat_breed")
    merge_nested_structures(combined_nested, cat_nested)

    # 🔸 Step 4: Optionally save everything to DB
    save_nested_rates_to_db(combined_nested)

    nested_rates_dict = convert_defaultdict(combined_nested)
    dog_nested_dict = convert_defaultdict(dog_nested)
    cat_nested_dict = convert_defaultdict(cat_nested)

    # Define the path for the JSON file in the same static_data folder
    JSON_DEBUG_FILE = output_folder / "nested_rates_debug.json"

    # Save JSON for debugging
    if nested_rates_dict is not None:
        with open(JSON_DEBUG_FILE, "w", encoding="utf-8") as f:
            json.dump(nested_rates_dict, f, indent=4)
        print(f"✅ Exported nested_rates_debug.json to {JSON_DEBUG_FILE}")

    # Dynamically extract all factors for table headers
    first_pet = next(iter(nested_rates_dict))
    first_scheme = next(iter(nested_rates_dict[first_pet]))
    factor_names = list(nested_rates_dict[first_pet][first_scheme].keys())
    factor_names.remove('limit')  # exclude limit for dynamic rows


    # 🔸 Step 5: Return dictionary
    return nested_rates_dict, dog_nested_dict, cat_nested_dict

# -------------------------
# Build DF_MERGED_CACHE
# -------------------------
def re_rated_cache():
    """
    Build the final df_merged DataFrame and store it in DF_MERGED_CACHE.
    """
    global DF_MERGED_CACHE

    # Make sure the base caches are loaded
    load_static_cache()

    # --------------------------------------------------
    # df_merged building logic goes here
    # --------------------------------------------------
# Convert to DataFrames
    df_master = pd.DataFrame([{
        "policy_master_id": m.policy_master_id,
        "policy_number": m.policy_number
    } for m in POLICY_MASTER_CACHE.values()])
    print(f"✅ Loaded cache from POLICY_MASTER_CACHE: {(len(df_master))} rows")

    # policy_number = 'SAP0079206'
    # df_master = df_master[df_master["policy_number"] == policy_number]

    df_history = pd.DataFrame([{
        "policy_master_id": h.policy_master_id,
        "scheme_quote_result_id": h.scheme_quote_result_id,
        "transaction_type_id": h.transaction_type_id,
        "risk_id": h.risk_id,
        "effective_date": h.effective_date,
        "gwp": h.gwp,
        "adjustment_number": h.adjustment_number,
    } for h in POLICY_HISTORY_CACHE.values()])
    print(f"✅ Loaded cache from POLICY_HISTORY_CACHE: {(len(df_history))} rows")

    min_yoa = 2023
    df_history["yoa"] = df_history.apply(
        lambda x: x["effective_date"].year,
        axis = 1 
    )
    df_history = df_history[df_history["yoa"] >= min_yoa]
    df_history["inception_month"] = df_history.apply(
        lambda x: (x["effective_date"].year) + div0(x["effective_date"].month, 100), 
        axis = 1
    )

    df_tt = pd.DataFrame([{
        "transaction_type_id": tt.transaction_type_id,
        "transaction_name": tt.transaction_name
    } for tt in TRANSACTION_TYPE_CACHE.values()])
    print(f"✅ Loaded cache from TRANSACTION_TYPE_CACHE: {(len(df_tt))} rows")

    df_risk = pd.DataFrame([{
        "risk_id": r.risk_id,
        "copay": r.copay
    } for r in RISK_CACHE.values()])
    print(f"✅ Loaded cache from RISK_CACHE: {(len(df_risk))} rows")
    
    df_prp = pd.DataFrame([{
        "pet_risk_pet_id": prp.pet_risk_pet_id,
        "pet_name": prp.pet_name,
        "risk_id": prp.risk_id,
        "pet_type_dldid": prp.pet_type_dldid,
        "pet_sub_type_dldid": prp.pet_sub_type_dldid,
        "breed_dldid": prp.breed_dldid,
        "size_dldid": prp.size_dldid,
        "gender_dldid": prp.gender_dldid,
        "cost_of_pet": prp.cost_of_pet,
        "pet_dob": prp.pet_dob,
        "pet_name": prp.pet_name,
        "prn": prp.prn,
        "neutered": prp.neutered,
        "chipped": prp.chipped,
        "vaccinations": prp.vaccinations,
        "pre_existing": prp.pre_existing,
        "aggressive": prp.aggressive,
        "is_pet_yours": prp.is_pet_yours,
    } for prp in PET_RISK_PET_CACHE.values()])
    print(f"✅ Loaded cache from PET_RISK_PET_CACHE: {(len(df_prp))} rows")

    # Assume null rows on Aggressive is FALSE
    df_prp["aggressive"] = df_prp["aggressive"].fillna(False)

    df_dld = pd.DataFrame([{
        "dld_id": dld.defined_list_detail_id,
        "dld_name": dld.dld_name,
        "unique_id": dld.unique_id
    } for dld in DEFINED_LIST_DETAIL_CACHE.values()])
    print(f"✅ Loaded cache from DEFINED_LIST_DETAIL_CACHE: {(len(df_dld))} rows")
    
    df_dld["Item"] = (
        df_dld["unique_id"]
        .str.split(".", n=1).str[0]
        .str.replace("Cat", "PetSub", regex=False)
        .str.replace("Dog", "PetSub", regex=False)
        .str.replace("PetSubBreeds", "Breed", regex=False)
        .str.lower()
    )

    df_pr = pd.DataFrame([{
        "risk_id": pr.risk_id,
        "pet_proposer_id": pr.pet_proposer_id,
        "pet_cover_level_dldid": pr.pet_cover_level_dldid
    } for pr in PET_RISK_CACHE.values()])
    print(f"✅ Loaded cache from PET_RISK_CACHE: {(len(df_pr))} rows")
    
    df_pp = pd.DataFrame([{
        "pet_proposer_id": pp.pet_proposer_id,
        "address_id": pp.address_id,
        "ph_dob": pp.ph_dob,
        "uk_resident": pp.uk_resident,
        "kept_at_address": pp.kept_at_address,
        "trade_business": pp.trade_business
    } for pp in PET_PROPOSER_CACHE.values()])
    print(f"✅ Loaded cache from PET_PROPOSER_CACHE: {(len(df_pp))} rows")

    df_a = pd.DataFrame([{
        "address_id": a.address_id,
        "postcode": a.postcode
    } for a in ADDRESS_CACHE.values()])
    print(f"✅ Loaded cache from ADDRESS_CACHE: {(len(df_a))} rows")

    # Pull in Cover Level Name and proposer info
    df_pr_merged = df_pr.merge(
        df_dld[["dld_name", "dld_id"]], 
        how="inner", 
        left_on="pet_cover_level_dldid", 
        right_on="dld_id"
    )
    df_pr_merged = df_pr_merged.merge(df_pp, how="inner", on="pet_proposer_id")
    df_pr_merged = df_pr_merged.merge(df_a, how="inner", on="address_id")
    
    # Remove columns not required
    df_pr_merged = df_pr_merged[[
        "risk_id", "dld_name", "ph_dob", "postcode", "uk_resident", "kept_at_address","trade_business"
        ]].rename(columns={"dld_name": "scheme"})

    # Map the DLD ID columns to readable "Item" types
    melted_prp = df_prp.melt(
        id_vars=[
            "pet_risk_pet_id", 
            "risk_id", 
            "prn",
            "pet_name",
            "pet_dob",
            "cost_of_pet",
            "neutered", 
            "aggressive", 
            "pre_existing",
            "chipped",
            "vaccinations",
            "is_pet_yours"
        ],
        value_vars=[
            "pet_type_dldid",
            "pet_sub_type_dldid",
            "breed_dldid",
            "size_dldid",
            "gender_dldid",
        ],
        var_name="item_type",
        value_name="dld_id"
    )

    # Join the DLD table to the PRP one
    melted_merge = melted_prp.merge(
        df_dld, 
        how="left", 
        on="dld_id"
    )

    # Pivot the table
    pivoted_merge = melted_merge.pivot_table(
        index=[
            "pet_risk_pet_id", 
            "risk_id",
            "pet_name",
            "prn",
            "pet_dob",
            "cost_of_pet",
            "neutered", 
            "aggressive", 
            "pre_existing",
            "chipped",
            "vaccinations",
            "is_pet_yours"
        ],
        columns="Item",
        values="dld_name",
        aggfunc="first"
    ).reset_index()
    pivoted_merge["pet_name"] = pivoted_merge["pet_name"].str.strip()
    

    # Premium per pet
    df_sqrc = pd.DataFrame([{
        "scheme_quote_result_comment_id": sqrc.scheme_quote_result_comment_id,
        "scheme_quote_result_id": sqrc.scheme_quote_result_id,
        "comment_text": sqrc.comment_text,
        "prem_per_pet": sqrc.premium_total,
    } for sqrc in SCHEME_QUOTE_RESULT_COMMENT_CACHE.values()])

    df_sqrc = df_sqrc[df_sqrc["comment_text"].str.contains("Belongs", case=False)]
    df_sqrc["pet_name"] = df_sqrc["comment_text"].str.extract(r"^(.*?)\s*Belongs to proposer", expand=False).str.strip()
    df_sqrc = df_sqrc[["scheme_quote_result_id", "pet_name", "prem_per_pet"]]

    # Debugging
    if debug == "Yes":
        df_master.to_csv(debugging_folder / "df_master.csv", index=False)
        df_history.to_csv(debugging_folder / "df_history.csv", index=False)
        df_tt.to_csv(debugging_folder / "df_tt.csv", index=False)
        df_risk.to_csv(debugging_folder / "df_risk.csv", index=False)
        df_prp.to_csv(debugging_folder / "df_prp.csv", index=False)
        df_pr_merged.to_csv(debugging_folder / "df_pr_merged.csv", index=False)
        pivoted_merge.to_csv(debugging_folder / "pivoted_merge.csv", index=False)
        df_sqrc.to_csv(debugging_folder / "df_sqrc.csv", index=False)
    else:
        None
    print(f"✅ Exported files to debug folder")

    # Join the tables
    df_merged = df_master.merge(df_history, how="inner", on="policy_master_id")
    df_merged = df_merged.merge(df_risk, how="inner", on="risk_id")
    df_merged = df_merged.merge(df_tt, how="inner", on="transaction_type_id")
    df_merged = df_merged.merge(pivoted_merge, how="inner", on="risk_id")
    df_merged = df_merged.merge(df_pr_merged, how="inner", on="risk_id")
    df_merged = df_merged.merge(df_sqrc, how="inner", on=["scheme_quote_result_id", "pet_name"])

    # Multipet calc
    df_merged["max_prn"] = df_merged.groupby(["policy_number", "adjustment_number"])["prn"].transform("max")
    df_merged["multipet"] = df_merged["max_prn"].apply(lambda x: "yes" if x > 1 else "no")

    # GWP per pet calc
    df_merged["total_combined_prem"] = df_merged.groupby(["policy_number", "adjustment_number"])["prem_per_pet"].transform("sum")
    df_merged["gwp_per_pet"] = div0(df_merged["prem_per_pet"], df_merged["total_combined_prem"]) * df_merged["gwp"]

    # Reformatting
    df_merged["pettype"] = df_merged["pettype"].str.lower()
    df_merged["scheme"] = df_merged["scheme"].str.lower()
    df_merged["postcode"] = (
        df_merged['postcode']
        .astype(str)
        .str.strip()
        .str.lower()
        .str.extract(r'^([a-z]{1,2})', expand=False)
    )
    df_merged["breed"] = df_merged["breed"].str.lower()

    # Add S/M/L to crossbreed
    df_merged["breed"] = df_merged.apply(
        lambda row: f"{row['breed']}: {row['sizeofpet'].split()[0]}"
                    if row["breed"].lower() in ["crossbreed", "mongrel"]
                    else row["breed"],
        axis=1
    ).str.lower()

    df_merged["copay"] = df_merged["copay"].map({1: "yes", 2: "no"})
    df_merged["neutered"] = df_merged["neutered"].map({True: "yes", False: "no"})
    df_merged["pre_existing"] = df_merged["pre_existing"].map({True: "yes", False: "no"})
    df_merged["aggressive"] = df_merged["aggressive"].map({True: "yes", False: "no"})
    df_merged["chipped"] = df_merged["chipped"].map({True: "yes", False: "no"})
    df_merged["vaccinations"] = df_merged["vaccinations"].map({True: "yes", False: "no"})
    df_merged["uk_resident"] = df_merged["uk_resident"].map({True: "yes", False: "no"})
    df_merged["is_pet_yours"] = df_merged["is_pet_yours"].map({True: "yes", False: "no"})
    df_merged["kept_at_address"] = df_merged["kept_at_address"].map({True: "yes", False: "no"})
    df_merged["trade_business"] = df_merged["trade_business"].map({True: "yes", False: "no"})

    df_merged["neutered_gender"] = (
        df_merged["gender"].astype(str) + ": " + df_merged["neutered"].astype(str)
    ).str.lower()
    
    # Filter NB / REN only
    df_merged = df_merged[
        (df_merged["transaction_name"] == "New Business") | 
        (df_merged["transaction_name"] == "Renewal")  
    ]

    # Policyholder Age (Years)
    df_merged["ph_age"] = df_merged.apply(
        lambda x: x["effective_date"].year - x["ph_dob"].year,
        axis = 1 
    )
    ph_bins = [0, 19.999, 29.999, 39.999, 49.999, 59.999, 69.999, 79.999, 89.999, float("inf")]
    df_merged["ph_age"] = pd.cut(
        df_merged["ph_age"], 
        bins=ph_bins, 
        labels=ph_age_order, 
        right=True, 
        include_lowest=True
    )

    # Pet Age in months
    df_merged["pet_age_mnths"] = df_merged.apply(
        lambda x: (x["effective_date"].year - x["pet_dob"].year) * 12 + (x["effective_date"].month - x["pet_dob"].month),
        axis = 1 
    )
    df_merged["pet_age"] = df_merged["pet_age_mnths"]

    # Pet Age & Gender
    pet_bins_1 = [0, 50, 100, float("inf")]
    pet_labels_1 = ["1\u201350", "51\u2013100", "101+"]
    df_merged["pet_age_mnths"] = pd.cut(
        df_merged["pet_age_mnths"], 
        bins=pet_bins_1, 
        labels=pet_labels_1, 
        right=True, 
        include_lowest=True
    )
    df_merged["pet_age_gender"] = (
        df_merged["gender"].astype(str) + ": " + df_merged["pet_age_mnths"].astype(str)
    ).str.lower()

    # Pet Age in Months
    pet_bins_2 = [
        0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,28,31,
        34,37,40,43,46,48,54,60,66,72,78,84,90,96,102,108,114,120,126,132,138,
        144,150,156,162,168,174,180,186,192,204,216,228,240,float("inf")
    ]
    df_merged["pet_age"] = pd.cut(
        df_merged["pet_age"], 
        bins=pet_bins_2, 
        labels=pet_age_order, 
        right=True, 
        include_lowest=True
    )

    # Cost of Pet
    pet_price_bins = [0, 75, 150, 300, 600, 1200, float("inf")]
    df_merged["pet_price"] = pd.cut(
        df_merged["cost_of_pet"],
        bins = pet_price_bins,
        labels = pet_price_order,
        right=True,
        include_lowest=True
    )

    # Fetch the rates
    all_rates = PetRates.objects.all()
    df_rates = pd.DataFrame(list(all_rates.values()))
    print(f"✅ Loaded from PetRates{(len(df_rates))}")
    df_rates["scheme"] = df_rates["scheme"].str.replace("_", " ")
    df_rates = df_rates.rename(columns={"pet_type": "pettype"})

    
    # Exclude Champ policies for now
    df_merged = df_merged[~df_merged["scheme"].str.contains("Champ", case=False, na=False)]
    
    # Debugging
    if debug == "Yes":   
        df_rates.to_csv(debugging_folder / "df_rates.csv", index=False)
        df_merged.to_csv(debugging_folder / "df_merged.csv", index=False)
    else:
        None
    
    # Prepare base rates DataFrame
    df_base_rates = df_rates[df_rates["factor"] == "base_rate"][["pettype", "scheme", "rate"]]
    df_base_rates = df_base_rates.rename(columns={"rate": "base_rate"})

    # Merge base rates
    df_merged = df_merged.merge(df_base_rates, on=["pettype", "scheme"], how="left")
    print("Base rates loaded for first 10 rows:")
    print(df_merged[["pettype", "scheme", "base_rate"]].head(10))

    # Prepare limits DataFrame
    df_limits = df_rates[["pettype", "scheme", "limit"]].drop_duplicates()
    
    # Merge limits
    df_merged = df_merged.merge(df_limits, on=["pettype", "scheme"], how="left")
    print("Limit loaded for first 10 rows:")
    print(df_merged[["pettype", "scheme", "limit"]].head(10))

    factors = [
        "pet_age_gender", "pet_age", "pet_price", "neutered_gender", "chipped",
        "vaccinations", "pre_existing", "aggressive", "is_pet_yours", "postcode",
        "uk_resident", "kept_at_address", "trade_business", "ph_age", "copay", "multipet"
    ]

    # Handle breed separately because it depends on pet type
    breed_mask = df_rates["factor"].isin(["dog_breed", "cat_breed"])
    df_breed_rates = df_rates[breed_mask].rename(columns={"option": "breed", "rate": "breed_factor"})
    df_breed_rates = df_breed_rates[["pettype", "scheme", "breed", "breed_factor"]]

    # Merge breed factor
    df_merged = df_merged.merge(df_breed_rates, how="left", on=["pettype", "scheme", "breed"])
    print("✅ Breed factor loaded.")

    # Now handle remaining factors
    for factor in factors:
        df_factor = df_rates[df_rates["factor"] == factor].rename(
            columns={"option": factor, "rate": f"{factor}_factor"}
        )
        df_factor = df_factor[["pettype", "scheme", factor, f"{factor}_factor"]]
        df_merged = df_merged.merge(df_factor, how="left", on=["pettype", "scheme", factor])
        print(f"✅ {factor}_factor loaded.")

    # Quick check: show first few rows
    debug_cols = ["pettype", "scheme", "breed"] + [f"{factor}_factor" for factor in factors] + ["breed_factor"]
    print(df_merged[debug_cols].head(10))

    df_merged["re_rated_gwp_per_pet"] = df_merged.eval(
        "base_rate * pet_age_factor * pet_age_gender_factor * breed_factor * pet_price_factor *"
        "neutered_gender_factor * chipped_factor * vaccinations_factor * pre_existing_factor *"
        "aggressive_factor * is_pet_yours_factor * postcode_factor * uk_resident_factor *"
        "kept_at_address_factor * trade_business_factor * ph_age_factor * copay_factor * multipet_factor"
    )
    df_merged["re_rated_gwp_per_pol"] = df_merged.groupby(
        ["policy_number", "adjustment_number"]
        )["re_rated_gwp_per_pet"].transform("sum")
    # --------------------------------------------------
    # Export to CSV
    df_merged.to_csv(r'C:\Users\jorda\OneDrive\Desktop\df_merged_export.csv', index=False)
    
    RE_RATED_CACHE = df_merged

    # Save to parquet for persistence
    if RE_RATED_CACHE is not None:
        RE_RATED_CACHE.to_parquet(RE_RATED_FILE, index=False)
        print(f"✅ Exported df_merged to {RE_RATED_FILE}")

# -------------------------
# Load DF_MERGED_CACHE from disk
# -------------------------
def load_re_rated_cache():
    """
    Load DF_MERGED_CACHE from parquet file if it exists.
    """
    global RE_RATED_CACHE
    if RE_RATED_FILE.exists():
        RE_RATED_CACHE = pd.read_parquet(RE_RATED_FILE)
        print(f"✅ Loaded re rated from {RE_RATED_FILE}, rows: {len(RE_RATED_CACHE)}")
    else:
        print("⚠️ df_merged.parquet not found — run build_re_rated_policies_cache() first.")
