import io
import os
import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from django.core.files.base import ContentFile
from django.conf import settings
from datetime import datetime

# ── SHARED SECURITY HELPER ──────────────────────────────────────────────────
def _generate_qr_seal(content, identifier):
    qr = qrcode.make(content)
    temp_path = os.path.join(settings.BASE_DIR, f'media/qr_{identifier}.png')
    qr.save(temp_path)
    return temp_path

# ── DOCUMENT 1: INTERNSHIP AGREEMENT (PORTRAIT) ──────────────────────────────
def generate_agreement_pdf(application, admin):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    student, company, offer = application.student, application.offer.company, application.offer
    internship = application.internship 
    gen_date = datetime.now().strftime("%d/%m/%Y")

    # Header
    p.setFont("Helvetica-Bold", 11)
    p.drawCentredString(width/2, height - 30, "PEOPLE'S DEMOCRATIC REPUBLIC OF ALGERIA")
    p.drawCentredString(width/2, height - 45, "Ministry of Higher Education and Scientific Research")
    
    logo_path = os.path.join(settings.BASE_DIR, 'static/images/logo_univ.png')
    if os.path.exists(logo_path):
        p.drawImage(logo_path, 45, height - 105, width=2.2*cm, preserveAspectRatio=True, mask='auto')

    p.setFont("Helvetica-Bold", 18)
    p.drawCentredString(width/2 + 20, height - 85, "INTERNSHIP AGREEMENT")
    p.setFont("Helvetica-Bold", 14)
    p.drawCentredString(width/2 + 20, height - 105, "CONVENTION DE STAGE")

    p.setLineWidth(1)
    p.rect(40, height - 230, 235, 110)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, height - 135, f"UNIVERSITY: {admin.university.name.upper() if admin.university else 'CONSTANTINE 2'}")
    p.setFont("Helvetica", 9)
    p.drawString(50, height - 185, f"Head of {admin.department.name if admin.department else 'University'} Dept")

    p.rect(width - 275, height - 230, 235, 110)
    p.drawString(width - 265, height - 135, f"COMPANY: {company.companyName}")

    p.rect(40, height - 580, 515, 320)
    p.setFont("Helvetica-Bold", 14)
    p.drawCentredString(width/2, height - 290, "STUDENT INFORMATION DATA")
    
    p.setFont("Helvetica", 11)
    y = height - 330
    p.drawString(55, y, f"Full Name : {student.lastName.upper()} {student.firstName}")
    p.drawString(55, y-26, f"Department : {student.department.name if student.department else 'General'}")
    p.drawString(55, y-52, f"Student ID Card No : {student.IDCardNumber}")
    p.drawString(55, y-78, f"Social Security Number : {student.socialSecurityNumber or '................'}")
    p.drawString(55, y-104, f"Degree Pursued : Bachelor in Information Technology (L3 TI)")
    p.drawString(55, y-130, f"Internship Topic : {internship.topic}")
    p.drawString(55, y-156, f"Internship Period : From {internship.startDate} To {internship.endDate}")
    
    qr_path = _generate_qr_seal(f"STAG.IO-AGREEMENT-{application.id}", application.id)
    p.drawImage(qr_path, width - 180, 50, width=4*cm, height=4*cm)
    p.drawString(50, 150, "Institutional Signature")

    p.showPage() # Second page for Articles
    p.setFont("Helvetica-Bold", 16)
    p.drawCentredString(width/2, height - 50, "LEGAL TERMS AND CONDITIONS")
    p.save()
    if os.path.exists(qr_path): os.remove(qr_path)
    buffer.seek(0)
    return ContentFile(buffer.read(), name=f"agreement_{application.id}.pdf")

