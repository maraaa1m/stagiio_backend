from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # ── THE CONTROL TOWER ──
    # Logic: Direct entry point to the Django Admin interface. 
    # Standardized to '/admin/' to match the university's management expectations.
    path('admin/', admin.site.urls),

    # ── JWT TOKEN ROTATION ──
    # Logic: API #4 in your checklist. This endpoint allows the React frontend 
    # to exchange an expired access token for a new one using the refresh token, 
    # ensuring the student doesn't have to re-login every hour.
    path('api/auth/token/refresh/', TokenRefreshView.as_view()),

    # ── DECOUPLED APP DISCOVERY ──
    # Architect's Note: We use the 'include()' pattern to maintain a Modular Monolith.
    # Each app (accounts, offers, applications) manages its own internal routing logic.
    path('api/', include('accounts.urls')),
    path('api/', include('offers.urls')),
    path('api/', include('applications.urls')),
]

# ── MEDIA STREAMING BRIDGE ──
# Logic: This is the 'Static Gate'. During development (DEBUG=True), 
# this tells Django to act as a file server for the 'media/' folder. 
# This allows the Frontend to display the Student Photos and the Constantine 2 PDFs.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)