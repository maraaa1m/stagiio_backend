from django.db import models
from accounts.models import User, Student, Admin
from offers.models import InternshipOffer

class Application(models.Model):
    PENDING = 'PENDING'
    ACCEPTED = 'ACCEPTED'
    REFUSED = 'REFUSED'
    VALIDATED = 'VALIDATED'

    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (ACCEPTED, 'Accepted'),
        (REFUSED, 'Refused'),
        (VALIDATED, 'Validated'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='applications')
    offer = models.ForeignKey(InternshipOffer, on_delete=models.CASCADE, related_name='applications')
    applicationDate = models.DateField(auto_now_add=True)
    applicationStatus = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    matchingScore = models.FloatField(default=0.0)
    
    # NEW: Persists feedback from the recruiter for the student's dashboard
    refusalReason = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.student} -> {self.offer}"

class Internship(models.Model):
    ONGOING = 'ONGOING' 
    PENDING_CERT = 'PENDING_CERT' 
    COMPLETED = 'COMPLETED' 
    
    STATUS_CHOICES = [
        (ONGOING, 'Ongoing'),
        (PENDING_CERT, 'Pending Certification'),
        (COMPLETED, 'Completed'),
    ]

    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name='internship')
    startDate = models.DateField()
    endDate = models.DateField()
    topic = models.CharField(max_length=200)
    supervisorName = models.CharField(max_length=200)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=ONGOING)

    def __str__(self):
        return f"Internship: {self.application.student} ({self.status})"

class Agreement(models.Model):
    internship = models.OneToOneField(Internship, on_delete=models.CASCADE, related_name='agreement')
    admin = models.ForeignKey(Admin, on_delete=models.SET_NULL, null=True, related_name='agreements')
    generationDate = models.DateField(auto_now_add=True)
    pdfUrl = models.FileField(upload_to='agreements/', blank=True, null=True)
    status = models.CharField(max_length=10, default='VALIDATED')

    def __str__(self):
        return f"Agreement for {self.internship.application.student}"

class Certificate(models.Model):
    internship = models.OneToOneField(Internship, on_delete=models.CASCADE, related_name='certificate')
    admin = models.ForeignKey(Admin, on_delete=models.SET_NULL, null=True, related_name='certificates')
    issueDate = models.DateField(auto_now_add=True)
    pdfUrl = models.FileField(upload_to='certificates/', blank=True, null=True)

    def __str__(self):
        return f"Certificate for {self.internship.application.student}"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)