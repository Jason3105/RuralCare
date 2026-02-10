from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, PatientProfile, DoctorProfile, DoctorKYC, PatientQRCode, QRCodeScanLog

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'user_type', 'is_staff', 'created_at')
    list_filter = ('user_type', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-created_at',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'phone_number', 'profile_picture')}),
        ('User Type', {'fields': ('user_type', 'supabase_user_id')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'date_of_birth', 'gender', 'blood_group')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name')
    list_filter = ('gender', 'blood_group')

@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'specialization', 'license_number', 'is_verified', 'hospital_affiliation')
    search_fields = ('user__username', 'user__email', 'license_number', 'specialization')
    list_filter = ('is_verified', 'specialization', 'department')

@admin.register(DoctorKYC)
class DoctorKYCAdmin(admin.ModelAdmin):
    list_display = ('get_doctor_name', 'status', 'created_at', 'verified_at')
    search_fields = ('doctor__user__username', 'doctor__user__email', 'full_name')
    list_filter = ('status', 'created_at', 'verified_at')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('doctor', 'full_name', 'date_of_birth', 'gender', 'nationality')
        }),
        ('Contact Information', {
            'fields': ('personal_email', 'mobile_number', 'residential_address', 'city', 'state', 'postal_code', 'country')
        }),
        ('Clinic Information', {
            'fields': ('clinic_address', 'clinic_latitude', 'clinic_longitude')
        }),
        ('Identification', {
            'fields': ('identity_document_type', 'identity_document_number', 'identity_document_file')
        }),
        ('Medical License', {
            'fields': ('license_number_verified', 'license_issuing_authority', 'license_issue_date', 'license_expiry_date', 'license_document')
        }),
        ('Educational Qualification', {
            'fields': ('medical_degree', 'medical_university', 'graduation_year', 'degree_certificate')
        }),
        ('Professional Information', {
            'fields': ('current_hospital', 'designation', 'department_specialty', 'years_of_practice', 'employment_document')
        }),
        ('Address Proof', {
            'fields': ('address_proof_type', 'address_proof_file')
        }),
        ('Bank Details', {
            'fields': ('bank_account_holder', 'bank_account_number', 'bank_ifsc_code')
        }),
        ('KYC Status', {
            'fields': ('status', 'rejection_reason', 'verification_notes')
        }),
        ('Verification', {
            'fields': ('verified_at', 'verified_by', 'created_at', 'updated_at')
        }),
    )
    
    def get_doctor_name(self, obj):
        return obj.doctor.user.get_full_name() or obj.doctor.user.username
    get_doctor_name.short_description = 'Doctor Name'
    
    def save_model(self, request, obj, form, change):
        if form.cleaned_data.get('status') == 'approved' and obj.verified_at is None:
            from django.utils import timezone
            obj.verified_at = timezone.now()
            obj.verified_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(PatientQRCode)
class PatientQRCodeAdmin(admin.ModelAdmin):
    list_display = ('patient', 'status', 'is_active', 'created_at', 'expires_at', 'last_scanned_at')
    search_fields = ('patient__username', 'patient__email', 'encrypted_token')
    list_filter = ('status', 'is_active', 'created_at')
    readonly_fields = ('id', 'encrypted_token', 'created_at', 'regenerated_at', 'last_scanned_at')
    
    fieldsets = (
        ('Patient', {
            'fields': ('patient', 'id')
        }),
        ('Token & QR Code', {
            'fields': ('encrypted_token', 'qr_code_image', 'qr_code_url')
        }),
        ('Status', {
            'fields': ('status', 'is_active', 'expires_at')
        }),
        ('Scan History', {
            'fields': ('last_scanned_at', 'last_scanned_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'regenerated_at')
        }),
    )


@admin.register(QRCodeScanLog)
class QRCodeScanLogAdmin(admin.ModelAdmin):
    list_display = ('qr_code', 'patient', 'scanned_by', 'scan_timestamp', 'access_granted', 'ip_address')
    search_fields = ('patient__username', 'patient__email', 'scanned_by__username', 'ip_address')
    list_filter = ('access_granted', 'scan_timestamp')
    readonly_fields = ('id', 'scan_timestamp')
    
    fieldsets = (
        ('QR Code & Patient', {
            'fields': ('qr_code', 'patient')
        }),
        ('Doctor Scan', {
            'fields': ('scanned_by',)
        }),
        ('Scan Details', {
            'fields': ('scan_timestamp', 'ip_address', 'user_agent')
        }),
        ('Access Control', {
            'fields': ('access_granted', 'denial_reason')
        }),
    )