from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User, Student, Company, University, Faculty, Department
from offers.models import Skill 
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

# --- JWT: ROLE & JURISDICTION INJECTION ---
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    LOGIC: Security Token Orchestration.
    We override the default JWT payload to include the user's role and their 
    institutional scope. This allows the React frontend to perform 'Route Guarding'
    and display the correct dashboard (Superadmin vs Departmental Admin) 
    immediately after the handshake.
    """
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        token['email'] = user.email
        
        if hasattr(user, 'admin_profile'):
            try:
                admin = user.admin_profile
                if admin.department:
                    token['department_id'] = admin.department.id
                    token['department'] = admin.department.name
                else:
                    token['department_id'] = None
                    token['department'] = None
                token['faculty_id'] = admin.faculty.id if admin.faculty else None
                token['university_id'] = admin.university.id if admin.university else None
            except Exception:
                token['department_id'] = None
                token['department'] = None
                token['faculty_id'] = None
                token['university_id'] = None
        return token

# --- INSTITUTIONAL DISCOVERY SERIALIZERS ---
class UniversitySerializer(serializers.ModelSerializer):
    class Meta:
        model = University
        fields = '__all__'

class FacultySerializer(serializers.ModelSerializer):
    class Meta:
        model = Faculty
        fields = '__all__'

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = '__all__'

# --- ACTOR REGISTRATION ENGINES ---

class StudentRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    
    class Meta:
        model = User
        fields = ['email', 'password']

    def validate_email(self, value):
        if not value.endswith('.dz'):
            raise serializers.ValidationError("Please use your professional .dz university email.")
        return value

    def create(self, validated_data):
        req_data = self.context['request'].data
        
        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            password=validated_data['password'],
            role=User.STUDENT,
        )
        
        Student.objects.create(
            user=user,
            firstName=req_data.get('firstName', ''),
            lastName=req_data.get('lastName', ''),
            phoneNumber=req_data.get('phoneNumber', ''),
            univWillaya=req_data.get('univWillaya', ''),
            university_id=req_data.get('university'), 
            faculty_id=req_data.get('faculty'),       
            department_id=req_data.get('department'), 
        )
        return user

class CompanyRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    
    class Meta:
        model = User
        fields = ['email', 'password']

    def create(self, validated_data):
        req_data = self.context['request'].data
        files = self.context['request'].FILES
        
        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            password=validated_data['password'],
            role=User.COMPANY,
        )
        
        Company.objects.create(
            user=user,
            companyName=req_data.get('companyName', ''),
            description=req_data.get('description', ''),
            location=req_data.get('location', ''),
            website=req_data.get('website', ''),
            phoneNumber=req_data.get('phoneNumber', ''),
            registreCommerce=files.get('registreCommerce'),
        )
        return user

# --- DATA MODIFICATION LAYER ---

class StudentUpdateSerializer(serializers.ModelSerializer):
    skills = serializers.PrimaryKeyRelatedField(many=True, queryset=Skill.objects.all(), required=False)
    
    class Meta:
        model = Student
        fields = [
            'phoneNumber', 
            'univWillaya', 
            'githubLink', 
            'portfolioLink', 
            'IDCardNumber', 
            'socialSecurityNumber',
            'university', 
            'faculty', 
            'department', 
            'skills'
        ]

    def update(self, instance, validated_data):
        skill_ids = validated_data.pop('skills', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if skill_ids is not None:
            instance.skills.set(skill_ids)
        return instance

class CompanyUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['companyName', 'location', 'description', 'website', 'phoneNumber', 'registreCommerce']