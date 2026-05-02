from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

# Core Identity Models
from accounts.models import User, Company, Admin, Student

# Marketplace & Workflow Models (ADDED FOR STATISTICS)
from offers.models import InternshipOffer
from applications.models import Application, Internship, Agreement

# ── PRIVATE HELPERS: SECURITY GUARDS ─────────────────────────────────────────

def _require_admin(request):
    try:
        return Admin.objects.get(user=request.user), None
    except Admin.DoesNotExist:
        return None, Response({'error': 'Institutional Admin profile required'}, status=403)

def _require_dean(request):
    admin, err = _require_admin(request)
    if err: return None, err
    # Logic: is_dean property checks if department is NULL
    if not admin.is_dean:
        return None, Response({'error': 'Access Denied: Dean level authority required.'}, status=403)
    return admin, None


# ── STUDENT DIRECTORY & DETAILS ──────────────────────────────────────────────

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
            # FIXED: Serialize department name string, not the model object
            'department': s.department.name if s.department else None,
            'univWillaya': s.univWillaya,
            'isPlaced': Application.objects.filter(student=s, applicationStatus='VALIDATED').exists(),
        })
    return Response(data)

@api_view(['GET'])
def get_student_detail(request, student_id):
    """
    LOGIC: Full academic profile for a single student.
    Returns all fields needed by the AdminStudentDetail component.
    """
    admin, err = _require_admin(request)
    if err: return err

    student = get_object_or_404(Student, id=student_id)

    # SILO GUARD: prevent department heads from accessing students outside their scope
    if admin.department and student.department != admin.department:
        return Response({'error': 'Access denied: student outside your department.'}, status=403)

    # Fetch history for the detail view
    applications = Application.objects.filter(student=student).select_related('offer', 'offer__company')

    apps_data = []
    for a in applications:
        apps_data.append({
            'id': a.id,
            'status': a.applicationStatus,
            'offer': {'title': a.offer.title},
            'company_name': a.offer.company.companyName,
            'matching_score': a.matchingScore,
            'applied_at': str(a.applicationDate),
        })

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
        # ABSOLUTE URIs: Ensuring files are reachable from React
        'cvUrl': request.build_absolute_uri(student.cvFile.url) if student.cvFile else None,
        'photoUrl': request.build_absolute_uri(student.profile_photo.url) if student.profile_photo else None,
        'skills': [{'id': s.id, 'skillName': s.skillName} for s in student.skills.all()],
        'isPlaced': Application.objects.filter(student=student, applicationStatus='VALIDATED').exists(),
        'applications': apps_data,
    })


# ── CORPORATE MANAGEMENT (DEAN ONLY) ────────────────────────────────────────

@api_view(['GET'])
def get_pending_companies(request):
    admin, err = _require_dean(request)
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
    admin, err = _require_dean(request)
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
            'phoneNumber': c.phoneNumber,
            'registreCommerce': request.build_absolute_uri(c.registreCommerce.url) if c.registreCommerce else None,
            'isBlacklisted': c.isBlacklisted,
            'totalOffers': c.offers.count(),
        })
    return Response(data)


# ── STATISTICS (EXPANDED ANALYTICS) ─────────────────────────────────────────

@api_view(['GET'])
def get_statistics(request):
    """
    LOGIC: Hardened Scoped KPIs.
    Returns 13 fields to power the advanced Admin Statistics dashboard.
    """
    admin, err = _require_admin(request)
    if err: return err

    student_qs = Student.objects.all()
    app_qs = Application.objects.all()

    # Apply Horizontal Isolation
    if admin.department:
        student_qs = student_qs.filter(department=admin.department)
        app_qs = app_qs.filter(student__department=admin.department)

    total_students = student_qs.count()
    placed = app_qs.filter(applicationStatus='VALIDATED').values('student').distinct().count()
    total_apps = app_qs.count()

    return Response({
        'scope': 'Faculty-Wide' if not admin.department else f"Dept: {admin.department.name}",
        'total_students': total_students,
        'placed_students': placed,
        'unplaced_students': total_students - placed,
        'total_companies': Company.objects.filter(isApproved=True).count(),
        'pending_companies': Company.objects.filter(isApproved=False, isBlacklisted=False).count(),
        'total_offers': InternshipOffer.objects.count(),
        'total_applications': total_apps,
        'pending_applications': app_qs.filter(applicationStatus='PENDING').count(),
        'accepted_applications': app_qs.filter(applicationStatus='ACCEPTED').count(),
        'validated_applications': app_qs.filter(applicationStatus='VALIDATED').count(),
        'refused_applications': app_qs.filter(applicationStatus='REFUSED').count(),
        'pending_validations': app_qs.filter(applicationStatus='ACCEPTED').count(),
    })


# ── AGREEMENT HISTORY ────────────────────────────────────────────────────────

@api_view(['GET'])
def get_all_agreements(request):
    admin, err = _require_admin(request)
    if err: return err

    queryset = Agreement.objects.filter(status='VALIDATED').select_related(
        'internship__application__student', 
        'internship__application__offer__company'
    )
    
    if admin.department:
        queryset = queryset.filter(internship__application__student__department=admin.department)
        
    data = []
    for ag in queryset:
        app = ag.internship.application
        data.append({
            'id': ag.id,
            'student': f"{app.student.firstName} {app.student.lastName}",
            # FIXED: Serialize department name string
            'dept': app.student.department.name if app.student.department else None,
            'company': app.offer.company.companyName,
            'offer': app.offer.title, # ADDED AS PER AUDIT
            'generatedOn': str(ag.generationDate), # ADDED AS PER AUDIT
            'pdfUrl': request.build_absolute_uri(ag.pdfUrl.url) if ag.pdfUrl else None,
        })
    return Response(data)

# ── DEAN UTILITIES ───────────────────────────────────────────────────────────

@api_view(['PUT'])
def approve_company(request, company_id):
    admin, err = _require_dean(request)
    if err: return err
    company = get_object_or_404(Company, id=company_id)
    company.isApproved = True
    company.save()
    return Response({'message': f'{company.companyName} approved.'})

@api_view(['PUT'])
def refuse_company(request, company_id):
    admin, err = _require_dean(request)
    if err: return err
    company = get_object_or_404(Company, id=company_id)
    company.delete()
    return Response({'message': 'Company removed.'})

@api_view(['PUT'])
def blacklist_company(request, company_id):
    admin, err = _require_dean(request)
    if err: return err
    company = get_object_or_404(Company, id=company_id)
    company.isBlacklisted = True
    company.isApproved = False
    company.save()
    return Response({'message': 'Company blacklisted.'})

@api_view(['GET'])
def get_blacklisted_companies(request):
    admin, err = _require_dean(request)
    if err: return err
    companies = Company.objects.filter(isBlacklisted=True)
    data = [{'id': c.id, 'companyName': c.companyName, 'email': c.user.email} for c in companies]
    return Response(data)