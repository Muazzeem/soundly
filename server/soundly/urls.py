from django.conf import settings
from django.urls import include, path
from django.contrib import admin

from search import views as search_views
from soundly.views import api_root

from dj_rest_auth.views import LoginView, PasswordResetConfirmView
from dj_rest_auth.registration.views import RegisterView
from otp.api.views import ResendOTPView, VerifyOTPView
from users.api.views import CustomPasswordResetView


urlpatterns = [
    path("", api_root, name="api_root"),
    path("admin/", admin.site.urls),
    path("search/", search_views.search, name="search"),
    path("auth/signup/", RegisterView.as_view(), name="account_signup"),
    path("auth/login/", LoginView.as_view(), name="account_login"),
        # Your stuff: custom urls includes go here
    # ...
    path("api/", include("soundly.api_router")),
    path("auth/", include("dj_rest_auth.urls")),
    path('password/reset/', CustomPasswordResetView.as_view(), name='rest_password_reset'),
    path(
        'auth/password/reset/confirm/<uidb64>/<token>/',
        PasswordResetConfirmView.as_view(),
        name='password_reset_confirm'
    ),

    # OTP validation URLs
    path("auth/verify-otp/", VerifyOTPView.as_view(), name="verify_otp"),
    path("auth/resend-otp/", ResendOTPView.as_view(), name="resend_otp"),
]


if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)

urlpatterns = urlpatterns + [

]
