from django.urls import path
from . import views

# FIX 5: Static paths MUST be declared before dynamic <int:offer_id> patterns.
# Previously 'offers/recommended/' and 'offers/expiring-soon/' were declared after
# 'offers/<int:offer_id>/' which causes Django to try matching the string "recommended"
# as an integer, failing silently in some versions and breaking in others.
urlpatterns = [
    # ── Static paths first ──
    path('offers/recommended/', views.get_recommended_offers),
    path('offers/expiring-soon/', views.get_expiring_soon),
    path('offers/create/', views.create_offer),
    path('offers/', views.get_offers),
    path('skills/', views.get_skills),
    path('student/skills/suggest/', views.suggest_skills),

    # ── Dynamic paths after all static ones ──
    path('offers/<int:offer_id>/', views.get_offer_detail),
    path('offers/<int:offer_id>/update/', views.update_offer),
    path('offers/<int:offer_id>/delete/', views.delete_offer),
    path('offers/<int:offer_id>/match-score/', views.get_match_score),
    path('offers/<int:offer_id>/match-report/', views.get_match_report),
]