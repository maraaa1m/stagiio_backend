import io
import os
import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from django.core.files.base import ContentFile
from django.conf import settings
from datetime import datetime

def _generate_qr_seal(content, identifier):
    qr = qrcode.make(content)
    # Using a unique temp name to avoid race conditions (Fixing Audit med bug)
    temp_filename = f'qr_{identifier}_{datetime.now().timestamp()}.png'
    temp_path = os.path.join(settings.BASE_DIR, 'media', temp_filename)
    qr.save(temp_path)
    return temp_path

def generate_agreement_pdf(application, admin):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    student = application.student
    company = application.offer.company
    internship = application.internship 
    gen_date = datetime.now().strftime("%d/%m/%Y")

    # --- PAGE 1: THE OFFICIAL FORM ---
    
    # 1. Republic Header
    p.setFont("Helvetica-Bold", 12)
    p.drawCentredString(width/2, height - 1.5*cm, "PEOPLE'S DEMOCRATIC REPUBLIC OF ALGERIA")
    p.setFont("Helvetica", 11)
    p.drawCentredString(width/2, height - 2.1*cm, "Ministry of Higher Education and Scientific Research")
    
    # 2. Institutional Header
    p.setFont("Helvetica-Bold", 14)
    p.drawCentredString(width/2, height - 3.2*cm, "UNIVERSITY OF ABDELHAMID MEHRI – CONSTANTINE 2")
    
    # 3. Main Title
    p.setFont("Helvetica-Bold", 22)
    p.drawCentredString(width/2, height - 4.5*cm, "INTERNSHIP AGREEMENT")
    p.setFont("Helvetica-Bold", 18)
    p.drawCentredString(width/2, height - 5.3*cm, "BETWEEN")

    # 4. The Two Side-by-Side Boxes
    p.setLineWidth(1)
    # University Box (Left)
    p.rect(1.5*cm, height - 9*cm, 8.5*cm, 3*cm)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(1.7*cm, height - 6.5*cm, "UNIVERSITY OF CONSTANTINE 2")
    p.setFont("Helvetica", 8)
    p.drawString(1.7*cm, height - 6.9*cm, "New city Ali Mendjeli, Constantine")
    p.setFont("Helvetica-Bold", 9)
    p.drawString(1.7*cm, height - 7.5*cm, "Represented by:")
    p.setFont("Helvetica", 9)
    p.drawString(1.7*cm, height - 7.9*cm, "The Vice Rector for External Relations")
    p.drawString(1.7*cm, height - 8.6*cm, "Tel/Fax: +213 031 82 45 79")

    # ET (Center)
    p.setFont("Helvetica-Bold", 14)
    p.drawCentredString(width/2, height - 7.5*cm, "AND")

    # Company Box (Right)
    p.rect(width - 10*cm, height - 9*cm, 8.5*cm, 3*cm)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(width - 9.8*cm, height - 6.5*cm, "THE HOST ENTERPRISE")
    p.setFont("Helvetica", 9)
    p.drawString(width - 9.8*cm, height - 7.1*cm, f"Name: {company.companyName}")
    p.setFont("Helvetica-Bold", 9)
    p.drawString(width - 9.8*cm, height - 7.7*cm, "Represented by:")
    p.setFont("Helvetica", 9)
    p.drawString(width - 9.8*cm, height - 8.1*cm, "The Authorized Manager")
    p.drawString(width - 9.8*cm, height - 8.6*cm, f"Tel: {company.phoneNumber or '................'}")

    # 5. The Main Student Data Box (Centered)
    p.rect(1.5*cm, height - 21*cm, width - 3*cm, 11.5*cm)
    p.setFont("Helvetica-Bold", 15)
    p.drawCentredString(width/2, height - 10.3*cm, "STUDENT INFORMATION DATA")
    p.line(width/2 - 4*cm, height - 10.5*cm, width/2 + 4*cm, height - 10.5*cm)

    p.setFont("Helvetica", 11)
    y_start = height - 11.5*cm
    line_h = 0.9*cm
    
    fields = [
        ("Full Name", f"{student.lastName.upper()} {student.firstName}"),
        ("Faculty", admin.faculty.name if admin.faculty else "New Technologies (NTIC)"),
        ("Department", student.department.name if student.department else "IFA"),
        ("Student ID Card No", student.IDCardNumber),
        ("Social Security No", student.socialSecurityNumber or "................"),
        ("Phone Number", student.phoneNumber),
        ("Degree Pursued", "Bachelor in Information Technology (L3 TI)"),
        ("Internship Topic", internship.topic),
        ("Academic Supervisor", f"Dr. {admin.lastName}"),
        ("Starting Date", str(internship.startDate)),
        ("Ending Date", str(internship.endDate))
    ]

    for i, (label, val) in enumerate(fields):
        p.drawString(2*cm, y_start - (i * line_h), f"{label} :")
        p.setFont("Helvetica-Bold", 11)
        p.drawString(6.5*cm, y_start - (i * line_h), str(val))
        p.setFont("Helvetica", 11)

    # 6. Bottom Visa & Signatures
    p.setFont("Helvetica-Bold", 10)
    p.drawString(2*cm, height - 23*cm, "Visa of Department Head:")
    p.drawString(2*cm, height - 26*cm, "For the Company")
    p.drawRightString(width - 2*cm, height - 26*cm, "For the University")

    # 7. Security QR Code (Digital Trust Seal)
    qr_path = _generate_qr_seal(f"STAGIO-VALID-{application.id}", application.id)
    p.drawImage(qr_path, width/2 - 1.5*cm, 2*cm, width=3*cm, height=3*cm)
    p.setFont("Helvetica-Oblique", 8)
    p.drawCentredString(width/2, 1.5*cm, "Digitally Verified by Stag.io Infrastructure")

    # --- PAGE 2: LEGAL ARTICLES (THE DETAILS) ---
    p.showPage()
    p.setFont("Helvetica-Bold", 16)
    p.drawCentredString(width/2, height - 2*cm, "TERMS AND CONDITIONS")
    p.line(2*cm, height - 2.2*cm, width - 2*cm, height - 2.2*cm)

    articles = [
        ("Article 1: Purpose", "This agreement defines the legal conditions for hosting students within the host organization for practical training."),
        ("Article 2: Goal", "The internship aims to ensure practical application of the knowledge taught at University Constantine 2."),
        ("Article 3: Status", "The student retains their university status and remains under academic responsibility."),
        ("Article 4: Discipline", "The student must comply with the internal rules, safety regulations, and working hours of the host company."),
        ("Article 5: Social Protection", f"The student remains covered by social security insurance under ID: {student.socialSecurityNumber}."),
        ("Article 6: Liability", "In case of a work-related accident, the company must notify the university administration immediately."),
        ("Article 7: Confidentiality", "The student is bound by professional secrecy regarding company data. The final report is mandatory for validation.")
    ]

    y_art = height - 4*cm
    for title, text in articles:
        p.setFont("Helvetica-Bold", 12)
        p.drawString(2*cm, y_art, title)
        p.setFont("Helvetica", 10)
        p.drawString(2*cm, y_art - 0.6*cm, text)
        y_art -= 2*cm

    p.save()
    if os.path.exists(qr_path): os.remove(qr_path)
    buffer.seek(0)
    return ContentFile(buffer.read(), name=f"agreement_{application.id}.pdf")

