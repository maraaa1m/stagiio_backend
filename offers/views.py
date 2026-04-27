from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from datetime import date, timedelta

from .models import InternshipOffer, Skill
from .serializers import InternshipOfferSerializer, SkillSerializer
from accounts.models import Company, Student, Admin
from utils.matching import calculate_matching_score

# ── CORPORATE OPERATIONS ──

@api_view(['POST'])
def create_offer(request):
    try:
        company = Company.objects.get(user=request.user)
        # Governance Logic: Only Superadmin-approved companies can generate supply
        if not company.isApproved:
            return Response({'error': 'Institutional audit pending.'}, status=403)
        
        serializer = InternshipOfferSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(company=company)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Company.DoesNotExist:
        return Response(status=403)

@api_view(['GET'])
def get_offers(request):
    """Logic: Companies see their own. Admins see everything."""
    try:
        company = Company.objects.get(user=request.user)
        offers  = InternshipOffer.objects.filter(company=company)
    except Company.DoesNotExist:
        offers = InternshipOffer.objects.all()
    serializer = InternshipOfferSerializer(offers, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_offer_detail(request, offer_id):
    offer = get_object_or_404(InternshipOffer, id=offer_id)
    serializer = InternshipOfferSerializer(offer)
    return Response(serializer.data)

@api_view(['PUT'])
def update_offer(request, offer_id):
    try:
        company = Company.objects.get(user=request.user)
        offer = InternshipOffer.objects.get(id=offer_id, company=company)
        serializer = InternshipOfferSerializer(offer, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)
    except:
        return Response(status=404)

@api_view(['DELETE'])
def delete_offer(request, offer_id):
    try:
        company = Company.objects.get(user=request.user)
        offer = InternshipOffer.objects.get(id=offer_id, company=company)
        offer.delete()
        return Response({'message': 'Removed'}, status=200)
    except:
        return Response(status=404)

# ── STUDENT INTELLIGENCE ──

@api_view(['GET'])
def get_recommended_offers(request):
    """Logic: Neural Matcher. Automatically filters for capacity and deadlines."""
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return Response(status=403)

    # Logic: Only show offers where is_recruitment_open property is True
    offers = [o for o in InternshipOffer.objects.all() if o.is_recruitment_open]
    
    scored_offers = []
    for offer in offers:
        score = calculate_matching_score(student, offer)
        scored_offers.append({
            'id': offer.id,
            'title': offer.title,
            'company': offer.company.companyName,
            'willaya': offer.willaya,
            'matchingScore': score,
            'remaining': offer.remainingSpots,
            'deadline': str(offer.applicationDeadline),
            'requiredSkills': [s.skillName for s in offer.requiredSkills.all()],
        })

    scored_offers.sort(key=lambda x: x['matchingScore'], reverse=True)
    return Response(scored_offers)

# FIXED: Re-added the missing function that caused the crash
@api_view(['GET'])
def get_match_score(request, offer_id):
    """Logic: Institutional Compatibility Index."""
    try:
        student = Student.objects.get(user=request.user)
        offer = get_object_or_404(InternshipOffer, id=offer_id)
        score = calculate_matching_score(student, offer)
        return Response({'matchingScore': score})
    except:
        return Response(status=404)

@api_view(['GET'])
def get_match_report(request, offer_id):
    """Logic: Skill-Gap analytics for career guidance."""
    try:
        student = Student.objects.get(user=request.user)
        offer = get_object_or_404(InternshipOffer, id=offer_id)
        
        required = set(offer.requiredSkills.all())
        owned = set(student.skills.all())
        common = required & owned
        missing = required - owned
        score = round((len(common) / len(required)) * 100, 2) if required else 100

        return Response({
            'matchingScore': score,
            'matchedSkills': [s.skillName for s in common],
            'missingSkills': [s.skillName for s in missing],
        })
    except:
        return Response(status=404)

# ── UTILITIES ──

@api_view(['GET'])
def get_expiring_soon(request):
    today = date.today()
    in_3days = today + timedelta(days=3)
    offers = InternshipOffer.objects.filter(applicationDeadline__gte=today, applicationDeadline__lte=in_3days, is_active=True)
    data = [{
        'id': o.id,
        'title': o.title,
        'company': o.company.companyName,
        'daysLeft': (o.applicationDeadline - today).days,
    } for o in offers]
    return Response(data)

@api_view(['GET'])
def get_skills(request):
    skills = Skill.objects.all().order_by('skillName')
    serializer = SkillSerializer(skills, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def suggest_skills(request):
    try:
        student = Student.objects.get(user=request.user)
        local_offers = InternshipOffer.objects.filter(willaya=student.univWillaya)
        skill_count = {}
        for offer in local_offers:
            for skill in offer.requiredSkills.all():
                skill_count[skill.skillName] = skill_count.get(skill.skillName, 0) + 1
        owned_names = {s.skillName for s in student.skills.all()}
        suggestions = sorted([{'skill': k, 'demand': v} for k, v in skill_count.items() if k not in owned_names], key=lambda x: x['demand'], reverse=True)
        return Response({'suggestions': suggestions[:5]})
    except:
        return Response(status=403)