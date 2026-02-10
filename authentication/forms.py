from django import forms
from .models import DoctorProfile, MedicalRecord, PatientProfile, User

class DoctorProfileForm(forms.ModelForm):
    class Meta:
        model = DoctorProfile
        fields = [
            'gender', 'date_of_birth', 'specialization', 'license_number',
            'years_of_experience', 'medical_degree', 'additional_qualifications',
            'hospital_affiliation', 'department', 'clinic_address', 'city',
            'state', 'pincode', 'country', 'consultation_fee', 'bio',
            'languages_spoken'
        ]
        widgets = {
            'gender': forms.Select(attrs={'placeholder': 'Select Gender'}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'specialization': forms.Select(attrs={'placeholder': 'Select Specialization'}),
            'license_number': forms.TextInput(attrs={'placeholder': 'Medical License Number'}),
            'years_of_experience': forms.NumberInput(attrs={'placeholder': 'Years of Experience'}),
            'medical_degree': forms.TextInput(attrs={'placeholder': 'e.g., MBBS, MD, DM'}),
            'additional_qualifications': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Any additional certifications or qualifications'}),
            'hospital_affiliation': forms.TextInput(attrs={'placeholder': 'Hospital/Clinic Name'}),
            'department': forms.TextInput(attrs={'placeholder': 'Department'}),
            'clinic_address': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Clinic/Hospital Address'}),
            'city': forms.TextInput(attrs={'placeholder': 'City'}),
            'state': forms.TextInput(attrs={'placeholder': 'State'}),
            'pincode': forms.TextInput(attrs={'placeholder': 'Pincode'}),
            'country': forms.TextInput(attrs={'placeholder': 'Country'}),
            'consultation_fee': forms.NumberInput(attrs={'placeholder': 'Consultation Fee (₹)'}),
            'bio': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Brief description about yourself and your expertise'}),
            'languages_spoken': forms.TextInput(attrs={'placeholder': 'e.g., English, Hindi, Tamil'}),
        }
    
    def clean_pincode(self):
        pincode = self.cleaned_data.get('pincode')
        if pincode and not pincode.isdigit():
            raise forms.ValidationError("Pincode must contain only digits")
        if pincode and len(pincode) != 6:
            raise forms.ValidationError("Pincode must be 6 digits")
        return pincode
    
    def clean_years_of_experience(self):
        years = self.cleaned_data.get('years_of_experience')
        if years and years < 0:
            raise forms.ValidationError("Years of experience cannot be negative")
        if years and years > 60:
            raise forms.ValidationError("Please enter a valid years of experience")
        return years


class MedicalRecordForm(forms.ModelForm):
    class Meta:
        model = MedicalRecord
        fields = ['title', 'document_type', 'document_file', 'report_date']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-ring focus:border-input text-foreground transition-colors',
                'placeholder': 'e.g., Blood Test Results - Dec 2025'
            }),
            'document_type': forms.Select(attrs={
                'class': 'w-full px-4 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-ring focus:border-input text-foreground transition-colors'
            }),
            'document_file': forms.FileInput(attrs={
                'class': 'sr-only',
                'accept': '.pdf,.jpg,.jpeg,.png'
            }),
            'report_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-4 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-ring focus:border-input text-foreground transition-colors'
            }),
        }
    
    def clean_document_file(self):
        file = self.cleaned_data.get('document_file')
        if file:
            # Check file size (max 10MB)
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError("File size must be less than 10MB")
            
            # Check file extension
            allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
            file_ext = file.name.lower().split('.')[-1]
            if f'.{file_ext}' not in allowed_extensions:
                raise forms.ValidationError("Only PDF, JPG, JPEG, and PNG files are allowed")
        
        return file


class PatientProfileForm(forms.ModelForm):
    # User fields
    first_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-primary focus:border-input text-foreground transition-colors',
            'placeholder': 'First Name'
        })
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-primary focus:border-input text-foreground transition-colors',
            'placeholder': 'Last Name'
        })
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-primary focus:border-input text-foreground transition-colors',
            'placeholder': 'Email Address'
        })
    )
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-primary focus:border-input text-foreground transition-colors',
            'placeholder': 'Phone Number'
        })
    )
    
    class Meta:
        model = PatientProfile
        fields = [
            'date_of_birth', 'gender', 'blood_group', 'address',
            'emergency_contact_name', 'emergency_contact_phone',
            'medical_history', 'allergies', 'current_medications'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-4 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-primary focus:border-input text-foreground transition-colors'
            }),
            'gender': forms.Select(
                choices=[('', 'Select Gender'), ('male', 'Male'), ('female', 'Female'), ('other', 'Other')],
                attrs={
                    'class': 'w-full px-4 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-primary focus:border-input text-foreground transition-colors'
                }
            ),
            'blood_group': forms.Select(
                choices=[
                    ('', 'Select Blood Group'),
                    ('A+', 'A+'), ('A-', 'A-'),
                    ('B+', 'B+'), ('B-', 'B-'),
                    ('AB+', 'AB+'), ('AB-', 'AB-'),
                    ('O+', 'O+'), ('O-', 'O-')
                ],
                attrs={
                    'class': 'w-full px-4 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-primary focus:border-input text-foreground transition-colors'
                }
            ),
            'address': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full px-4 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-primary focus:border-input text-foreground transition-colors',
                'placeholder': 'Enter your full address'
            }),
            'emergency_contact_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-primary focus:border-input text-foreground transition-colors',
                'placeholder': 'Emergency Contact Name'
            }),
            'emergency_contact_phone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-primary focus:border-input text-foreground transition-colors',
                'placeholder': 'Emergency Contact Phone'
            }),
            'medical_history': forms.Textarea(attrs={
                'rows': 4,
                'class': 'w-full px-4 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-primary focus:border-input text-foreground transition-colors',
                'placeholder': 'Brief medical history (e.g., past illnesses, surgeries)'
            }),
            'allergies': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full px-4 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-primary focus:border-input text-foreground transition-colors',
                'placeholder': 'Any known allergies (medications, food, etc.)'
            }),
            'current_medications': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full px-4 py-2 bg-background border border-input rounded-md focus:ring-2 focus:ring-primary focus:border-input text-foreground transition-colors',
                'placeholder': 'Current medications you are taking'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Initialize user fields if user is provided
        if self.user:
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
            self.fields['email'].initial = self.user.email
            self.fields['phone_number'].initial = self.user.phone_number
    
    def save(self, commit=True):
        profile = super().save(commit=False)
        
        # Update user fields
        if self.user:
            self.user.first_name = self.cleaned_data.get('first_name', '')
            self.user.last_name = self.cleaned_data.get('last_name', '')
            self.user.email = self.cleaned_data.get('email', '')
            self.user.phone_number = self.cleaned_data.get('phone_number', '')
            if commit:
                self.user.save()
        
        if commit:
            profile.save()
        return profile
