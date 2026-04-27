from rest_framework import serializers
from .models import InternshipOffer, Skill

class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ['id', 'skillName']

class InternshipOfferSerializer(serializers.ModelSerializer):
    """
    LOGIC: The Hybrid Operational Serializer.
    Orchestrates the conversion of flat UI forms into complex relational models.
    """
    requiredSkills = SkillSerializer(many=True, read_only=True)
    remainingSpots = serializers.IntegerField(read_only=True)
    
    # Logic: Accepts IDs for writing, provides objects for reading.
    skillIds = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)

    class Meta:
        model = InternshipOffer
        fields = [
            'id', 'title', 'description', 'willaya', 'type',
            'maxParticipants', 'remainingSpots', 'is_active',
            'applicationDeadline', 'internshipStartDate', 'internshipEndDate',
            'requiredSkills', 'skillIds',
        ]

    def validate(self, data):
        """
        BUSINESS RULE: Chronological Integrity.
        Ensures the recruitment phase ends before the work phase begins.
        """
        if data.get('applicationDeadline') and data.get('internshipStartDate'):
            if data['applicationDeadline'] >= data['internshipStartDate']:
                raise serializers.ValidationError("Deadline must be before the internship start date.")
        return data

    def create(self, validated_data):
        skill_ids = validated_data.pop('skillIds', [])
        offer = InternshipOffer.objects.create(**validated_data)
        for s_id in skill_ids:
            try:
                skill = Skill.objects.get(id=s_id)
                offer.requiredSkills.add(skill)
            except Skill.DoesNotExist: pass
        return offer

    def update(self, instance, validated_data):
        skill_ids = validated_data.pop('skillIds', [])
        for attr, value in validated_data.items(): setattr(instance, attr, value)
        instance.save()
        if skill_ids is not None:
            instance.requiredSkills.set(skill_ids) # Atomic Sync
        return instance