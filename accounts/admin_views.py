from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from accounts.models import User, Company, Admin, Student
from offers.models import InternshipOffer
from applications.models import Application, Internship, Agreement

# ── PRIVATE HELPERS ──

def _require_admin(request):
    try:
        return Admin.objects.get(user=request.user), None
    except Admin.DoesNotExist:
        return None, Response({'error': 'Institutional Admin profile required'}, status=403)

def _require_superadmin(request):
    """
    Logic: This is the 'Dean' gate renamed to 'Superadmin' as requested.
    Checks if the admin has no department assigned (The Global Boss).
    """
    admin, err = _require_admin(request)
    if err: return None, err
    # If department is None, they are the Superadmin
    if admin.department is not None:
        return None, Response({'error': 'Access Denied: Superadmin level authority required.'}, status=403)
    return admin, None

# ── STUDENT DIRECTORY ──

@api_view(['GET'])
def get_all_students(request):
    admin, err = _require_admin(request)
    if err: return err
    
    queryset = Student.objects.select_related('user', 'department')
    if admin.department:
        queryset = queryset.filter(department=admin.department)

    data = []
    for s in queryset:
        data.append({
            'id': s.id,
            'firstName': s.firstName,
            'lastName': s.lastName,
            'email': s.user.email,
            'photo': request.build_absolute_uri(s.profile_photo.url) if s.profile_photo else None,
            'department': s.department.name if s.department else None,
            'univWillaya': s.univWillaya,
            'isPlaced': Application.objects.filter(student=s, applicationStatus='VALIDATED').exists(),
        })
    return Response(data)

@api_view(['GET'])
def get_student_detail(request, student_id):
    admin, err = _require_admin(request)
    if err: return err
    student = get_object_or_404(Student, id=student_id)
    if admin.department and student.department != admin.department:
        return Response({'error': 'Access denied'}, status=403)

    apps = Application.objects.filter(student=student).select_related('offer', 'offer__company')
    return Response({
        'id': student.id,
        'firstName': student.firstName,
        'lastName': student.lastName,
        'email': student.user.email,
        'phoneNumber': student.phoneNumber,
        'univWillaya': student.univWillaya,
        'university': student.university.name if student.university else None,
        'faculty': student.faculty.name if student.faculty else None,
        'department': student.department.name if student.department else None,
        'IDCardNumber': student.IDCardNumber,
        'socialSecurityNumber': student.socialSecurityNumber,
        'githubLink': student.githubLink,
        'portfolioLink': student.portfolioLink,
        'cvUrl': request.build_absolute_uri(student.cvFile.url) if student.cvFile else None,
        'photoUrl': request.build_absolute_uri(student.profile_photo.url) if student.profile_photo else None,
        'skills': [{'id': s.id, 'skillName': s.skillName} for s in student.skills.all()],
        'applications': [{'id': a.id, 'status': a.applicationStatus, 'offer': a.offer.title, 'company': a.offer.company.companyName} for a in apps]
    })

# ── CORPORATE MANAGEMENT (SUPERADMIN ONLY) ──

@api_view(['GET'])
def get_pending_companies(request):
    admin, err = _require_superadmin(request)
    if err: return err
    companies = Company.objects.filter(isApproved=False, isBlacklisted=False)
    data = []
    for c in companies:
        data.append({
            'id': c.id,
            'companyName': c.companyName,
            'email': c.user.email,
            'location': c.location,
            'registreCommerce': request.build_absolute_uri(c.registreCommerce.url) if c.registreCommerce else None,
            'description': c.description,
        })
    return Response(data)

@api_view(['GET'])
def get_all_companies(request):
    """Returns the master list of approved corporate partners."""
    admin, err = _require_admin(request) # Any admin can view partners
    if err: return err
    companies = Company.objects.filter(isApproved=True).select_related('user')
    data = []
    for c in companies:
        data.append({
            'id': c.id,
            'companyName': c.companyName,
            'email': c.user.email,
            'location': c.location,
            'website': c.website,
            'totalOffers': c.offers.count(),
        })
    return Response(data)

# FIXED: Function name now matches Line 39 of accounts/urls.py
@api_view(['GET'])
def get_blacklisted_companies(request):
    admin, err = _require_superadmin(request)
    if err: return err
    companies = Company.objects.filter(isBlacklisted=True)
    data = [{'id': c.id, 'companyName': c.companyName, 'email': c.user.email} for c in companies]
    return Response(data)

# ── STATISTICS ──

@api_view(['GET'])
def get_statistics(request):
    admin, err = _require_admin(request)
    if err: return err
    student_qs = Student.objects.all()
    app_qs = Application.objects.all()
    if admin.department:
        student_qs = student_qs.filter(department=admin.department)
        app_qs = app_qs.filter(student__department=admin.department)

    accepted_count = app_qs.filter(applicationStatus='ACCEPTED').count()
    
    return Response({
        'scope': 'Faculty' if not admin.department else admin.department.name,
        'total_students': student_qs.count(),
        'placed_students': app_qs.filter(applicationStatus='VALIDATED').values('student').distinct().count(),
        'total_companies': Company.objects.filter(isApproved=True).count(),
        'total_offers': InternshipOffer.objects.count(),
        'pending_validations': accepted_count,
        'pending_agreements': accepted_count,
        'total_applications': app_qs.count(),
    })

# ── AGREEMENT AUDIT ──

@api_view(['GET'])
def get_all_agreements(request):
    admin, err = _require_admin(request)
    if err: return err
    queryset = Agreement.objects.filter(status='VALIDATED').select_related('internship__application__student')
    if admin.department:
        queryset = queryset.filter(internship__application__student__department=admin.department)
    data = []
    for ag in queryset:
        app = ag.internship.application
        data.append({
            'id': ag.id,
            'student': f"{app.student.firstName} {app.student.lastName}",
            'dept': app.student.department.name if app.student.department else 'N/A',
            'company': app.offer.company.companyName,
            'offer': app.offer.title,
            'generatedOn': str(ag.generationDate),
            'pdfUrl': request.build_absolute_uri(ag.pdfUrl.url) if ag.pdfUrl else None,
        })
    return Response(data)

# ── ACTIONS (SUPERADMIN ONLY) ──

@api_view(['PUT'])
def approve_company(request, company_id):
    admin, err = _require_superadmin(request)
    if err: return err
    company = get_object_or_404(Company, id=company_id)
    company.isApproved = True
    company.save()
    return Response({'message': 'Approved'})

@api_view(['PUT'])
def refuse_company(request, company_id):
    admin, err = _require_superadmin(request)
    if err: return err
    company = get_object_or_404(Company, id=company_id)
    company.delete()
    return Response({'message': 'Removed'})

@api_view(['PUT'])
def blacklist_company(request, company_id):
    admin, err = _require_superadmin(request)
    if err: return err
    company = get_object_or_404(Company, id=company_id)
    company.isBlacklisted = True
    company.isApproved = False
    company.save()
    return Response({'message': 'Blacklisted'})