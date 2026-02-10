"""
Django management command to initialize Evidence Traceability Engine
Ingests default guidelines and rule-based references
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Initialize Evidence Traceability Engine with default data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--guidelines',
            action='store_true',
            help='Initialize default guidelines',
        )
        parser.add_argument(
            '--rules',
            action='store_true',
            help='Initialize default rule-based references',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Initialize all default data',
        )
        parser.add_argument(
            '--search-pubmed',
            action='store_true',
            help='Search and ingest PubMed studies',
        )
        parser.add_argument(
            '--cancer-type',
            type=str,
            help='Cancer type for PubMed search',
        )
        parser.add_argument(
            '--treatment-type',
            type=str,
            help='Treatment type for PubMed search',
        )
    
    def handle(self, *args, **options):
        try:
            # Import here to avoid import errors if models not ready
            from cancer_detection.evidence_ingester import EvidenceIngestionService
            from cancer_detection.rule_based_references import RuleBasedReferenceManager
            
            ingestion_service = EvidenceIngestionService()
            
            should_init_guidelines = options['guidelines'] or options['all']
            should_init_rules = options['rules'] or options['all']
            should_search_pubmed = options['search_pubmed']
            
            if should_init_guidelines:
                self.stdout.write('Initializing default guidelines...')
                result = ingestion_service.initialize_default_evidence()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Initialized {result['guidelines']} guidelines"
                    )
                )
            
            if should_init_rules:
                self.stdout.write('Initializing rule-based references...')
                admin_user = User.objects.filter(is_staff=True).first()
                count = RuleBasedReferenceManager.initialize_default_rules(admin_user)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Initialized {count} rule-based references"
                    )
                )
            
            if should_search_pubmed:
                cancer_type = options.get('cancer_type', 'breast')
                treatment_type = options.get('treatment_type', 'chemotherapy')
                
                self.stdout.write(
                    f'Searching PubMed for {cancer_type} + {treatment_type}...'
                )
                result = ingestion_service.search_and_ingest_studies(
                    cancer_type=cancer_type,
                    treatment_type=treatment_type,
                    max_results=5
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Ingested {result['studies_ingested']} PubMed studies"
                    )
                )
            
            if not (should_init_guidelines or should_init_rules or should_search_pubmed):
                # Default: initialize everything
                self.stdout.write('No options specified. Initializing all default data...')
                result = ingestion_service.initialize_default_evidence()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Initialized {result['guidelines']} guidelines"
                    )
                )
                
                admin_user = User.objects.filter(is_staff=True).first()
                count = RuleBasedReferenceManager.initialize_default_rules(admin_user)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Initialized {count} rule-based references"
                    )
                )
            
            self.stdout.write(
                self.style.SUCCESS(
                    '✓ Evidence Traceability Engine initialized successfully!'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Error initializing evidence engine: {str(e)}')
            )
            raise CommandError(f'Failed to initialize: {str(e)}')
