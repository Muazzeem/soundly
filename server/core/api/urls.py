from django.urls import path
from .views import country_list

urlpatterns = [
    path('countries', country_list, name='country-list'),
]
