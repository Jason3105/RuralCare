from django.apps import AppConfig


class PatientPortalConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'patient_portal'
    verbose_name = 'Patient Portal'
    
    def ready(self):
        """Import signals when app is ready"""
        import patient_portal.signals