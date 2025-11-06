import pandas as pd
from django.shortcuts import render
from .models import *
from collections import defaultdict
from django.views.decorators.http import require_GET
from django.http import JsonResponse
from .utils import *
import json
import os
from base import static_data

rating_guide =  r'C:\Users\jorda\OneDrive\Desktop\SP Rating Guide v38 - Multiple changes.xlsx'

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

# Create your views here.
rooms = [
    {'name': 'GWP Summary By YoA', 'url': 'gwp-summaries'},
    {'name': 'Full Policy List', 'url': 'policy_list'},
    {'name': 'Rates', 'url': 'rates'},
]

def home(request):
    context = {'rooms': rooms}
    return render(request, 'base/home.html', context)

factors = [
    {'name': 'Premium Calculator', 'url': 'prem_calc'},
    {'name': 'Base Rates', 'url': 'base_rates'},
    {'name': 'Pet Gender & Age', 'url': 'pet_age_gender'},
    {'name': 'Pet Age (Months)', 'url': 'pet_age'},
    {'name': 'Pet Breed', 'url': 'breed'},
    {'name': 'Multipet', 'url': 'multipet'},
    {'name': 'Copay', 'url': 'copay'},
    {'name': 'Chipped', 'url': 'chipped'},
    {'name': 'Postcode', 'url': 'postcode'},
    {'name': 'Policyholder Age', 'url': 'ph_age'},
    {'name': 'Purchase Price (£)', 'url': 'pet_price'},
    {'name': 'Neutering & Gender', 'url': 'neutered'},
    {'name': 'Vaccinations', 'url': 'vaccinations'},
    {'name': 'Pre-existing', 'url': 'pre_existing'},
    {'name': 'Aggressive', 'url': 'aggressive'},
    {'name': 'Is Pet yours?', 'url': 'is_pet_yours'},
    {'name': 'UK Resident', 'url': 'uk_resident'},
    {'name': 'Kept at Address', 'url': 'kept_at_address'},
    {'name': 'Trade or Business', 'url': 'trade_business'},
    {'name': 'Re-rated policies', 'url': 're_rated_policies'},
    {'name': 'test', 'url': 'test'},
]

cover_limits = {
    "Bronze": 2250,
    "Silver": 3000,
    "Gold": 4000,
    "Prime": 2500,
    "Premier": 4000,
    "Premier Plus": 8000
}

pet_age_order = ['0','1','2','3','4','5','6','7','8','9','10','11','12','13','14','15','16',
             '17','18','19','20','21','22','23','24–28','29–31','32–34','35–37','38–40',
             '41–43','44–46','47–48','49–54','55–60','61–66','67–72','73–78','79–84',
             '85–90','91–96','97–102','103–108','109–114','115–120','121–126','127–132',
             '133–138','139–144','145–150','151–156','157–162','163–168','169–174','175–180',
             '181–186','187–192','193–204','205–216','217–228','229–240','241+']

ph_age_order = ['0 - 19.999','20 - 29.999','30 - 39.999','40 - 49.999','50 - 59.999','60 - 69.999','70 - 79.999','80 - 89.999','90 and over']

pet_price_order = [ '£0–£75','£76–£150','£151–£300','£301–£600','£601–£1,200','£1,201+']

def rates(request):
    context = {'factors': factors}
    return render(request, 'base/rates.html', context)

# Helper to convert defaultdict -> dict recursively
def convert_defaultdict(d):
    if isinstance(d, defaultdict):
        d = dict(d)
    for k, v in d.items():
        if isinstance(v, defaultdict):
            d[k] = convert_defaultdict(v)
    return d

# Debug step for viewing the data structure
def export_nested_rates_to_file(nested_rates_dict, file_path=None):
    if file_path is None:
        file_path = os.path.join(os.getcwd(), "nested_rates_debug.json")
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(nested_rates_dict, f, indent=4)
    
    print(f"✅ Nested rates exported to {file_path}")

