from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

# Core Identity Models
from accounts.models import User, Company, Admin, Student

# Marketplace Models
from offers.models import InternshipOffer

# Workflow Models
from applications.models import Application, Agreement

# ── PRIVATE HELPER: SECURITY GUARD ──────────────────────────────────────────
def _require_admin(request):
    """
    Logic: Primary Access Control.
    Ensures the requester has an official 'Admin' profile linked to their account.
    """
    try:
        return Admin.objects.get(user=request.user), None
    except Admin.DoesNotExist:
        return None, Response({'error': 'Institutional Admin profile required'}, status=403)


# ── INSTITUTIONAL STUDENT DIRECTORY ──────────────────────────────────────────
@api_view(['GET'])
def get_all_students(request):
    """
    LOGIC: Departmental Data Siloing.
    - Dean (dept=NULL): Receives the full faculty directory.
    - Dept Head: Receives only students from their specific curriculum.
    Ensures compliance with academic data isolation rules.
    """
    admin, err = _require_admin(request)
    if err: return err
    
    # Query Scope Definition
    queryset = Student.objects.select_related('user')
    
    # MASTER SILO FILTER
    if admin.department:
        queryset = queryset.filter(department=admin.department)

    data = []
    for s in queryset:
        # Check placement status for instant UI badging
        is_placed = Application.objects.filter(student=s, applicationStatus='VALIDATED').exists()
        
        data.append({
            'id': s.id,
            'firstName': s.firstName,
            'lastName': s.lastName,
            'email': s.user.email,
            'department': s.department,
            'univWillaya': s.univWillaya,
            'isPlaced': is_placed,
            # Legal Audit: Admin can open the physical CV if required
            'cvUrl': request.build_absolute_uri(s.cvFile.url) if s.cvFile else None,
            'socialSecurityNumber': s.socialSecurityNumber # For administrative identity check
        })
    return Response(data)


# ── CORPORATE LEGAL AUDIT (DEAN ONLY) ────────────────────────────────────────
@api_view(['GET'])
def get_pending_companies(request):
    """
    LOGIC: Evidence-Based Onboarding.
    Only the Dean can perform this audit. The API provides absolute links to the 
    'Registre de Commerce' (PDF/Image) for legal verification.
    """
    admin, err = _require_admin(request)
    if err: return err
    
    # Security Gate: Department heads are blocked from corporate legal data
    if admin.department:
        return Response({'error': 'Access Denied: Only the Dean manages corporate trust.'}, status=403)

    companies = Company.objects.filter(isApproved=False, isBlacklisted=False)
    data = []
    for c in companies:
        data.append({
            'id': c.id,
            'companyName': c.companyName,
            'email': c.user.email,
            'location': c.location,
            # THE KEY: Absolute URL for the physical PDF/Image license
            'registreCommerce': request.build_absolute_uri(c.registreCommerce.url) if c.registreCommerce else None,
            'description': c.description,
        })
    return Response(data)


@api_view(['GET'])
def get_all_companies(request):
    """Logic: Returns the directory of currently trusted corporate partners."""
    admin, err = _require_admin(request)
    if err: return err
    companies = Company.objects.filter(isApproved=True, isBlacklisted=False)
    data = []
    for c in companies:
        data.append({
            'id': c.id,
            'companyName': c.companyName,
            'location': c.location,
            'website': c.website,
            'totalOffers': c.offers.count()
        })
    return Response(data)


@api_view(['PUT'])
def approve_company(request, company_id):
    """Logic: Institutional Approval Gate restricted strictly to the Dean."""
    admin, err = _require_admin(request)
    if err: return err
    if admin.department:
        return Response({'error': 'Unauthorized: Dean level approval required.'}, status=403)
    
    company = get_object_or_404(Company, id=company_id)
    company.isApproved = True
    company.save()
    return Response({'message': f'Company {company.companyName} officially approved by the Dean.'})


# ── GOVERNANCE STATISTICS ───────────────────────────────────────────────────
@api_view(['GET'])
def get_statistics(request):
    """
    LOGIC: Scoped KPI Aggregation.
    Calculates metrics (placed vs unplaced) based on the Admin's jurisdiction.
    Ensures stats are accurate for each departmental silo.
    """
    admin, err = _require_admin(request)
    if err: return err
    
    student_qs = Student.objects.all()
    app_qs = Application.objects.all()
    
    # Isolation Logic: If not Dean, reduce math scope to specific dept
    if admin.department:
        student_qs = student_qs.filter(department=admin.department)
        app_qs = app_qs.filter(student__department=admin.department)
        
    total_students = student_qs.count()
    placed = app_qs.filter(applicationStatus='VALIDATED').values('student').distinct().count()
    
    return Response({
        'scope': 'Faculty-Wide' if not admin.department else f"Dept: {admin.department}",
        'total_students': total_students,
        'placed_students': placed,
        'unplaced_students': total_students - placed,
        'total_companies': Company.objects.filter(isApproved=True).count(),
        'pending_validations': app_qs.filter(applicationStatus='ACCEPTED').count(),
    })


@api_view(['GET'])
def get_all_agreements(request):
    """Logic: Historical Audit list, siloed by department."""
    admin, err = _require_admin(request)
    if err: return err
    
    queryset = Agreement.objects.filter(status='VALIDATED').select_related(
        'internship__application__student'
    )
    
    # Silo Guard
    if admin.department:
        queryset = queryset.filter(internship__application__student__department=admin.department)
        
    data = []
    for ag in queryset:
        app = ag.internship.application
        data.append({
            'id': ag.id,
            'student': f"{app.student.firstName} {app.student.lastName}",
            'dept': app.student.department,
            'company': app.offer.company.companyName,
            'pdfUrl': request.build_absolute_uri(ag.pdfUrl.url) if ag.pdfUrl else None,
        })
    return Response(data)

# ── BLACKLISTING (DEAN ONLY) ───────────────────────────────────────────────
@api_view(['PUT'])
def refuse_company(request, company_id):
    admin, err = _require_admin(request)
    if err or admin.department: return Response(status=403)
    company = get_object_or_404(Company, id=company_id)
    company.delete()
    return Response({'message': 'Rejected'})

@api_view(['PUT'])
def blacklist_company(request, company_id):
    admin, err = _require_admin(request)
    if err or admin.department: return Response(status=403)
    company = get_object_or_404(Company, id=company_id)
    company.isBlacklisted = True
    company.isApproved = False
    company.save()
    return Response({'message': 'Blacklisted'})

@api_view(['GET'])
def get_blacklisted_companies(request):
    admin, err = _require_admin(request)
    if err or admin.department: return Response(status=403)
    companies = Company.objects.filter(isBlacklisted=True)
    data = [{'id': c.id, 'companyName': c.companyName, 'email': c.user.email} for c in companies]
    return Response(data)