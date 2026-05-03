from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    STUDENT = 'STUDENT'
    COMPANY = 'COMPANY'
    ADMIN = 'ADMIN'
    ROLE_CHOICES = [(STUDENT, 'Student'), (COMPANY, 'Company'), (ADMIN, 'Admin')]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, null=True, blank=True)

    def __str__(self):
        return self.email

class University(models.Model):
    name = models.CharField(max_length=255)
    wilaya = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = "Universities"

    def __str__(self):
        return self.name

class Faculty(models.Model):
    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name='faculties')
    name = models.CharField(max_length=255)

    class Meta:
        verbose_name_plural = "Faculties"

    def __str__(self):
        return f"{self.name} ({self.university.name})"

class Department(models.Model):
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name='departments')
    name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.name} ({self.faculty.name})"

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    firstName = models.CharField(max_length=100)
    lastName = models.CharField(max_length=100)
    IDCardNumber = models.CharField(max_length=50, unique=True, null=True, blank=True)
    socialSecurityNumber = models.CharField(max_length=50, unique=True, null=True, blank=True)
    phoneNumber = models.CharField(max_length=20)
    githubLink = models.URLField(blank=True, null=True)
    portfolioLink = models.URLField(blank=True, null=True)
    cvFile = models.FileField(upload_to='cvs/', blank=True, null=True)
    profile_photo = models.ImageField(upload_to='photos/', blank=True, null=True)
    univWillaya = models.CharField(max_length=100)

    # RELATIONAL LINKS
    university = models.ForeignKey(University, on_delete=models.PROTECT, related_name='students', null=True)
    faculty = models.ForeignKey(Faculty, on_delete=models.PROTECT, related_name='students', null=True)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='students', null=True)

    skills = models.ManyToManyField('offers.Skill', blank=True, related_name='students')

    def __str__(self):
        return f"{self.firstName} {self.lastName}"

class Company(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='company_profile')
    companyName = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    registreCommerce = models.FileField(upload_to='registres/', blank=True, null=True)
    location = models.CharField(max_length=100)
    website = models.URLField(blank=True, null=True)
    phoneNumber = models.CharField(max_length=20, blank=True, null=True)
    isApproved = models.BooleanField(default=False)
    isBlacklisted = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "Companies"

    def __str__(self):
        return self.companyName

class Admin(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='admin_profile')
    firstName = models.CharField(max_length=100)
    lastName = models.CharField(max_length=100)

    # ADMINISTRATIVE JURISDICTION
    university = models.ForeignKey(University, on_delete=models.CASCADE, null=True, blank=True)
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE, null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)

    @property
    def is_superadmin(self):
        """
        Logic: Per teacher's suggestion.
        If an admin is not restricted to a specific department, they possess
        Superadmin privileges for global institutional oversight.
        """
        return self.department is None

    @property
    def is_dean(self):
        """
        FIX 2: Alias for is_superadmin.
        applications/views.py references admin.is_dean throughout.
        Both properties return True when department is None (superadmin/dean level).
        """
        return self.department is None

    def __str__(self):
        if self.department:
            return f"{self.firstName} {self.lastName} (Head of {self.department.name})"
        return f"{self.firstName} {self.lastName} (Superadmin)"