def all_rates():
    file_path = rating_guide
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
        table_rows = parse_rates_excel(file_path, sheet_name, h1, h2, factor_name, pet_filter)
        nested = build_nested_structure(table_rows, factor_name)
        merge_nested_structures(combined_nested, nested)

    # 🔸 Step 3: Add Breed Factors
    breed_sheet = "Breed"

    # Dog Breeds
    dog_rows = parse_rates_excel(file_path, breed_sheet, "Dog Breed", None, "dog_breed", "dog")
    dog_nested = build_nested_structure(dog_rows, "dog_breed")
    merge_nested_structures(combined_nested, dog_nested)

    # Cat Breeds
    cat_rows = parse_rates_excel(file_path, breed_sheet, "Cat Breed", None, "cat_breed", "cat")
    cat_nested = build_nested_structure(cat_rows, "cat_breed")
    merge_nested_structures(combined_nested, cat_nested)

    # 🔸 Step 4: Optionally save everything to DB
    save_nested_rates_to_db(combined_nested)

    nested_rates_dict = convert_defaultdict(combined_nested)
    dog_nested_dict = convert_defaultdict(dog_nested)
    cat_nested_dict = convert_defaultdict(cat_nested)
    export_nested_rates_to_file(nested_rates_dict)

    # Dynamically extract all factors for table headers
    first_pet = next(iter(nested_rates_dict))
    first_scheme = next(iter(nested_rates_dict[first_pet]))
    factor_names = list(nested_rates_dict[first_pet][first_scheme].keys())
    factor_names.remove('limit')  # exclude limit for dynamic rows


    # 🔸 Step 5: Return dictionary
    return nested_rates_dict, dog_nested_dict, cat_nested_dict

def get_rates_from_db(factor):
    """
    Returns a nested dictionary similar to nested_rates_dict
    but fetched from the DB.
    Handles both single-value and multi-option factors.
    """
    qs = PetRates.objects.filter(factor=factor)
    nested = {}

    for row in qs:
        pet_dict = nested.setdefault(row.pet_type, {})
        scheme_dict = pet_dict.setdefault(row.scheme, {"limit": row.limit})

        # Handle options (e.g. yes/no) vs single values
        if row.option:
            existing_value = scheme_dict.get(factor)
            if not isinstance(existing_value, dict):
                # Convert float or None into a dict
                scheme_dict[factor] = {}
            scheme_dict[factor][row.option] = row.rate
        else:
            scheme_dict[factor] = row.rate

    return nested

def base_rates(request):
    nested_rates = get_rates_from_db("base_rate")

    return render(request, "base/rates/base_rates.html", {
        "nested_rates": nested_rates,
        "factor": ["base_rate"]
    })   

def copay(request):
    nested_rates = get_rates_from_db("copay")
    print(nested_rates)
    return render(request, "base/rates/copay.html", {
        "nested_rates": nested_rates,
        "factor": ["copay"]
    })

def postcode(request):
    nested_rates = get_rates_from_db("postcode")

    first_pet = next(iter(nested_rates))
    first_scheme = next(iter(nested_rates[first_pet]))
    pc_area = list(nested_rates[first_pet][first_scheme]['postcode'].keys())
    pc_area.sort()

    return render(request, "base/rates/postcode.html", {
        "nested_rates": nested_rates,
        "pc_area": pc_area
    })

def breed(request):
    dog_nested = get_rates_from_db("dog_breed")
    cat_nested = get_rates_from_db("cat_breed")
    
    first_pet_dog = next(iter(dog_nested))
    first_scheme_dog = next(iter(dog_nested[first_pet_dog]))
    dog_breed_list = list(dog_nested[first_pet_dog][first_scheme_dog]['dog_breed'].keys())
    dog_breed_list.sort()

    first_pet_cat = next(iter(cat_nested))
    first_scheme_cat = next(iter(cat_nested[first_pet_cat]))
    cat_breed_list = list(cat_nested[first_pet_cat][first_scheme_cat]['cat_breed'].keys())
    cat_breed_list.sort()

    return render(request, "base/rates/breed.html", {
        'dog_nested_rates': dog_nested,
        'dog_breeds': dog_breed_list,
        'cat_nested_rates': cat_nested,
        'cat_breeds': cat_breed_list,
    })

