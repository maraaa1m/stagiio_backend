from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.conf import settings
from datetime import date

from .models import Application, Internship, Agreement, Certificate, Notification
from .serializers import NotificationSerializer
from accounts.models import Student, Company, Admin
from offers.models import InternshipOffer
from utils.matching import calculate_matching_score
from utils.pdf_generator import generate_agreement_pdf, generate_certificate_pdf

# ── PRIVATE HELPER ──
def _require_admin(request):
    try:
        return Admin.objects.get(user=request.user), None
    except Admin.DoesNotExist:
        return None, Response({'error': 'Admin profile required'}, status=403)

# ── STUDENT OPERATIONS ──

@api_view(['POST'])
def apply_to_offer(request):
    try:
        student = Student.objects.get(user=request.user)
        offer_id = request.data.get('offer_id')
        offer = get_object_or_404(InternshipOffer, id=offer_id)
        if not offer.is_recruitment_open:
            return Response({'error': 'Offer is closed or full'}, status=400)
        if Application.objects.filter(student=student, offer=offer).exists():
            return Response({'error': 'Already applied'}, status=400)
        score = calculate_matching_score(student, offer)
        Application.objects.create(student=student, offer=offer, matchingScore=score)
        return Response({'message': 'Success', 'matchingScore': score}, status=201)
    except Exception as e: return Response({'error': str(e)}, status=500)

@api_view(['GET'])
def get_student_applications(request):
    try:
        student = Student.objects.get(user=request.user)
        apps = Application.objects.filter(student=student).select_related('offer', 'offer__company').order_by('-applicationDate')
        data = []
        for a in apps:
            pdf_agreement = request.build_absolute_uri(a.internship.agreement.pdfUrl.url) if hasattr(a, 'internship') and hasattr(a.internship, 'agreement') and a.internship.agreement.pdfUrl else None
            pdf_certificate = request.build_absolute_uri(a.internship.certificate.pdfUrl.url) if hasattr(a, 'internship') and hasattr(a.internship, 'certificate') and a.internship.certificate.pdfUrl else None
            data.append({
                'id': a.id, 'offer_id': a.offer.id, 'offerTitle': a.offer.title, 'company': a.offer.company.companyName,
                'status': a.applicationStatus, 'internshipStatus': a.internship.status if hasattr(a, 'internship') else None,
                'matchingScore': a.matchingScore, 'appliedAt': str(a.applicationDate), 'pdfUrl': pdf_agreement, 'pdfCertificate': pdf_certificate
            })
        return Response(data)
    except: return Response(status=404)

@api_view(['GET'])
def get_application(request, application_id):
    try:
        app = get_object_or_404(Application, id=application_id, student__user=request.user)
        return Response({
            'id': app.id, 'status': app.applicationStatus, 'matchingScore': app.matchingScore,
            'offerTitle': app.offer.title, 'company': app.offer.company.companyName, 'appliedAt': str(app.applicationDate)
        })
    except: return Response(status=404)

# ── COMPANY OPERATIONS ──

@api_view(['GET'])
def get_company_applications(request):
    try:
        company = Company.objects.get(user=request.user)
        apps = Application.objects.filter(offer__company=company).select_related('student', 'student__user', 'internship').order_by('-matchingScore')
        data = []
        for a in apps:
            data.append({
                'id': a.id, 'status': a.applicationStatus, 'matchingScore': a.matchingScore,
                'internshipId': a.internship.id if hasattr(a, 'internship') else None,
                'internshipStatus': a.internship.status if hasattr(a, 'internship') else None,
                'student': {
                    'firstName': a.student.firstName, 'lastName': a.student.lastName, 'email': a.student.user.email,
                    'photo': request.build_absolute_uri(a.student.profile_photo.url) if a.student.profile_photo else None,
                    'cv': request.build_absolute_uri(a.student.cvFile.url) if a.student.cvFile else None,
                    'skills': [s.skillName for s in a.student.skills.all()]
                },
                'offer': a.offer.title
            })
        return Response(data)
    except: return Response(status=403)

@api_view(['PUT'])
def accept_application(request, application_id):
    company = get_object_or_404(Company, user=request.user)
    app = get_object_or_404(Application, id=application_id, offer__company=company)
    app.applicationStatus = 'ACCEPTED'
    app.save()
    Notification.objects.create(user=app.student.user, message=f"Accepted by {company.companyName}.")
    return Response({'message': 'Accepted'})

@api_view(['PUT'])
def refuse_application(request, application_id):
    company = get_object_or_404(Company, user=request.user)
    app = get_object_or_404(Application, id=application_id, offer__company=company)
    app.applicationStatus = 'REFUSED'
    app.refusalReason = request.data.get('reason', '')
    app.save()
    Notification.objects.create(user=app.student.user, message=f"Refused by {company.companyName}.")
    return Response({'message': 'Refused'})

