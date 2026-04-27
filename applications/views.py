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


# ── STUDENT: RECRUITMENT PHASE ──

@api_view(['POST'])
def apply_to_offer(request):
    try:
        student = Student.objects.get(user=request.user)
        offer_id = request.data.get('offer_id')
        offer = get_object_or_404(InternshipOffer, id=offer_id)

        if not offer.is_recruitment_open:
            return Response({'error': 'Applications closed or capacity reached.'}, status=400)

        if Application.objects.filter(student=student, offer=offer).exists():
            return Response({'error': 'You already applied to this offer.'}, status=400)

        score = calculate_matching_score(student, offer)
        Application.objects.create(student=student, offer=offer, matchingScore=score)
        return Response({'message': 'Success', 'matchingScore': score}, status=201)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


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
                'id': a.id,
                'offerTitle': a.offer.title,
                'company': a.offer.company.companyName,
                'status': a.applicationStatus,
                'internshipStatus': a.internship.status if hasattr(a, 'internship') else None,
                'matchingScore': a.matchingScore,
                'appliedAt': str(a.applicationDate),
                'pdfAgreement': pdf_agreement,
                'pdfCertificate': pdf_certificate,
            })
        return Response(data)
    except:
        return Response(status=404)


@api_view(['GET'])
def get_application(request, application_id):
    app = get_object_or_404(Application, id=application_id, student__user=request.user)
    return Response({'id': app.id, 'status': app.applicationStatus, 'score': app.matchingScore})


# ── COMPANY: SUPERVISION PHASE ──

@api_view(['GET'])
def get_company_applications(request):
    try:
        company = Company.objects.get(user=request.user)
        apps = Application.objects.filter(offer__company=company).select_related('student', 'student__user').order_by('-matchingScore')
        data = []
        for a in apps:
            data.append({
                'id': a.id,
                'status': a.applicationStatus,
                'internshipStatus': a.internship.status if hasattr(a, 'internship') else None,
                'internshipId': a.internship.id if hasattr(a, 'internship') else None,
                'matchingScore': a.matchingScore,
                'student': {
                    'firstName': a.student.firstName, 'lastName': a.student.lastName,
                    'email': a.student.user.email,
                    'cv': request.build_absolute_uri(a.student.cvFile.url) if a.student.cvFile else None,
                    'skills': [s.skillName for s in a.student.skills.all()]
                },
                'offer': a.offer.title
            })
        return Response(data)
    except:
        return Response(status=403)


@api_view(['PUT'])
def accept_application(request, application_id):
    """FIXED: Added missing function requested by urls.py"""
    company = get_object_or_404(Company, user=request.user)
    app = get_object_or_404(Application, id=application_id, offer__company=company)
    if app.applicationStatus != 'PENDING':
        return Response({'error': 'Already processed.'}, status=400)
    app.applicationStatus = 'ACCEPTED'
    app.save()
    Notification.objects.create(user=app.student.user, message=f"Accepted by {company.companyName}. Admin notified.")
    return Response({'message': 'Accepted'})


@api_view(['PUT'])
def refuse_application(request, application_id):
    company = get_object_or_404(Company, user=request.user)
    app = get_object_or_404(Application, id=application_id, offer__company=company)
    reason = request.data.get('reason', 'No reason provided.')
    app.applicationStatus = 'REFUSED'
    app.save()
    Notification.objects.create(user=app.student.user, message=f"Application refused. Reason: {reason}")
    return Response({'message': 'Refused'})


@api_view(['POST'])
def company_mark_internship_ended(request, internship_id):
    try:
        company = Company.objects.get(user=request.user)
        internship = get_object_or_404(Internship, id=internship_id, application__offer__company=company)
        if date.today() < internship.endDate:
            return Response({'error': 'Internship period not yet over.'}, status=400)
        internship.status = Internship.PENDING_CERT
        internship.save()
        return Response({'message': 'Success. Awaiting University certification.'})
    except:
        return Response(status=403)


# ── ADMIN: GOVERNANCE PHASE ──

@api_view(['GET'])
def get_accepted_for_admin(request):
    try:
        admin = Admin.objects.get(user=request.user)
        qs = Application.objects.filter(applicationStatus='ACCEPTED')
        if not admin.is_superadmin:
            qs = qs.filter(student__department=admin.department)
        data = [{'id': a.id, 'student': f"{a.student.firstName} {a.student.lastName}", 'dept': a.student.department.name, 'company': a.offer.company.companyName, 'offer': a.offer.title} for a in qs]
        return Response(data)
    except:
        return Response(status=403)


@api_view(['POST'])
def admin_validate_internship(request, application_id):
    try:
        admin = Admin.objects.get(user=request.user)
        query_params = {'id': application_id, 'applicationStatus': 'ACCEPTED'}
        if not admin.is_superadmin:
            query_params['student__department'] = admin.department
        app = get_object_or_404(Application, **query_params)

        internship, _ = Internship.objects.get_or_create(
            application=app,
            defaults={'startDate': app.offer.internshipStartDate, 'endDate': app.offer.internshipEndDate, 'topic': app.offer.title, 'supervisorName': f"Admin {admin.lastName}", 'status': Internship.ONGOING}
        )
        pdf_file = generate_agreement_pdf(app, admin)
        Agreement.objects.update_or_create(internship=internship, defaults={'admin': admin, 'pdfUrl': pdf_file})
        app.applicationStatus = 'VALIDATED'
        app.save()
        return Response({'message': 'Agreement Generated'}, status=201)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
def admin_issue_certificate(request, internship_id):
    try:
        admin = Admin.objects.get(user=request.user)
        query_params = {'id': internship_id, 'status': Internship.PENDING_CERT}
        if not admin.is_superadmin:
            query_params['application__student__department'] = admin.department
        internship = get_object_or_404(Internship, **query_params)

        pdf_file = generate_certificate_pdf(internship, admin)
        Certificate.objects.create(internship=internship, admin=admin, pdfUrl=pdf_file)
        internship.status = Internship.COMPLETED
        internship.save()
        return Response({'message': 'Certificate issued.'}, status=201)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


# ── NOTIFICATIONS ──

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
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return Response({'message': 'All read'})