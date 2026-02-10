"""
Management command to update pending blockchain transactions
"""
from django.core.management.base import BaseCommand
from blockchain.status_updater import update_pending_transactions


class Command(BaseCommand):
    help = 'Check and update pending blockchain transactions'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output',
        )
    
    def handle(self, *args, **options):
        verbose = options.get('verbose', False)
        
        self.stdout.write(self.style.WARNING('Checking pending blockchain transactions...'))
        
        result = update_pending_transactions()
        
        if result['success']:
            self.stdout.write(self.style.SUCCESS(
                f"\n✓ Update Complete:\n"
                f"  • Checked: {result['checked']} transactions\n"
                f"  • Confirmed: {result['confirmed']} transactions\n"
                f"  • Still Pending: {result['still_pending']} transactions\n"
                f"  • Failed: {result['failed']} transactions"
            ))
            
            if verbose and result['updated_scans']:
                self.stdout.write(self.style.SUCCESS('\nConfirmed Transactions:'))
                for scan in result['updated_scans']:
                    self.stdout.write(
                        f"  • Scan #{scan['scan_id']}: Block {scan['block_number']} "
                        f"(Log ID: {scan['log_id'] or 'N/A'})"
                    )
        else:
            self.stdout.write(self.style.ERROR(
                f"✗ Error: {result.get('error', 'Unknown error')}"
            ))
