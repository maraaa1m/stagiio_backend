def calculate_matching_score(student, offer):
    

    if offer.type == 'IN_PERSON':
        if student.univWillaya != offer.willaya:
            return 0 

    required_skills = offer.requiredSkills.all()
    
    if len(required_skills) == 0:
        return 100 
    
    student_skills = student.skills.all()
    
    common = set(required_skills) & set(student_skills)
    score = (len(common) / len(required_skills)) * 100
    
    return round(score, 2)