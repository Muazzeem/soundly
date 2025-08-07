# adapters.py
from allauth.account.adapter import DefaultAccountAdapter
from django.http import HttpResponse

class CustomAccountAdapter(DefaultAccountAdapter):
    def respond_user_inactive(self, request, user):
        # For API: return an error response instead of redirect
        return HttpResponse("Account is inactive", status=403)