def multipet(request):
    nested_rates = get_rates_from_db("multipet")
    return render(request, "base/rates/multipet.html", {
        "nested_rates": nested_rates,
        "factor": ["multipet"]
    })

def chipped(request):
    nested_rates = get_rates_from_db("chipped")

    return render(request, "base/rates/chipped.html", {
        "nested_rates": nested_rates,
        "factor": ["chipped"]
    })

def ph_age(request):
    nested_rates = get_rates_from_db("ph_age")

    first_pet = next(iter(nested_rates))
    first_scheme = next(iter(nested_rates[first_pet]))
    age_bandings = list(nested_rates[first_pet][first_scheme]['ph_age'].keys())
    age_bandings.sort(key=lambda x: ph_age_order.index(x) if x in ph_age_order else float('inf'))

    return render(request, "base/rates/ph_age.html", {
        "nested_rates": nested_rates,
        "age_bandings": age_bandings
    })

def pet_age(request):
    nested_rates = get_rates_from_db("pet_age")

    first_pet = next(iter(nested_rates))
    first_scheme = next(iter(nested_rates[first_pet]))
    pet_age_bandings = list(nested_rates[first_pet][first_scheme]['pet_age'].keys())
    pet_age_bandings.sort(key=lambda x: pet_age_order.index(x) if x in pet_age_order else float('inf'))

    return render(request, "base/rates/pet_age.html", {
        "nested_rates": nested_rates,
        "pet_age_bandings": pet_age_bandings
    })

def pet_price(request):
    nested_rates = get_rates_from_db("pet_price")

    first_pet = next(iter(nested_rates))
    first_scheme = next(iter(nested_rates[first_pet]))
    price_bands = list(nested_rates[first_pet][first_scheme]['pet_price'].keys())
    price_bands.sort(key=lambda x: pet_price_order.index(x) if x in pet_price_order else float('inf'))

    return render(request, "base/rates/pet_price.html", {
        "nested_rates": nested_rates,
        "price_bands": price_bands
    })

def neutered(request):
    nested_rates = get_rates_from_db("neutered_gender")

    first_pet = next(iter(nested_rates))
    first_scheme = next(iter(nested_rates[first_pet]))
    neutered = list(nested_rates[first_pet][first_scheme]['neutered_gender'].keys())
    neutered.sort()
    
    return render(request, "base/rates/neutered.html", {
        "nested_rates": nested_rates,
        "neutered": neutered
    })

def pet_age_gender(request):
    nested_rates = get_rates_from_db("pet_age_gender")

    first_pet = next(iter(nested_rates))
    first_scheme = next(iter(nested_rates[first_pet]))
    pet_age_gender_group = list(nested_rates[first_pet][first_scheme]['pet_age_gender'].keys())
    order = ['Female: 1-50', 'Female: 51-100', 'Female: 101+', 'Male: 1-50', 'Male: 51-100', 'Male: 101+']
    pet_age_gender_group.sort(key=lambda x: order.index(x) if x in order else float('inf'))

    return render(request, "base/rates/pet_age_gender.html", {
        "nested_rates": nested_rates,
        "pet_age_gender_group": pet_age_gender_group
    })

def vaccinations(request):
    nested_rates = get_rates_from_db("vaccinations")
    return render(request, "base/rates/vaccinations.html", {
        "nested_rates": nested_rates
    })

def pre_existing(request):
    nested_rates = get_rates_from_db("pre_existing")
    print(nested_rates)
    return render(request, "base/rates/pre_existing.html", {
        "nested_rates": nested_rates
    })

def aggressive(request):
    nested_rates = get_rates_from_db("aggressive")
    return render(request, "base/rates/aggressive.html", {
        "nested_rates": nested_rates
    })

