from django.db import models
from datetime import date

class Skill(models.Model):
    """
    LOGIC: The Technical Dictionary.
    Acts as a single source of truth for skill names, preventing 'keyword 
    mismatch' (e.g., 'React' vs 'ReactJS') in the matching engine.
    """
    skillName = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.skillName

class InternshipOffer(models.Model):
    """
    LOGIC: The Resource Management Engine.
    This model decouples the advertisement lifecycle from the professional period.
    """
    ONLINE = 'ONLINE'
    IN_PERSON = 'IN_PERSON'
    TYPE_CHOICES = [(ONLINE, 'Online'), (IN_PERSON, 'In Person')]

    company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE, related_name='offers')
    title = models.CharField(max_length=200)
    description = models.TextField()
    willaya = models.CharField(max_length=100) 
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    
    # --- CAPACITY MANAGEMENT ---
    # maxParticipants: Limits the institutional placement capacity.
    # is_active: Manual kill-switch for corporate control.
    maxParticipants = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    
    # --- TEMPORAL ARCHITECTURE ---
    # applicationDeadline: The end of the recruitment window.
    applicationDeadline = models.DateField() 
    # internshipDates: The actual professional working period.
    internshipStartDate = models.DateField()
    internshipEndDate = models.DateField()
    
    requiredSkills = models.ManyToManyField(Skill, related_name='offers')

    class Meta:
        ordering = ['-id']

    @property
    def is_recruitment_open(self):
        """LOGIC: Automated lifecycle check for availability."""
        return date.today() <= self.applicationDeadline and self.remainingSpots > 0 and self.is_active

    @property
    def remainingSpots(self):
        """
        LOGIC: The Saturation Guard.
        A spot is only consumed when the University Admin VALIDATES the agreement,
        ensuring perfect data integrity between marketplace and legal validation.
        """
        from applications.models import Application
        validated_count = Application.objects.filter(offer=self, applicationStatus='VALIDATED').count()
        return max(0, self.maxParticipants - validated_count)

    def __str__(self): return f"{self.title} @ {self.company.companyName}"