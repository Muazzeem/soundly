from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
import pycountry


@api_view(["GET"])
def country_list(request):
    search = request.GET.get("search", "").lower()
    countries = list(pycountry.countries)

    if search:
        countries = [c for c in countries if search in c.name.lower()]

    def get_flag_emoji(alpha_2):
        return chr(ord(alpha_2[0].upper()) + 127397) + chr(ord(alpha_2[1].upper()) + 127397)

    result = [
        {
            "name": c.name,
            "alpha_2": c.alpha_2,
            "alpha_3": c.alpha_3,
            "flag_url": f"https://flagcdn.com/w40/{c.alpha_2.lower()}.png",
        }
        for c in countries
    ]
    return Response(result, status=status.HTTP_200_OK)

