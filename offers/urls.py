from django.urls import path
from . import views

urlpatterns = [
    path('offers/', views.get_offers),
    path('offers/create/', views.create_offer),
    path('offers/<int:offer_id>/', views.get_offer_detail),
    path('offers/<int:offer_id>/update/', views.update_offer),
    path('offers/<int:offer_id>/delete/', views.delete_offer),
    path('offers/recommended/', views.get_recommended_offers),
    path('offers/<int:offer_id>/match-score/', views.get_match_score),
    path('offers/<int:offer_id>/match-report/', views.get_match_report),
    path('offers/expiring-soon/', views.get_expiring_soon),
    path('skills/', views.get_skills),
    path('student/skills/suggest/', views.suggest_skills),
]