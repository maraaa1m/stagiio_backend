from rest_framework import serializers
from .models import Application, Internship, Agreement, Certificate, Notification

class CertificateSerializer(serializers.ModelSerializer):
    """
    LOGIC: The Professional Credential Mapping.
    Ensures the student receives an absolute link to their PDF diploma.
    """
    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = Certificate
        fields = ['id', 'issueDate', 'pdf_url']

    def get_pdf_url(self, obj):
        request = self.context.get('request')
        if obj.pdfUrl and request:
            return request.build_absolute_uri(obj.pdfUrl.url)
        return None

class AgreementSerializer(serializers.ModelSerializer):
    """LOGIC: The Legal Contract Mapping."""
    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = Agreement
        fields = ['id', 'generationDate', 'status', 'pdf_url']

    def get_pdf_url(self, obj):
        request = self.context.get('request')
        if obj.pdfUrl and request:
            return request.build_absolute_uri(obj.pdfUrl.url)
        return None

class InternshipSerializer(serializers.ModelSerializer):
    """
    LOGIC: The Operational Lifecycle Mapping.
    Nests the Agreement and Certificate so the student sees their full journey.
    """
    agreement = AgreementSerializer(read_only=True)
    certificate = CertificateSerializer(read_only=True)
    
    class Meta:
        model = Internship
        fields = [
            'id', 'startDate', 'endDate', 'topic', 
            'supervisorName', 'status', 'agreement', 'certificate'
        ]

class ApplicationSerializer(serializers.ModelSerializer):
    """
    LOGIC: The Recruitment Dashboard Mapping.
    MASTER FIX: Includes offer_id, offer_title, and company_name.
    SYNC: Naming updated to refusalReason to match the PostgreSQL model.
    """
    internship = InternshipSerializer(read_only=True)
    
    # RELATIONAL LOOKUPS: Providing flat keys for Frontend logic
    offer_id = serializers.ReadOnlyField(source='offer.id')
    offer_title = serializers.ReadOnlyField(source='offer.title')
    company_name = serializers.ReadOnlyField(source='offer.company.companyName')
    
    # FORMATTING: Standardizing the date for the UI list
    applied_date = serializers.DateField(source='applicationDate', read_only=True)

    class Meta:
        model = Application
        fields = [
            'id', 
            'offer_id', 
            'offer_title', 
            'company_name', 
            'applied_date', 
            'applicationStatus', 
            'matchingScore', 
            'refusalReason', # FIXED: Matches model class field
            'internship'
        ]
    
        # DATA INTEGRITY: These fields are governed by server logic, not user input
        read_only_fields = [
            'applicationDate', 
            'applicationStatus', 
            'matchingScore', 
            'refusalReason'
        ]

class NotificationSerializer(serializers.ModelSerializer):
    """LOGIC: User Alert Mapping."""
    class Meta:
        model = Notification
        fields = ['id', 'message', 'created_at', 'is_read']