import pandas as pd
from django.shortcuts import render
from .models import *
from collections import defaultdict
from django.views.decorators.http import require_GET
from django.http import JsonResponse
from .utils import *
from base import static_data
from .forms import UserForms

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
    # Load cached data (no DB queries)
    static_data.load_re_rated_cache()
    df_merged = static_data.RE_RATED_CACHE

    # Filter Policy Records
    df_merged = df_merged[df_merged["decline_flag"] == "N"]
    df_merged = df_merged[df_merged["transaction_name"] == "New Business"]

    # Initialize defaults
    copay = None
    asat_date = None

    if request.method == 'POST':
        form = UserForms(request.POST)
        if form.is_valid():
            copay = form.cleaned_data['copay']
            asat_date = form.cleaned_data['asat_date']

            # Convert to float safely (since form returns string)
            try:
                asat_date = float(asat_date)
            except (TypeError, ValueError):
                asat_date = None

            print(f"Co-pay: {copay}, As At Date: {asat_date}")

            if asat_date is not None:
                df_merged["inception_month"] = df_merged["inception_month"].astype(float)
                df_merged = df_merged[df_merged["inception_month"] <= asat_date]

            # Filter by Co-pay only if not '*'
            if copay is not None and "copay" in df_merged.columns:
                if copay != '*':
                    df_merged = df_merged[df_merged["copay"] == copay]
    else:
        form = UserForms()

    # ---- Group and sum GWP fields by inception_month ----
    df_sum = (
        df_merged.groupby("inception_month", as_index=False)[["gwp_per_pet", "re_rated_gwp_per_pet"]]
        .sum()
        .rename(columns={"gwp_per_pet": "gwp", "re_rated_gwp_per_pet": "re_rated_gwp"})
        .sort_values("inception_month")

    )
    df_sum["rate_change"] = div0(df_sum["re_rated_gwp"], df_sum["gwp"]) - 1

    # Convert for template rendering
    sum_pols = df_sum.to_dict(orient="records")
    policies = df_merged.to_dict(orient="records")

    print(sum_pols)

    return render(
        request,
        "base/rates/re_rated_policies.html",
        {"policies": policies, "sum_pols": sum_pols, "form": form}
    )

def test(request):

    return render(request, "base/rates/test.html")