def is_pet_yours(request):
    nested_rates = get_rates_from_db("is_pet_yours")
    return render(request, "base/rates/is_pet_yours.html", {
        "nested_rates": nested_rates
    })

def uk_resident(request):
    nested_rates = get_rates_from_db("uk_resident")
    return render(request, "base/rates/uk_resident.html", {
        "nested_rates": nested_rates
    })

def kept_at_address(request):
    nested_rates = get_rates_from_db("kept_at_address")
    return render(request, "base/rates/kept_at_address.html", {
        "nested_rates": nested_rates
    })

def trade_business(request):
    nested_rates = get_rates_from_db("trade_business")
    return render(request, "base/rates/trade_business.html", {
        "nested_rates": nested_rates
    })

def prem_calc(request):
    # Distinct pet types
    pet_types = PetRates.objects.values_list('pet_type', flat=True).distinct()

    # Distinct schemes / cover levels
    cover_levels = PetRates.objects.values_list('scheme', flat=True).distinct()

    pet_age_options = list(PetRates.objects.filter(factor='pet_age').values_list('option', flat=True).distinct())
    pet_age_options.sort(key=lambda x: pet_age_order.index(x) if x in pet_age_order else float('inf'))

    pet_price_options = list(PetRates.objects.filter(factor='pet_price').values_list('option', flat=True).distinct())
    pet_price_options.sort(key=lambda x: pet_price_order.index(x) if x in pet_price_order else float('inf'))

    ph_age_options = list(PetRates.objects.filter(factor='ph_age').values_list('option', flat=True).distinct())
    ph_age_options.sort(key=lambda x: ph_age_order.index(x) if x in ph_age_order else float('inf'))

    dog_breeds = list(PetRates.objects.filter(factor='dog_breed').values_list('option', flat=True).distinct())
    cat_breeds = list(PetRates.objects.filter(factor='cat_breed').values_list('option', flat=True).distinct())

    postcodes = list(PetRates.objects.filter(factor='postcode').values_list('option', flat=True).distinct())



    context = {
        "pet_types": pet_types,
        "cover_levels": cover_levels,
        "pet_age_options": pet_age_options,
        "pet_price_options": pet_price_options,
        "ph_age_options": ph_age_options,
        "dog_breeds": dog_breeds,
        "cat_breeds": cat_breeds,
        "postcodes": postcodes
    }

    return render(request, "base/rates/prem_calc.html", context)

@require_GET
def get_pet_rates(request):
    pet_type = request.GET.get("pet_type")
    cover_level = request.GET.get("cover_level")
    pet_age = request.GET.get("pet_age1") or ""
    pet_gender = request.GET.get("pet_gender") or ""
    pet_age_gender = f"{pet_gender.lower()}: {pet_age}"
    pet_age_mnths = request.GET.get("pet_age2")

    print("=== GET PET RATES ===")
    print("pet_type:", pet_type)
    print("cover_level:", cover_level)
    print("pet_age:", pet_age)
    print("pet_gender:", pet_gender)
    print("pet_age_gender:", pet_age_gender)
    print("pet_age_mnths:", pet_age_mnths)

    if not pet_type or not cover_level:
        return JsonResponse({"error": "Missing parameters"}, status=400)

    rates = PetRates.objects.filter(
        pet_type__iexact=pet_type,
        scheme__iexact=cover_level,
    )

    if not rates:
        print("No matching base_rate found.")
        return JsonResponse({"error": "No matching base rate found"}, status=404)

    limit = rates.first().limit

    all_factors = {}

    for r in rates:
        if r.option:
            all_factors.setdefault(r.factor, {})[r.option] = r.rate
        else:
            all_factors[r.factor] = r.rate

    base_rate = all_factors.get("base_rate", 0)
    pet_age_gender_rate = all_factors["pet_age_gender"].get(pet_age_gender, 1)
    pet_age_rate = all_factors["pet_age"].get(pet_age_mnths, 1)

    print("base_rate:", base_rate, "limit:", limit, "pet_age_gender_rate:", pet_age_gender_rate, "pet_age_rate", pet_age_rate)

    return JsonResponse({
        "base_rate": base_rate,
        "limit": limit,
        "pet_age_gender_rate": pet_age_gender_rate,
        "pet_age_rate": pet_age_rate
    })

