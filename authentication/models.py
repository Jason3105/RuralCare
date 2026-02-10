from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid
import secrets
from django.utils import timezone
from datetime import timedelta

class User(AbstractUser):
    USER_TYPE_CHOICES = [
        ('patient', 'Patient'),
        ('doctor', 'Doctor'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES)
    supabase_user_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    profile_picture = models.URLField(max_length=500, null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.username} ({self.user_type})"
    
    class Meta:
        db_table = 'users'


class PatientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='patient_profile')
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, null=True, blank=True)
    blood_group = models.CharField(max_length=5, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    emergency_contact_name = models.CharField(max_length=100, null=True, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, null=True, blank=True)
    medical_history = models.TextField(null=True, blank=True)
    allergies = models.TextField(null=True, blank=True)
    current_medications = models.TextField(null=True, blank=True)
    
    # Telegram Integration
    telegram_chat_id = models.CharField(max_length=100, null=True, blank=True, 
                                        help_text='Telegram Chat ID for notifications')
    telegram_username = models.CharField(max_length=100, null=True, blank=True,
                                         help_text='Telegram username')
    telegram_notifications_enabled = models.BooleanField(default=True,
                                                         help_text='Enable Telegram notifications')
    
    def __str__(self):
        return f"Patient Profile - {self.user.username}"
    
    class Meta:
        db_table = 'patient_profiles'


class PatientQRCode(models.Model):
    """
    Secure QR Code system for patient access
    """
    QR_STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('expired', 'Expired'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.OneToOneField(User, on_delete=models.CASCADE, related_name='qr_code')
    
    # Encrypted token - non-guessable, unique per patient
    encrypted_token = models.CharField(max_length=255, unique=True, db_index=True)
    
    # QR Code image
    qr_code_image = models.ImageField(upload_to='patient_qr_codes/', null=True, blank=True)
    qr_code_url = models.URLField(max_length=500, null=True, blank=True)
    
    # Status and security
    status = models.CharField(max_length=20, choices=QR_STATUS_CHOICES, default='active')
    is_active = models.BooleanField(default=True)
    
    # Expiration
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    regenerated_at = models.DateTimeField(null=True, blank=True)
    last_scanned_at = models.DateTimeField(null=True, blank=True)
    last_scanned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                         related_name='scanned_patient_qr_codes')
    
    class Meta:
        db_table = 'patient_qr_codes'
        verbose_name = 'Patient QR Code'
        verbose_name_plural = 'Patient QR Codes'
    
    def __str__(self):
        return f"QR Code for {self.patient.username}"
    
    def is_expired(self):
        """Check if QR code is expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def get_status(self):
        """Get current status of QR code"""
        if not self.is_active:
            return 'inactive'
        if self.is_expired():
            return 'expired'
        return 'active'


class QRCodeScanLog(models.Model):
    """
    Audit log for every QR code scan
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    qr_code = models.ForeignKey(PatientQRCode, on_delete=models.CASCADE, related_name='scan_logs')
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='qr_scan_logs_as_patient')
    scanned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, 
                                    related_name='qr_scans_performed', limit_choices_to={'user_type': 'doctor'})
    
    # Scan details
    scan_timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Result
    access_granted = models.BooleanField(default=True)
    denial_reason = models.CharField(max_length=255, blank=True, null=True)
    
    # Blockchain verification fields
    blockchain_tx_hash = models.CharField(max_length=66, blank=True, null=True, 
                                          help_text='Ethereum transaction hash')
    blockchain_log_id = models.BigIntegerField(blank=True, null=True,
                                                help_text='Smart contract log ID')
    blockchain_block_number = models.BigIntegerField(blank=True, null=True,
                                                      help_text='Block number on blockchain')
    blockchain_verified = models.BooleanField(default=False,
                                               help_text='Whether logged on blockchain')
    
    class Meta:
        db_table = 'qr_code_scan_logs'
        ordering = ['-scan_timestamp']
        verbose_name = 'QR Code Scan Log'
        verbose_name_plural = 'QR Code Scan Logs'
    
    def __str__(self):
        return f"Scan by Dr. {self.scanned_by.username if self.scanned_by else 'Unknown'} - {self.scan_timestamp}"
    
    def get_etherscan_url(self):
        """Get Etherscan URL for this transaction"""
        if self.blockchain_tx_hash:
            return f"https://sepolia.etherscan.io/tx/{self.blockchain_tx_hash}"
        return None