@api_view(['POST'])
def company_mark_internship_ended(request, internship_id):
    company = get_object_or_404(Company, user=request.user)
    internship = get_object_or_404(Internship, id=internship_id, application__offer__company=company)
    internship.status = Internship.PENDING_CERT
    internship.save()
    return Response({'message': 'Ended'})

# ── ADMIN OPERATIONS (GOVERNANCE) ──

@api_view(['GET'])
def get_all_applications_for_admin(request):
    admin, err = _require_admin(request)
    if err: return err
    qs = Application.objects.select_related('student', 'student__user', 'offer', 'offer__company')
    if not admin.is_superadmin:
        qs = qs.filter(student__department=admin.department)
    data = []
    for a in qs:
        data.append({
            'id': a.id, 'status': a.applicationStatus, 'student': f"{a.student.firstName} {a.student.lastName}",
            'email': a.student.user.email, 'photo': request.build_absolute_uri(a.student.profile_photo.url) if a.student.profile_photo else None,
            'offer': a.offer.title, 'company': a.offer.company.companyName, 'score': a.matchingScore
        })
    return Response(data)

@api_view(['GET'])
def get_accepted_for_admin(request):
    admin, err = _require_admin(request)
    if err: return err
    qs = Application.objects.filter(applicationStatus='ACCEPTED').select_related('student', 'student__user', 'offer', 'offer__company')
    if not admin.is_superadmin:
        qs = qs.filter(student__department=admin.department)
    data = [{'id': a.id, 'student': f"{a.student.firstName} {a.student.lastName}", 'email': a.student.user.email, 'dept': a.student.department.name if a.student.department else 'N/A', 'company': a.offer.company.companyName, 'offer': a.offer.title, 'score': a.matchingScore} for a in qs]
    return Response(data)

@api_view(['GET'])
def get_pending_certifications(request):
    admin, err = _require_admin(request)
    if err: return err
    qs = Internship.objects.filter(status=Internship.PENDING_CERT).select_related('application__student', 'application__offer__company')
    if not admin.is_superadmin:
        qs = qs.filter(application__student__department=admin.department)
    data = [{'id': i.id, 'student': f"{i.application.student.firstName} {i.application.student.lastName}", 'company': i.application.offer.company.companyName, 'offer': i.application.offer.title} for i in qs]
    return Response(data)

@api_view(['POST'])
def admin_validate_internship(request, application_id):
    admin, err = _require_admin(request)
    if err: return err
    app = get_object_or_404(Application, id=application_id, applicationStatus='ACCEPTED')
    s_date = request.data.get('startDate') or app.offer.internshipStartDate
    e_date = request.data.get('endDate') or app.offer.internshipEndDate
    topic = request.data.get('topic') or app.offer.title
    supervisor = request.data.get('supervisorName') or f"Admin {admin.lastName}"
    internship, _ = Internship.objects.get_or_create(application=app, defaults={'startDate': s_date, 'endDate': e_date, 'topic': topic, 'supervisorName': supervisor})
    pdf_file = generate_agreement_pdf(app, admin)
    Agreement.objects.update_or_create(internship=internship, defaults={'admin': admin, 'pdfUrl': pdf_file})
    app.applicationStatus = 'VALIDATED'
    app.save()
    return Response({'message': 'Success'}, status=201)

@api_view(['POST'])
def admin_issue_certificate(request, internship_id):
    admin, err = _require_admin(request)
    if err: return err
    internship = get_object_or_404(Internship, id=internship_id, status=Internship.PENDING_CERT)
    pdf_file = generate_certificate_pdf(internship, admin)
    Certificate.objects.create(internship=internship, admin=admin, pdfUrl=pdf_file)
    internship.status = Internship.COMPLETED
    internship.save()
    return Response({'message': 'Issued'}, status=201)

# ── NOTIFICATIONS (FIXED: Added missing read-all function) ──

@api_view(['GET'])
def get_notifications(request):
    notes = Notification.objects.filter(user=request.user).order_by('-created_at')
    serializer = NotificationSerializer(notes, many=True)
    return Response({'notifications': serializer.data, 'count': notes.filter(is_read=False).count()})

@api_view(['PUT'])
def mark_notification_read(request, notification_id):
    note = get_object_or_404(Notification, id=notification_id, user=request.user)
    note.is_read = True
    note.save()
    return Response({'message': 'Read'})

@api_view(['PUT'])
def mark_all_notifications_read(request):
    """FIX: Added missing function for the Read All endpoint."""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return Response({'message': 'All read'})