def re_rated_policies(request):
    # Load cached data from disk (no DB queries)
    static_data.load_static_cache()

    # Convert to DataFrames
    df_master = pd.DataFrame([{
        "policy_master_id": m.policy_master_id,
        "policy_number": m.policy_number
    } for m in static_data.POLICY_MASTER_CACHE.values()])

    policy_number = 'SAP0079206'
    df_master = df_master[df_master["policy_number"] == policy_number]

    df_history = pd.DataFrame([{
        "policy_master_id": h.policy_master_id,
        "scheme_quote_result_id": h.scheme_quote_result_id,
        "transaction_type_id": h.transaction_type_id,
        "risk_id": h.risk_id,
        "effective_date": h.effective_date,
        "gwp": h.gwp,
        "adjustment_number": h.adjustment_number,
    } for h in static_data.POLICY_HISTORY_CACHE.values()])

    df_tt = pd.DataFrame([{
        "transaction_type_id": tt.transaction_type_id,
        "transaction_name": tt.transaction_name
    } for tt in static_data.TRANSACTION_TYPE_CACHE.values()])

    df_risk = pd.DataFrame([{
        "risk_id": r.risk_id,
        "copay": r.copay
    } for r in static_data.RISK_CACHE.values()])
    
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
    } for prp in static_data.PET_RISK_PET_CACHE.values()])

    df_dld = pd.DataFrame([{
        "dld_id": dld.defined_list_detail_id,
        "dld_name": dld.dld_name,
        "unique_id": dld.unique_id
    } for dld in static_data.DEFINED_LIST_DETAIL_CACHE.values()])
    
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
    } for pr in static_data.PET_RISK_CACHE.values()])
    
    df_pp = pd.DataFrame([{
        "pet_proposer_id": pp.pet_proposer_id,
        "address_id": pp.address_id,
        "ph_dob": pp.ph_dob,
        "uk_resident": pp.uk_resident,
        "kept_at_address": pp.kept_at_address,
        "trade_business": pp.trade_business
    } for pp in static_data.PET_PROPOSER_CACHE.values()])

    df_a = pd.DataFrame([{
        "address_id": a.address_id,
        "postcode": a.postcode
    } for a in static_data.ADDRESS_CACHE.values()])

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

    # Premium per pet
    df_sqrc = pd.DataFrame([{
        "scheme_quote_result_comment_id": sqrc.scheme_quote_result_comment_id,
        "scheme_quote_result_id": sqrc.scheme_quote_result_id,
        "comment_text": sqrc.comment_text,
        "prem_per_pet": sqrc.premium_total,
    } for sqrc in static_data.SCHEME_QUOTE_RESULT_COMMENT_CACHE.values()])

    df_sqrc = df_sqrc[df_sqrc["comment_text"].str.contains("Belongs", case=False)]
    df_sqrc["pet_name"] = df_sqrc["comment_text"].str.extract(r"^(.*?)\s*Belongs to proposer", expand=False).str.strip()
    df_sqrc = df_sqrc[["scheme_quote_result_id", "pet_name", "prem_per_pet"]]

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
    df_rates["scheme"] = df_rates["scheme"].replace("_", " ", regex=False)
  
    # Exclude Champ policies for now
    # df_merged = df_merged[~df_merged["scheme"].str.contains("Champ", case=False, na=False)]

    # Base Rates  
    df_merged["base_rate"] = df_merged.apply(
        lambda row: df_rates[
            (df_rates["pet_type"] == row["pettype"]) &
            (df_rates["scheme"] == row["scheme"]) &
            (df_rates["factor"] == "base_rate")
        ]['rate'].values[0], axis=1
     )
    
    # Limit
    df_merged["limit"] = df_merged.apply(
        lambda row: df_rates[
            (df_rates["pet_type"] == row["pettype"]) &
            (df_rates["scheme"] == row["scheme"])
        ]['limit'].values[0], axis=1
    )

    # Breeds
    df_merged["breed_factor"] = df_merged.apply(
        lambda row: (
            df_rates[
                (df_rates["pet_type"] == row["pettype"]) &
                (df_rates["scheme"] == row["scheme"]) &
                ((df_rates["factor"] == "dog_breed") | (df_rates["factor"] == "cat_breed")) &
                (df_rates["option"] == row["breed"])
            ]['rate'].values[0]
            if not df_rates[
                (df_rates["pet_type"] == row["pettype"]) &
                (df_rates["scheme"] == row["scheme"]) &
                ((df_rates["factor"] == "dog_breed") | (df_rates["factor"] == "cat_breed")) &
                (df_rates["option"] == row["breed"])
            ].empty
            else None # avoid IndexError if nothing matches
        ),
        axis=1
    )

    # Remaining factors
    factors = {
        "pet_age_gender_factor": ("pet_age_gender", "pet_age_gender"),
        "pet_age_factor": ("pet_age", "pet_age"),
        "pet_price_factor": ("pet_price", "pet_price"),
        "neutered_gender_factor": ("neutered_gender", "neutered_gender"),
        "chipped_factor": ("chipped", "chipped"),
        "vaccinations_factor": ("vaccinations", "vaccinations"),
        "pre_existing_factor": ("pre_existing", "pre_existing"),
        "aggressive_factor": ("aggressive", "aggressive"),
        "is_pet_yours_factor": ("is_pet_yours", "is_pet_yours"),
        "postcode_factor": ("postcode", "postcode"),
        "uk_resident_factor": ("uk_resident", "uk_resident"),
        "kept_at_address_factor": ("kept_at_address", "kept_at_address"),
        "trade_business_factor": ("trade_business", "trade_business"),
        "ph_age_factor": ("ph_age", "ph_age"),
        "copay_factor": ("copay", "copay"),
        "multipet_factor": ("multipet", "multipet"),
        
    }

    for new_col, (factor_name, option_col) in factors.items():
        df_merged[new_col] = df_merged.apply(
            lambda row: (
                df_rates[
                    (df_rates["pet_type"] == row["pettype"]) &
                    (df_rates["scheme"] == row["scheme"]) &
                    (df_rates["factor"] == factor_name) &
                    (df_rates["option"] == row[option_col])
                ]["rate"].values[0]
                if not df_rates[
                    (df_rates["pet_type"] == row["pettype"]) &
                    (df_rates["scheme"] == row["scheme"]) &
                    (df_rates["factor"] == factor_name) &
                    (df_rates["option"] == row[option_col])
                ].empty
                else None  # avoid IndexError if nothing matches
            ),
            axis=1
        )

    df_merged["re_rated_gwp_per_pet"] = df_merged.eval(
        "base_rate * pet_age_factor * pet_age_gender_factor * breed_factor * pet_price_factor *"
        "neutered_gender_factor * chipped_factor * vaccinations_factor * pre_existing_factor *"
        "aggressive_factor * is_pet_yours_factor * postcode_factor * uk_resident_factor *"
        "kept_at_address_factor * trade_business_factor * ph_age_factor * copay_factor * multipet_factor"
    )
    df_merged["re_rated_gwp_per_pol"] = df_merged.groupby(
        ["policy_number", "adjustment_number"]
        )["re_rated_gwp_per_pet"].transform("sum")
    
    print(df_merged)
    df_merged.to_csv(r'C:\Users\jorda\OneDrive\Desktop\df_merged_export.csv', index=False)

    # Convert DataFrame to list of dicts for template rendering
    policies = df_merged.to_dict(orient="records")


    return render(request, "base/rates/re_rated_policies.html", {"policies": policies})



def test(request):

    return render(request, "base/rates/test.html")

