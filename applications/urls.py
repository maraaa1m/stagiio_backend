from django.urls import path
from . import views

urlpatterns = [
    # ── STUDENT OPERATIONS ──
    # Logic: Initiates the recruitment phase and matching engine.
    path('applications/apply/', views.apply_to_offer),
    
    # Logic: Dashboards with departmental aliases to prevent frontend 404s.
    path('student/my-applications/', views.get_student_applications),
    path('student/applications/', views.get_student_applications), 

    # ── COMPANY OPERATIONS (Recruitment Phase) ──
    # Logic: Manage applicants before the contract is signed.
    path('company/applications/', views.get_company_applications),
    path('company/applications/<int:application_id>/accept/', views.accept_application),
    path('company/applications/<int:application_id>/refuse/', views.refuse_application),

    # ── COMPANY OPERATIONS (Operational Phase) ──
    # NEW Logic: The Company validates the end of professional tasks.
    # Triggers status: ONGOING -> PENDING_CERT.
    path('company/internships/<int:internship_id>/mark-ended/', views.company_mark_internship_ended),

    # ── ADMINISTRATIVE GOVERNANCE (Recruitment Validation) ──
    # Logic: Dean or Dept Head validates the start of the internship (Agreement).
    path('admin/pending-validations/', views.get_accepted_for_admin),
    path('admin/applications/', views.get_accepted_for_admin), # Frontend alias
    path('admin/validate/<int:application_id>/', views.admin_validate_internship),

    # ── ADMINISTRATIVE GOVERNANCE (Completion Validation) ──
    # NEW Logic: Dept Head verifies work end and generates the Certificate.
    # Triggers status: PENDING_CERT -> COMPLETED.
    path('admin/pending-certifications/', views.get_accepted_for_admin), # Reusing list logic with status filter
    path('admin/internships/<int:internship_id>/issue-certificate/', views.admin_issue_certificate),

    # ── NOTIFICATIONS & FEEDBACK ──
    # Logic: The system alert engine for multi-actor updates.
    path('notifications/', views.get_notifications),
    path('student/notifications/', views.get_notifications),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read),
]