"""
URL configuration for shodan project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.admin.sites import AdminSite
from django.urls import path, include

from two_factor.admin import AdminSiteOTPRequiredMixin
from two_factor.views import (
    BackupTokensView, DisableView, LoginView, ProfileView,
    QRGeneratorView, SetupCompleteView, SetupView,
)

from shodan import views

# Gate the Django admin behind two-factor authentication. We reassign the
# default admin.site instance's class to one mixing in AdminSiteOTPRequiredMixin,
# which overrides has_permission() to require request.user.is_verified(). This
# keeps all existing model registrations on admin.site intact while enforcing
# OTP for every admin request. See HLD U10.7.
class OTPAdminSite(AdminSiteOTPRequiredMixin, AdminSite):
    pass


admin.site.__class__ = OTPAdminSite

admin.site.site_header = "Shodan Dojo Admin"
admin.site.site_title = "Shodan Admin Portal"
admin.site.index_title = "Welcome to Shodan Dojo Admin Portal"


# After the TOTP setup wizard completes, reveal the one-time backup codes
# instead of the stock "setup complete" page. See HLD U10.12.
class ShodanSetupView(SetupView):
    success_url = 'backup_reveal'


two_factor_urlpatterns = [
    path('account/login/', LoginView.as_view(), name='login'),
    path('account/two_factor/setup/', ShodanSetupView.as_view(), name='setup'),
    path('account/two_factor/qrcode/', QRGeneratorView.as_view(), name='qr'),
    path('account/two_factor/setup/complete/', SetupCompleteView.as_view(), name='setup_complete'),
    path('account/two_factor/backup/tokens/', BackupTokensView.as_view(), name='backup_tokens'),
    path('account/two_factor/', ProfileView.as_view(), name='profile'),
    path('account/two_factor/disable/', DisableView.as_view(), name='disable'),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('account/two_factor/backup-reveal/', views.backup_reveal, name='backup_reveal'),
    path('', include((two_factor_urlpatterns, 'two_factor'))),
    path('', include('web.urls')),
    path('dev/error', views.dev_error, name='dev_error'),
    path('protected/files/<path:path>', views.protected_file, name='protected_file'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
