from django.urls import path
from . import views

urlpatterns = [
    # ── STUDENT PIPELINE ──
    path('applications/apply/', views.apply_to_offer),
    path('applications/<int:application_id>/', views.get_application),
    path('student/applications/', views.get_student_applications),
    path('student/my-applications/', views.get_student_applications),

    # ── COMPANY PIPELINE ──
    path('company/applications/', views.get_company_applications),
    path('company/applications/<int:application_id>/accept/', views.accept_application),
    path('company/applications/<int:application_id>/refuse/', views.refuse_application),
    path('company/internships/<int:internship_id>/mark-ended/', views.company_mark_internship_ended),

    # ── ADMINISTRATIVE GOVERNANCE (Hierarchical) ──
    # The Full Pipeline: Used for status filter tabs in the UI
    path('admin/applications/', views.get_all_applications_for_admin),
    
    # The Validation Queue: Filtered for ACCEPTED status
    path('admin/pending-validations/', views.get_accepted_for_admin),
    
    # The Certification Queue: Filtered for PENDING_CERT status
    path('admin/pending-certifications/', views.get_pending_certifications),
    
    # Execution Endpoints (Transactions)
    path('admin/validate/<int:application_id>/', views.admin_validate_internship),
    path('admin/internships/<int:internship_id>/issue-certificate/', views.admin_issue_certificate),

    # ── NOTIFICATIONS & FEEDBACK ──
    path('notifications/', views.get_notifications),
    path('student/notifications/', views.get_notifications),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read),
    path('student/notifications/read-all/', views.mark_all_notifications_read),
]