# ── DOCUMENT 2: INTERNSHIP CERTIFICATE (LANDSCAPE) ──────────────────────────
def generate_certificate_pdf(internship, admin):
    """
    LOGIC: The Professional Credential.
    Uses Hiba's landscape design mapped to the hardened relational backend.
    """
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)
    student = internship.application.student
    company = internship.application.offer.company

    # Hierarchy Data Mapping
    univ_name = admin.university.name.upper() if admin.university else "CONSTANTINE 2"
    fac_name = admin.faculty.name if admin.faculty else "NTIC"
    dept_name = admin.department.name if admin.department else "IFA"
    supervisor = f"{admin.firstName} {admin.lastName}"

    # --- HIBA'S DESIGN: BORDERS ---
    p.setLineWidth(2)
    p.rect(0.5*cm, 0.5*cm, width-1*cm, height-1*cm) # Outer
    p.setLineWidth(0.5)
    p.rect(0.7*cm, 0.7*cm, width-1.4*cm, height-1.4*cm) # Inner

    # --- HEADER ---
    p.setFont("Helvetica-Bold", 12)
    p.drawCentredString(width/2, height - 1.5*cm, "PEOPLE'S DEMOCRATIC REPUBLIC OF ALGERIA")
    p.setFont("Helvetica", 11)
    p.drawCentredString(width/2, height - 2.2*cm, "Ministry of Higher Education and Scientific Research")
    p.setFont("Helvetica-Bold", 12)
    p.drawCentredString(width/2, height - 2.9*cm, f"UNIVERSITY OF {univ_name}")

    # --- TITLE ---
    p.setFont("Helvetica-Bold", 45)
    p.drawCentredString(width/2, height - 6*cm, "INTERNSHIP CERTIFICATE")
    p.line(width/2 - 7*cm, height - 6.3*cm, width/2 + 7*cm, height - 6.3*cm)

    # --- CONTENT ---
    p.setFont("Helvetica", 14)
    y = height - 9*cm
    margin = 2.5*cm
    line_h = 1.1*cm

    p.drawString(margin, y, "This is to certify that the student:")
    p.setFont("Helvetica-Bold", 15)
    p.drawString(margin + 7.5*cm, y, f"{student.lastName.upper()} {student.firstName}")
    
    p.setFont("Helvetica", 14)
    p.drawString(margin, y - line_h, f"Student ID No:")
    p.setFont("Helvetica-Bold", 13)
    p.drawString(margin + 3.5*cm, y - line_h, str(student.IDCardNumber or 'N/A'))
    
    p.setFont("Helvetica", 14)
    p.drawString(margin, y - line_h*2, f"Faculty of:")
    p.drawString(margin + 2.8*cm, y - line_h*2, fac_name)
    p.drawString(margin + 10*cm, y - line_h*2, f"Department:")
    p.drawString(margin + 13.2*cm, y - line_h*2, dept_name)

    p.drawString(margin, y - line_h*3, "Has successfully completed a practical internship in the field of:")
    p.setFont("Helvetica-BoldOblique", 14)
    p.drawCentredString(width/2, y - line_h*4, f"\"{internship.topic}\"")

    p.setFont("Helvetica", 14)
    p.drawString(margin, y - line_h*5, f"At (Host Organization):")
    p.setFont("Helvetica-Bold", 14)
    p.drawString(margin + 5.5*cm, y - line_h*5, company.companyName)

    p.setFont("Helvetica", 14)
    p.drawString(margin, y - line_h*6, f"During the period from:")
    p.setFont("Helvetica-Bold", 13)
    p.drawString(margin + 5.5*cm, y - line_h*6, f"{internship.startDate}  to  {internship.endDate}")

    # Duration Calculation
    try:
        duration = (internship.endDate - internship.startDate).days
    except:
        duration = "..."
    p.setFont("Helvetica", 14)
    p.drawString(margin, y - line_h*7, f"Total Duration: {duration} Days")

    # --- SIGNATURES ---
    p.setFont("Helvetica", 12)
    p.drawRightString(width - margin, height - 17.5*cm, f"Issued on: {datetime.now().strftime('%d/%m/%Y')}")

    p.setFont("Helvetica-Bold", 11)
    p.drawString(margin + 1*cm, height - 18.8*cm, "Academic Supervisor")
    p.drawCentredString(width/2, height - 18.8*cm, "The Department Head")
    p.drawRightString(width - margin - 1*cm, height - 18.8*cm, "Company Manager")
    
    p.setFont("Helvetica", 10)
    p.drawString(margin + 1*cm, height - 19.3*cm, supervisor)

    p.setFont("Helvetica-Oblique", 8)
    p.drawCentredString(width/2, 1*cm, "This certificate is digitally generated by Stag.io Platform")

    p.showPage()
    p.save()
    buffer.seek(0)
    return ContentFile(buffer.read(), name=f"certificate_{internship.id}.pdf")