from django.contrib import admin
from .models import MedicineIdentification, MedicineDatabase


@admin.register(MedicineIdentification)
class MedicineIdentificationAdmin(admin.ModelAdmin):
    list_display = ['medicine_name', 'user', 'status', 'medicine_form', 'created_at']
    list_filter = ['status', 'medicine_form', 'created_at']
    search_fields = ['medicine_name', 'generic_name', 'brand_name', 'extracted_text']
    readonly_fields = ['id', 'created_at', 'updated_at', 'processing_time_seconds']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('id', 'user', 'image', 'original_filename', 'status')
        }),
        ('Medicine Details', {
            'fields': ('medicine_name', 'generic_name', 'brand_name', 'manufacturer', 
                      'drug_class', 'medicine_form', 'strength')
        }),
        ('Analysis Data', {
            'fields': ('extracted_text', 'ocr_confidence', 'identification_confidence',
                      'image_analysis', 'ai_analysis'),
            'classes': ('collapse',)
        }),
        ('Medical Information', {
            'fields': ('description', 'uses', 'side_effects', 'warnings',
                      'contraindications', 'drug_interactions', 'dosage_instructions',
                      'storage_instructions', 'prescription_required'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'processing_time_seconds'),
            'classes': ('collapse',)
        }),
    )


@admin.register(MedicineDatabase)
class MedicineDatabaseAdmin(admin.ModelAdmin):
    list_display = ['medicine_name', 'generic_name', 'drug_class', 'identification_count']
    list_filter = ['drug_class', 'therapeutic_class']
    search_fields = ['medicine_name', 'generic_name']
