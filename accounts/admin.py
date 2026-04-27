from django.contrib import admin
from .models import User, Student, Company, Admin as AdminProfile, University, Faculty, Department

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'username', 'role', 'is_staff')

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('firstName', 'lastName', 'department', 'univWillaya')

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('companyName', 'location', 'isApproved', 'isBlacklisted')
    readonly_fields = ('registreCommerce',)

@admin.register(AdminProfile)
class AdminProfileAdmin(admin.ModelAdmin):
    list_display = ('firstName', 'lastName', 'department', 'university')

@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = ('name', 'wilaya')

@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ('name', 'university')

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'faculty')