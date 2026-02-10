"""
PDF Generation for Medical Prescriptions with Blockchain Verification
"""
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.pdfgen import canvas
from django.core.files.base import ContentFile
from django.conf import settings
import hashlib
import qrcode
import io
from datetime import datetime
import os


def generate_qr_code(url, prescription_id):
    """Generate QR code for prescription verification"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save to BytesIO
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    # Return as ContentFile
    return ContentFile(buffer.read(), name=f'prescription_qr_{prescription_id}.png')


def generate_prescription_pdf(prescription, include_qr=False):
    """Generate prescription PDF with doctor info, medicines, and blockchain verification"""
    
    buffer = io.BytesIO()
    
    # Create PDF
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )
    
    # Container for PDF elements
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1e40af'),
        spaceAfter=12,
        alignment=1  # Center
    )
    
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#1e40af'),
        spaceAfter=6
    )
    
    normal_style = styles['Normal']
    
    # Header - RuralCare Logo/Title
    title = Paragraph("RuralCare", title_style)
    subtitle = Paragraph("Medical Prescription", styles['Heading3'])
    elements.append(title)
    elements.append(subtitle)
    elements.append(Spacer(1, 0.2*inch))
    
    # Doctor Information
    doctor = prescription.doctor
    doctor_profile = getattr(doctor, 'doctor_profile', None)
    
    # Get doctor's readable specialization
    specialization = 'General Medicine'
    if doctor_profile and doctor_profile.specialization:
        # Convert specialization code to display name
        spec_dict = dict(doctor_profile.SPECIALIZATION_CHOICES) if hasattr(doctor_profile, 'SPECIALIZATION_CHOICES') else {}
        specialization = spec_dict.get(doctor_profile.specialization, doctor_profile.specialization.replace('_', ' ').title())
    
    # Get license number or generate professional format
    license_no = 'Not Available'
    if doctor_profile and doctor_profile.license_number:
        license_no = doctor_profile.license_number
    
    # Get hospital affiliation
    hospital = 'Private Practice'
    if doctor_profile and doctor_profile.hospital_affiliation:
        hospital = doctor_profile.hospital_affiliation
    
    # Get contact with phone if available
    contact = doctor.email
    if doctor_profile and doctor_profile.hospital_phone:
        contact = f"{doctor.email} | {doctor_profile.hospital_phone}"
    
    doctor_info_data = [
        ['Doctor Information', ''],
        ['Name:', f"Dr. {doctor.first_name} {doctor.last_name}"],
        ['Specialization:', specialization],
        ['License No:', license_no],
        ['Hospital:', hospital],
        ['Contact:', contact],
    ]
    
    doctor_table = Table(doctor_info_data, colWidths=[2.2*inch, 4.3*inch])
    doctor_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dbeafe')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(doctor_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Patient Information
    patient = prescription.patient
    patient_info_data = [
        ['Patient Information', ''],
        ['Name:', f"{patient.first_name} {patient.last_name}"],
        ['Email:', patient.email],
        ['Date:', prescription.created_at.strftime('%B %d, %Y')],
    ]
    
    patient_table = Table(patient_info_data, colWidths=[2.2*inch, 4.3*inch])
    patient_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dbeafe')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(patient_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Diagnosis
    if prescription.diagnosis:
        elements.append(Paragraph("<b>Diagnosis:</b>", header_style))
        elements.append(Paragraph(prescription.diagnosis, normal_style))
        elements.append(Spacer(1, 0.15*inch))
    
    # Medicines
    elements.append(Paragraph("<b>Prescription (Rx):</b>", header_style))
    elements.append(Spacer(1, 0.1*inch))
    
    medicine_data = [['#', 'Medicine', 'Dosage', 'Frequency', 'Timing', 'Duration']]
    
    # Create a smaller font style for table cells
    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontSize=8,
        leading=10
    )
    
    for idx, medicine in enumerate(prescription.medicines.all(), 1):
        medicine_data.append([
            str(idx),
            Paragraph(medicine.medicine_name, table_cell_style),
            Paragraph(medicine.dosage, table_cell_style),
            Paragraph(medicine.get_frequency_display(), table_cell_style),
            Paragraph(medicine.get_timing_display(), table_cell_style),
            Paragraph(f"{medicine.duration_days} days", table_cell_style)
        ])
        
        # Add special instructions if any
        if medicine.instructions:
            medicine_data.append([
                '',
                Paragraph(f"<i>Note: {medicine.instructions}</i>", table_cell_style),
                '', '', '', ''
            ])
    
    # Adjusted column widths for better alignment (total width ~6.5 inches)
    medicine_table = Table(medicine_data, colWidths=[0.3*inch, 1.8*inch, 0.9*inch, 1.4*inch, 1.2*inch, 0.9*inch])
    medicine_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ('ALIGN', (2, 1), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
    ]))
    elements.append(medicine_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Additional Notes
    if prescription.doctor_notes:
        elements.append(Paragraph("<b>Additional Notes:</b>", header_style))
        elements.append(Paragraph(prescription.doctor_notes, normal_style))
        elements.append(Spacer(1, 0.15*inch))
    
    # Follow-up Instructions
    if prescription.follow_up_instructions:
        elements.append(Paragraph("<b>Follow-up Instructions:</b>", header_style))
        elements.append(Paragraph(prescription.follow_up_instructions, normal_style))
        elements.append(Spacer(1, 0.15*inch))
    
    # Signature
    elements.append(Spacer(1, 0.3*inch))
    sig_data = [
        ['', f"Dr. {doctor.first_name} {doctor.last_name}"],
        ['', '(Digital Signature)'],
        ['', f"Date: {prescription.created_at.strftime('%B %d, %Y')}"]
    ]
    sig_table = Table(sig_data, colWidths=[4*inch, 2.5*inch])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
        ('LINEABOVE', (1, 0), (1, 0), 1, colors.black),
    ]))
    elements.append(sig_table)
    
    # QR Code for verification (if included)
    if include_qr and prescription.qr_code:
        elements.append(Spacer(1, 0.3*inch))
        
        # Blockchain verification header
        blockchain_header = Paragraph("<b>Blockchain Verification</b>", header_style)
        elements.append(blockchain_header)
        elements.append(Spacer(1, 0.1*inch))
        
        # Verification info table
        verification_data = [
            ['Prescription ID:', str(prescription.id)],
        ]
        
        if prescription.pdf_hash:
            verification_data.append(['PDF Hash (SHA-256):', prescription.pdf_hash[:32] + '...'])
        
        if prescription.blockchain_tx_hash:
            verification_data.append(['Blockchain TX:', prescription.blockchain_tx_hash])
            verification_data.append(['Network:', 'Sepolia Testnet'])
            verification_data.append(['Status:', 'Verified ✓' if prescription.is_verified else 'Pending'])
        
        verification_table = Table(verification_data, colWidths=[2*inch, 4*inch])
        verification_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(verification_table)
        elements.append(Spacer(1, 0.15*inch))
        
        # Add QR code image centered
        qr_path = prescription.qr_code.path if hasattr(prescription.qr_code, 'path') else None
        if qr_path and os.path.exists(qr_path):
            qr_img = Image(qr_path, width=1.5*inch, height=1.5*inch)
            # Center the QR code
            qr_table = Table([[qr_img]], colWidths=[6*inch])
            qr_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ]))
            elements.append(qr_table)
            elements.append(Spacer(1, 0.1*inch))
            
            # QR code label
            qr_label = Paragraph(
                "<i>Scan QR code to verify prescription authenticity on blockchain</i>",
                ParagraphStyle(
                    'QRLabel',
                    parent=normal_style,
                    fontSize=8,
                    textColor=colors.HexColor('#6b7280'),
                    alignment=1  # Center
                )
            )
            elements.append(qr_label)
    
    # Build PDF
    doc.build(elements)
    
    # Get PDF content
    pdf_content = buffer.getvalue()
    buffer.close()
    
    # Generate hash
    pdf_hash = hashlib.sha256(pdf_content).hexdigest()
    
    # Save PDF file
    pdf_file = ContentFile(pdf_content, name=f'prescription_{prescription.id}.pdf')
    
    return pdf_file, pdf_hash