# (Keep your generate_certificate_pdf function here as it was)


def generate_certificate_pdf(internship, admin):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)
    student = internship.application.student
    company = internship.application.offer.company

    univ_name = admin.university.name.upper() if admin.university else "CONSTANTINE 2"
    fac_name = admin.faculty.name if admin.faculty else "NTIC"
    dept_name = admin.department.name if admin.department else "IFA"
    supervisor = f"{admin.firstName} {admin.lastName}"

    p.setLineWidth(2)
    p.rect(0.5*cm, 0.5*cm, width-1*cm, height-1*cm)
    p.setLineWidth(0.5)
    p.rect(0.7*cm, 0.7*cm, width-1.4*cm, height-1.4*cm)

    p.setFont("Helvetica-Bold", 12)
    p.drawCentredString(width/2, height - 1.5*cm, "PEOPLE'S DEMOCRATIC REPUBLIC OF ALGERIA")
    p.setFont("Helvetica", 11)
    p.drawCentredString(width/2, height - 2.2*cm, "Ministry of Higher Education and Scientific Research")
    p.setFont("Helvetica-Bold", 12)
    p.drawCentredString(width/2, height - 2.9*cm, f"UNIVERSITY OF {univ_name}")

    p.setFont("Helvetica-Bold", 45)
    p.drawCentredString(width/2, height - 6*cm, "INTERNSHIP CERTIFICATE")
    p.line(width/2 - 7*cm, height - 6.3*cm, width/2 + 7*cm, height - 6.3*cm)

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

    try:
        duration = (internship.endDate - internship.startDate).days
    except:
        duration = "..."
    p.setFont("Helvetica", 14)
    p.drawString(margin, y - line_h*7, f"Total Duration: {duration} Days")

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