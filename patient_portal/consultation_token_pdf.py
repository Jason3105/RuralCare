"""
PDF Generation for In-Person Consultation Tokens with Blockchain Verification
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from django.core.files.base import ContentFile
from django.utils import timezone as dj_timezone
import hashlib
import io
from datetime import datetime


def generate_consultation_token_pdf(consultation_token):
    """
    Generate a consultation token PDF for in-person visit.
    
    Args:
        consultation_token: ConsultationToken model instance
        
    Returns:
        tuple: (pdf_file: ContentFile, pdf_hash: str)
    """
    
    buffer = io.BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=36,
        bottomMargin=36
    )
    
    elements = []
    styles = getSampleStyleSheet()
    page_width = A4[0] - 80  # usable width after margins
    
    # ── Color Palette ──
    brand_blue = colors.HexColor('#1e3a8a')
    brand_light = colors.HexColor('#dbeafe')
    accent_green = colors.HexColor('#059669')
    accent_green_bg = colors.HexColor('#ecfdf5')
    text_dark = colors.HexColor('#111827')
    text_medium = colors.HexColor('#374151')
    text_light = colors.HexColor('#6b7280')
    border_color = colors.HexColor('#d1d5db')
    amber_bg = colors.HexColor('#fffbeb')
    amber_border = colors.HexColor('#d97706')
    
    # ── Custom Styles ──
    brand_title = ParagraphStyle('BrandTitle', parent=styles['Normal'],
        fontSize=22, textColor=brand_blue, fontName='Helvetica-Bold',
        alignment=TA_CENTER, spaceAfter=2)
    
    doc_subtitle = ParagraphStyle('DocSubtitle', parent=styles['Normal'],
        fontSize=11, textColor=text_medium, fontName='Helvetica',
        alignment=TA_CENTER, spaceAfter=0)
    
    token_num_style = ParagraphStyle('TokenNum', parent=styles['Normal'],
        fontSize=56, textColor=brand_blue, fontName='Helvetica-Bold',
        alignment=TA_CENTER, spaceAfter=0, spaceBefore=4)
    
    token_label = ParagraphStyle('TokenLabel', parent=styles['Normal'],
        fontSize=11, textColor=text_light, fontName='Helvetica',
        alignment=TA_CENTER, spaceAfter=0)
    
    cell_label = ParagraphStyle('CellLabel', parent=styles['Normal'],
        fontSize=9, textColor=text_light, fontName='Helvetica')
    
    cell_value = ParagraphStyle('CellValue', parent=styles['Normal'],
        fontSize=10, textColor=text_dark, fontName='Helvetica-Bold')
    
    cell_value_normal = ParagraphStyle('CellValueNormal', parent=styles['Normal'],
        fontSize=10, textColor=text_dark, fontName='Helvetica')
    
    small_mono = ParagraphStyle('SmallMono', parent=styles['Normal'],
        fontSize=7.5, textColor=text_medium, fontName='Courier', leading=10)
    
    footer_style = ParagraphStyle('Footer', parent=styles['Normal'],
        fontSize=8, textColor=text_light, fontName='Helvetica-Oblique',
        alignment=TA_CENTER)
    
    consultation = consultation_token.consultation
    doctor = consultation.doctor
    patient = consultation.patient
    doctor_profile = getattr(doctor, 'doctor_profile', None)
    
    # ── Convert scheduled time to local timezone (IST) ──
    scheduled_dt = dj_timezone.localtime(consultation.scheduled_datetime)
    
    # ==========================================
    # HEADER — Brand + Document Title
    # ==========================================
    elements.append(Paragraph("RuralCare", brand_title))
    elements.append(Paragraph("In-Person Consultation Token", doc_subtitle))
    elements.append(Spacer(1, 8))
    elements.append(HRFlowable(width="100%", thickness=2, color=brand_blue,
                               spaceAfter=10, spaceBefore=0))
    
    # ==========================================
    # TOKEN NUMBER — Large, prominent, centered
    # ==========================================
    token_box_data = [[
        Paragraph(f"#{consultation_token.token_number}", token_num_style)
    ], [
        Paragraph("TOKEN NUMBER", token_label)
    ]]
    token_box = Table(token_box_data, colWidths=[page_width])
    token_box.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (0, 0), 14),
        ('BOTTOMPADDING', (0, 1), (0, 1), 12),
        ('BACKGROUND', (0, 0), (-1, -1), brand_light),
        ('BOX', (0, 0), (-1, -1), 1.5, brand_blue),
        ('ROUNDEDCORNERS', [6, 6, 6, 6]),
    ]))
    elements.append(token_box)
    elements.append(Spacer(1, 14))
    
    # ==========================================
    # TWO-COLUMN: Doctor Info + Patient Info
    # ==========================================
    specialization = 'General Medicine'
    if doctor_profile and doctor_profile.specialization:
        spec_dict = dict(doctor_profile.SPECIALIZATION_CHOICES) if hasattr(doctor_profile, 'SPECIALIZATION_CHOICES') else {}
        specialization = spec_dict.get(doctor_profile.specialization,
                                       doctor_profile.specialization.replace('_', ' ').title())
    
    license_no = 'N/A'
    if doctor_profile and doctor_profile.license_number:
        license_no = doctor_profile.license_number
    
    hospital = 'Private Practice'
    if doctor_profile and doctor_profile.hospital_affiliation:
        hospital = doctor_profile.hospital_affiliation
    
    doctor_rows = [
        [Paragraph("<b>DOCTOR</b>", ParagraphStyle('', parent=cell_label, fontSize=10, textColor=brand_blue))],
        [Paragraph(f"Dr. {doctor.first_name} {doctor.last_name}", cell_value)],
        [Paragraph(specialization, cell_value_normal)],
        [Paragraph(f"License: {license_no}", cell_value_normal)],
        [Paragraph(hospital, cell_value_normal)],
    ]
    doctor_col = Table(doctor_rows, colWidths=[page_width * 0.48])
    doctor_col.setStyle(TableStyle([
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f9fafb')),
        ('BOX', (0, 0), (-1, -1), 0.5, border_color),
        ('LINEBELOW', (0, 0), (0, 0), 0.5, border_color),
        ('ROUNDEDCORNERS', [4, 4, 4, 4]),
    ]))
    
    patient_rows = [
        [Paragraph("<b>PATIENT</b>", ParagraphStyle('', parent=cell_label, fontSize=10, textColor=brand_blue))],
        [Paragraph(f"{patient.first_name} {patient.last_name}", cell_value)],
        [Paragraph(patient.email, cell_value_normal)],
    ]
    patient_col = Table(patient_rows, colWidths=[page_width * 0.48])
    patient_col.setStyle(TableStyle([
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f9fafb')),
        ('BOX', (0, 0), (-1, -1), 0.5, border_color),
        ('LINEBELOW', (0, 0), (0, 0), 0.5, border_color),
        ('ROUNDEDCORNERS', [4, 4, 4, 4]),
    ]))
    
    two_col = Table([[doctor_col, patient_col]], colWidths=[page_width * 0.50, page_width * 0.50])
    two_col.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    elements.append(two_col)
    elements.append(Spacer(1, 14))
    
    # ==========================================
    # CONSULTATION DETAILS — uses local timezone
    # ==========================================
    detail_header = [[
        Paragraph("<b>CONSULTATION DETAILS</b>",
                   ParagraphStyle('', parent=cell_label, fontSize=10, textColor=accent_green))
    ]]
    detail_fields = [[
        Paragraph("Date", cell_label),
        Paragraph("Time", cell_label),
        Paragraph("Mode", cell_label),
        Paragraph("Duration", cell_label),
    ], [
        Paragraph(scheduled_dt.strftime('%B %d, %Y'), cell_value),
        Paragraph(scheduled_dt.strftime('%I:%M %p'), cell_value),
        Paragraph("In-Person", cell_value),
        Paragraph(f"{consultation.duration_minutes} min", cell_value),
    ]]
    
    header_tbl = Table(detail_header, colWidths=[page_width])
    header_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), accent_green_bg),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('BOX', (0, 0), (-1, -1), 0.5, accent_green),
    ]))
    elements.append(header_tbl)
    
    quarter = page_width / 4
    fields_tbl = Table(detail_fields, colWidths=[quarter, quarter, quarter, quarter])
    fields_tbl.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('BOX', (0, 0), (-1, -1), 0.5, accent_green),
        ('LINEABOVE', (0, 0), (-1, 0), 0, colors.white),
        ('BACKGROUND', (0, 0), (-1, -1), accent_green_bg),
    ]))
    elements.append(fields_tbl)
    elements.append(Spacer(1, 16))
    
    # ==========================================
    # BLOCKCHAIN VERIFICATION
    # ==========================================
    elements.append(HRFlowable(width="100%", thickness=0.5, color=border_color,
                               spaceAfter=6, spaceBefore=0))
    
    bc_heading = ParagraphStyle('BCHead', parent=cell_label, fontSize=10,
                                textColor=brand_blue, fontName='Helvetica-Bold')
    elements.append(Paragraph("BLOCKCHAIN VERIFICATION", bc_heading))
    elements.append(Spacer(1, 6))
    
    verification_rows = [
        [Paragraph("Network", cell_label),
         Paragraph("Ethereum Sepolia Testnet", cell_value_normal)],
        [Paragraph("Token ID", cell_label),
         Paragraph(str(consultation_token.id), small_mono)],
    ]
    
    tx_hash = consultation_token.blockchain_tx_hash
    if tx_hash:
        verification_rows.append([
            Paragraph("Transaction Hash", cell_label),
            Paragraph(tx_hash, small_mono)
        ])
        etherscan_url = f"https://sepolia.etherscan.io/tx/{tx_hash}"
        verification_rows.append([
            Paragraph("Etherscan", cell_label),
            Paragraph(etherscan_url, small_mono)
        ])
        status_text = '<font color="#059669"><b>✓ Verified on Blockchain</b></font>' if consultation_token.is_verified else '<font color="#d97706"><b>⏳ Pending Confirmation</b></font>'
        verification_rows.append([
            Paragraph("Status", cell_label),
            Paragraph(status_text, cell_value_normal)
        ])
    else:
        verification_rows.append([
            Paragraph("Status", cell_label),
            Paragraph('<font color="#6b7280">Blockchain not connected</font>', cell_value_normal)
        ])
    
    if consultation_token.pdf_hash:
        verification_rows.append([
            Paragraph("PDF Hash (SHA-256)", cell_label),
            Paragraph(consultation_token.pdf_hash, small_mono)
        ])
    
    bc_table = Table(verification_rows, colWidths=[page_width * 0.22, page_width * 0.78])
    bc_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('LINEBELOW', (0, 0), (-1, -2), 0.3, colors.HexColor('#e5e7eb')),
    ]))
    elements.append(bc_table)
    elements.append(Spacer(1, 20))
    
    # ==========================================
    # IMPORTANT NOTE BOX
    # ==========================================
    note_data = [[Paragraph(
        '<font color="#92400e"><b>⚠ IMPORTANT:</b> Present this token at the clinic reception desk. '
        'This document is blockchain-verified and tamper-proof. Do not share with unauthorized persons.</font>',
        ParagraphStyle('NoteText', parent=styles['Normal'], fontSize=9,
                       textColor=colors.HexColor('#92400e'), leading=13)
    )]]
    note_table = Table(note_data, colWidths=[page_width])
    note_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), amber_bg),
        ('BOX', (0, 0), (-1, -1), 1, amber_border),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('ROUNDEDCORNERS', [4, 4, 4, 4]),
    ]))
    elements.append(note_table)
    elements.append(Spacer(1, 16))
    
    # ==========================================
    # FOOTER
    # ==========================================
    elements.append(HRFlowable(width="100%", thickness=0.5, color=border_color,
                               spaceAfter=6))
    generated_at = dj_timezone.localtime(dj_timezone.now()).strftime('%B %d, %Y at %I:%M %p IST')
    elements.append(Paragraph(
        f"Generated on {generated_at}  ·  RuralCare Healthcare Platform  ·  Blockchain-verified document",
        footer_style
    ))
    
    # Build PDF
    doc.build(elements)
    pdf_content = buffer.getvalue()
    buffer.close()
    
    pdf_hash = hashlib.sha256(pdf_content).hexdigest()
    pdf_file = ContentFile(pdf_content, name=f'consultation_token_{consultation_token.id}.pdf')
    
    return pdf_file, pdf_hash