class DoctorProfile(models.Model):
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]
    
    SPECIALIZATION_CHOICES = [
        ('general_medicine', 'General Medicine'),
        ('internal_medicine', 'Internal Medicine'),
        ('family_medicine', 'Family Medicine'),
        ('pediatrics', 'Pediatrics'),
        ('surgery', 'General Surgery'),
        ('orthopedics', 'Orthopedics'),
        ('cardiology', 'Cardiology'),
        ('neurology', 'Neurology'),
        ('psychiatry', 'Psychiatry'),
        ('dermatology', 'Dermatology'),
        ('ophthalmology', 'Ophthalmology'),
        ('ent', 'ENT (Ear, Nose & Throat)'),
        ('gynecology', 'Gynecology & Obstetrics'),
        ('urology', 'Urology'),
        ('nephrology', 'Nephrology'),
        ('gastroenterology', 'Gastroenterology'),
        ('pulmonology', 'Pulmonology'),
        ('endocrinology', 'Endocrinology'),
        ('rheumatology', 'Rheumatology'),
        ('oncology', 'Oncology'),
        ('surgical_oncology', 'Surgical Oncology'),
        ('radiation_oncology', 'Radiation Oncology'),
        ('medical_oncology', 'Medical Oncology'),
        ('pediatric_oncology', 'Pediatric Oncology'),
        ('hematology', 'Hematology'),
        ('radiology', 'Radiology'),
        ('pathology', 'Pathology'),
        ('anesthesiology', 'Anesthesiology'),
        ('emergency_medicine', 'Emergency Medicine'),
        ('critical_care', 'Critical Care Medicine'),
        ('plastic_surgery', 'Plastic Surgery'),
        ('neurosurgery', 'Neurosurgery'),
        ('cardiothoracic_surgery', 'Cardiothoracic Surgery'),
        ('vascular_surgery', 'Vascular Surgery'),
        ('transplant_surgery', 'Transplant Surgery'),
        ('infectious_disease', 'Infectious Disease'),
        ('allergy_immunology', 'Allergy & Immunology'),
        ('geriatrics', 'Geriatrics'),
        ('sports_medicine', 'Sports Medicine'),
        ('physical_medicine', 'Physical Medicine & Rehabilitation'),
        ('occupational_medicine', 'Occupational Medicine'),
        ('preventive_medicine', 'Preventive Medicine'),
        ('other', 'Other'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile')
    
    # Basic Information
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    
    # Professional Information
    specialization = models.CharField(max_length=100, choices=SPECIALIZATION_CHOICES, null=True, blank=True)
    license_number = models.CharField(max_length=50, unique=True)
    years_of_experience = models.IntegerField(null=True, blank=True)
    
    # Qualifications
    medical_degree = models.CharField(max_length=200, null=True, blank=True, help_text="e.g., MBBS, MD, DM")
    additional_qualifications = models.TextField(null=True, blank=True, help_text="Other certifications or qualifications")
    
    # Work Information
    hospital_affiliation = models.CharField(max_length=200, null=True, blank=True)
    hospital_phone = models.CharField(max_length=20, null=True, blank=True, help_text="Hospital contact number")
    department = models.CharField(max_length=100, null=True, blank=True)
    
    # Location Information
    clinic_address = models.TextField(null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    pincode = models.CharField(max_length=10, null=True, blank=True)
    country = models.CharField(max_length=100, default='India')
    
    # Professional Details
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    bio = models.TextField(null=True, blank=True, help_text="Brief description about yourself and expertise")
    languages_spoken = models.CharField(max_length=200, null=True, blank=True, help_text="Comma-separated languages")
    
    # Verification & Status
    is_verified = models.BooleanField(default=False)
    profile_completed = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    
    def __str__(self):
        return f"Dr. {self.user.username} - {self.specialization}"
    
    class Meta:
        db_table = 'doctor_profiles'


class DoctorKYC(models.Model):
    KYC_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('incomplete', 'Incomplete'),
    ]
    
    IDENTITY_DOCUMENT_CHOICES = [
        ('passport', 'Passport'),
        ('aadhaar', 'Aadhaar'),
        ('national_id', 'National ID'),
        ('driving_license', 'Driving License'),
    ]
    
    ADDRESS_PROOF_CHOICES = [
        ('utility_bill', 'Utility Bill'),
        ('rental_agreement', 'Rental Agreement'),
        ('property_deed', 'Property Deed'),
        ('bank_statement', 'Bank Statement'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doctor = models.OneToOneField(DoctorProfile, on_delete=models.CASCADE, related_name='kyc')
    
    # Basic Information
    full_name = models.CharField(max_length=200)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=20, choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')])
    nationality = models.CharField(max_length=100, null=True, blank=True)
    
    # Contact Information
    personal_email = models.EmailField(null=True, blank=True)
    mobile_number = models.CharField(max_length=20, null=True, blank=True)
    residential_address = models.TextField(null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    postal_code = models.CharField(max_length=10, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)

    clinic_address = models.TextField(null=True, blank=True)
    clinic_latitude = models.FloatField(null=True, blank=True)
    clinic_longitude = models.FloatField(null=True, blank=True)
    
    # Medical License Information
    license_number_verified = models.CharField(max_length=100, null=True, blank=True)
    license_issuing_authority = models.CharField(max_length=200, null=True, blank=True)
    license_issue_date = models.DateField(null=True, blank=True)
    license_expiry_date = models.DateField(null=True, blank=True)
    license_document = models.FileField(upload_to='doctor_kyc/license_documents/', null=True, blank=True)
    
    # Educational Qualification
    medical_degree = models.CharField(max_length=200, null=True, blank=True)
    medical_university = models.CharField(max_length=200, null=True, blank=True)
    graduation_year = models.IntegerField(null=True, blank=True)
    degree_certificate = models.FileField(upload_to='doctor_kyc/degree_documents/', null=True, blank=True)
    
    # Professional Information
    current_hospital = models.CharField(max_length=200, null=True, blank=True)
    designation = models.CharField(max_length=100, null=True, blank=True)
    department_specialty = models.CharField(max_length=100, null=True, blank=True)
    years_of_practice = models.IntegerField(null=True, blank=True)
    employment_document = models.FileField(upload_to='doctor_kyc/employment_documents/', null=True, blank=True)
    
    # Identity Documents
    identity_document_type = models.CharField(max_length=50, choices=IDENTITY_DOCUMENT_CHOICES, null=True, blank=True)
    identity_document_number = models.CharField(max_length=100, null=True, blank=True)
    identity_document_file = models.FileField(upload_to='doctor_kyc/identity_documents/', null=True, blank=True)
    
    # Address Proof
    address_proof_type = models.CharField(max_length=50, choices=ADDRESS_PROOF_CHOICES, null=True, blank=True)
    address_proof_file = models.FileField(upload_to='doctor_kyc/address_proofs/', null=True, blank=True)
    
    # Bank Details (for future payments)
    bank_account_holder = models.CharField(max_length=200, null=True, blank=True)
    bank_account_number = models.CharField(max_length=20, null=True, blank=True)
    bank_ifsc_code = models.CharField(max_length=20, null=True, blank=True)
    
    # Status and verification
    status = models.CharField(max_length=20, choices=KYC_STATUS_CHOICES, default='pending')
    rejection_reason = models.TextField(blank=True, null=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='verified_doctors')
    verification_notes = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"KYC - Dr. {self.doctor.user.username}"
    
    class Meta:
        db_table = 'doctor_kyc'
        verbose_name = 'Doctor KYC'
        verbose_name_plural = 'Doctor KYC'


class MedicalRecord(models.Model):
    DOCUMENT_TYPE_CHOICES = [
        ('prescription', 'Prescription'),
        ('lab_report', 'Lab Report'),
        ('imaging_report', 'Imaging Report'),
        ('discharge_summary', 'Discharge Summary'),
        ('medical_history', 'Medical History'),
        ('vaccination_record', 'Vaccination Record'),
        ('other', 'Other'),
    ]
    
    OCR_STATUS_CHOICES = [
        ('pending', 'Pending OCR'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='medical_records')
    
    # Document Information
    title = models.CharField(max_length=255)
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPE_CHOICES)
    document_file = models.FileField(upload_to='medical_records/%Y/%m/%d/')
    
    # OCR Related Fields
    extracted_text = models.TextField(blank=True, null=True)
    extracted_data = models.JSONField(blank=True, null=True)  # Structured data extracted from OCR
    ocr_status = models.CharField(max_length=20, choices=OCR_STATUS_CHOICES, default='processing')
    ocr_confidence = models.FloatField(null=True, blank=True)  # OCR confidence score (0-100)
    
    # Metadata
    report_date = models.DateField(null=True, blank=True)
    hospital_name = models.CharField(max_length=200, blank=True, null=True)
    doctor_name = models.CharField(max_length=100, blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title} - {self.patient.username}"
    
    class Meta:
        db_table = 'medical_records'
        ordering = ['-created_at']
        verbose_name = 'Medical Record'
        verbose_name_plural = 'Medical Records'
