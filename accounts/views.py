from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import (
    StudentRegisterSerializer,
    CompanyRegisterSerializer,
    StudentUpdateSerializer,
    CompanyUpdateSerializer,
    CustomTokenObtainPairSerializer,
    UniversitySerializer,
    FacultySerializer,
    DepartmentSerializer,
)
from .models import Student, Company, User, University, Faculty, Department
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail

# ── CUSTOM LOGIN ──
class CustomTokenObtainPairView(TokenObtainPairView):
    """Logic: Overrides JWT login to inject 'role' and 'department' into the token."""
    serializer_class = CustomTokenObtainPairSerializer

# ── HELPER: TOKEN ISSUANCE ──
def get_tokens_for_user(user):
    """Logic: Generates session keys. Role is added for immediate frontend routing."""
    refresh = RefreshToken.for_user(user)
    refresh['role'] = user.role
    return {'refresh': str(refresh), 'access': str(refresh.access_token)}

# ── HELPER: CANONICAL PROFILE BUILDER ──
def _build_student_profile(student, request):
    """
    LOGIC: Institutional Identity Assembly.
    Traverses the relational hierarchy to build a high-fidelity JSON profile.
    Ensures media links are absolute URIs for the React frontend.
    """
    def get_abs_url(field):
        if not field: return None
        return request.build_absolute_uri(field.url)

    return {
        'email':         student.user.email,
        'firstName':     student.firstName,
        'lastName':      student.lastName,
        'phoneNumber':   student.phoneNumber,
        'univWillaya':   student.univWillaya,
        'githubLink':    student.githubLink or '',
        'portfolioLink': student.portfolioLink or '',
        'photo':         get_abs_url(student.profile_photo),
        'cv':            get_abs_url(student.cvFile),
        
        # HIERARCHY DATA: Accessing names through Foreign Key relations
        'university':    student.university.name if student.university else "Not Set",
        'faculty':       student.faculty.name if student.faculty else "Not Set",
        'department':    student.department.name if student.department else "Not Set",
        'department_id': student.department.id if student.department else None,
        
        'socialSecurityNumber': student.socialSecurityNumber or 'Not Provided',
        'IDCardNumber':         student.IDCardNumber or 'Not Provided',
        'skills':        [{'id': s.id, 'skillName': s.skillName} for s in student.skills.all()],
    }

# ── INSTITUTIONAL DISCOVERY (PUBLIC) ──
# Logic: These APIs enable 'Chained Selects' in the registration form.

@api_view(['GET'])
@permission_classes([AllowAny])
def get_universities(request):
    """Returns the list of all participating Algerian Universities."""
    univs = University.objects.all().order_by('name')
    serializer = UniversitySerializer(univs, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_faculties(request, university_id):
    """Returns faculties belonging strictly to the selected University."""
    facs = Faculty.objects.filter(university_id=university_id).order_by('name')
    serializer = FacultySerializer(facs, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_departments(request, faculty_id):
    """Returns departments belonging strictly to the selected Faculty."""
    depts = Department.objects.filter(faculty_id=faculty_id).order_by('name')
    serializer = DepartmentSerializer(depts, many=True)
    return Response(serializer.data)

# ── ONBOARDING ──

@api_view(['POST'])
@permission_classes([AllowAny])
def register_student(request):
    """Logic: Orchestrates Student creation and assigns them to a Department silo."""
    serializer = StudentRegisterSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        user = serializer.save()
        return Response({'message': 'Success', **get_tokens_for_user(user)}, status=201)
    return Response(serializer.errors, status=400)

@api_view(['POST'])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser])
def register_company(request):
    """Logic: Captures corporate license (PDF) during the registration stream."""
    serializer = CompanyRegisterSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        user = serializer.save()
        return Response({'message': 'Success', **get_tokens_for_user(user)}, status=201)
    return Response(serializer.errors, status=400)

# ── PROFILE OPERATIONS ──

@api_view(['GET'])
def get_student_profile(request):
    try:
        student = Student.objects.get(user=request.user)
        return Response(_build_student_profile(student, request))
    except Student.DoesNotExist:
        return Response(status=404)

@api_view(['PUT'])
def update_student_profile(request):
    try:
        student = Student.objects.get(user=request.user)
        serializer = StudentUpdateSerializer(student, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Updated', 'data': _build_student_profile(student, request)})
        return Response(serializer.errors, status=400)
    except:
        return Response(status=404)

@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def upload_student_photo(request):
    try:
        student = Student.objects.get(user=request.user)
        student.profile_photo = request.FILES.get('photo')
        student.save()
        return Response({'url': request.build_absolute_uri(student.profile_photo.url)})
    except:
        return Response(status=400)

@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def upload_cv(request):
    try:
        student = Student.objects.get(user=request.user)
        student.cvFile = request.FILES.get('cv')
        student.save()
        return Response({'url': request.build_absolute_uri(student.cvFile.url)})
    except:
        return Response(status=400)

@api_view(['GET'])
def get_company_profile(request):
    try:
        company = Company.objects.get(user=request.user)
        return Response({
            'email':            request.user.email,
            'companyName':      company.companyName,
            'description':      company.description or '',
            'logo':             request.build_absolute_uri(company.logo.url) if company.logo else None,
            'registreCommerce': request.build_absolute_uri(company.registreCommerce.url) if company.registreCommerce else None,
            'location':         company.location,
            'website':          company.website or '',
            'phoneNumber':      company.phoneNumber or '',
            'isApproved':       company.isApproved,
        })
    except:
        return Response(status=404)

@api_view(['PUT'])
def update_company_profile(request):
    try:
        company = Company.objects.get(user=request.user)
        serializer = CompanyUpdateSerializer(company, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Success'})
        return Response(serializer.errors, status=400)
    except:
        return Response(status=404)

@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def upload_company_logo(request):
    try:
        company = Company.objects.get(user=request.user)
        company.logo = request.FILES.get('logo')
        company.save()
        return Response({'url': request.build_absolute_uri(company.logo.url)})
    except:
        return Response(status=400)

# ── SECURITY UTILITIES ──

@api_view(['POST'])
def logout(request):
    try:
        # Stateless termination: Adding the token to the server-side blacklist.
        token = RefreshToken(request.data.get('refresh'))
        token.blacklist()
        return Response(status=200)
    except:
        return Response(status=400)

@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_password(request):
    email = request.data.get('email', '').strip()
    try:
        user = User.objects.get(email=email)
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        reset_url = f"http://localhost:5173/reset-password/{uid}/{token}/"
        send_mail('Password Reset', f'Click here: {reset_url}', 'noreply@stag.io', [email])
    except:
        pass 
    return Response({'message': 'Email sent if account exists.'})

@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    """Logic: Verifies UID/Token and synchronizes new password to DB."""
    uidb64, token, new_password = request.data.get('uid'), request.data.get('token'), request.data.get('new_password')
    try:
        uid  = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
        if default_token_generator.check_token(user, token):
            user.set_password(new_password)
            user.save()
            return Response({'message': 'Success'})
        return Response({'error': 'Invalid token'}, status=400)
    except:
        return Response(status=400)