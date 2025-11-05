from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    # path('policy_list/', views.policy_list, name='policy_list'),
    # path('gwp-summaries/', views.gwp_summaries, name='gwp-summary'),
    path('rates/', views.rates, name='rates'),
    path('rates/prem_calc/', views.prem_calc, name='prem_calc'),
    path("rates/get_pet_rates/", views.get_pet_rates, name="get_pet_rates"),
    path('rates/base_rates/', views.base_rates, name='base_rates'),
    path('rates/postcode/', views.postcode, name='postcode'),
    path('rates/breed/', views.breed, name='breed'),
    path('rates/multipet/', views.multipet, name='multipet'),
    path('rates/copay/', views.copay, name='copay'),
    path('rates/chipped/', views.chipped, name='chipped'),
    path('rates/ph_age/', views.ph_age, name='ph_age'),
    path('rates/pet_age/', views.pet_age, name='pet_age'),
    path('rates/pet_price/', views.pet_price, name='pet_price'),
    path('rates/neutered/', views.neutered, name='neutered'),
    path('rates/pet_age_gender/', views.pet_age_gender, name='pet_age_gender'),
    path('rates/vaccinations/', views.vaccinations, name='vaccinations'),
    path('rates/pre_existing/', views.pre_existing, name='pre_existing'),
    path('rates/aggressive/', views.aggressive, name='aggressive'),
    path('rates/re_rate_policies/', views.re_rate_policies, name='re_rate_policies'),
    path('rates/test/', views.test, name='test'),
]