# Database Migration - Quick Start
# This script guides you through the migration process

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  RuralCare Database Migration" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "You are about to migrate data from:" -ForegroundColor Yellow
Write-Host "  Source: aws-1-ap-northeast-2.pooler.supabase.com" -ForegroundColor Gray
Write-Host "  Target: aws-1-ap-south-1.pooler.supabase.com" -ForegroundColor Gray
Write-Host ""

Write-Host "This will:" -ForegroundColor White
Write-Host "  1. Export all data from your filled database" -ForegroundColor Gray
Write-Host "  2. Import it into your empty database" -ForegroundColor Gray
Write-Host "  3. Create a backup file for safety" -ForegroundColor Gray
Write-Host ""

Write-Host "⚠️  IMPORTANT:" -ForegroundColor Red
Write-Host "  - Ensure you have stable internet connection" -ForegroundColor Yellow
Write-Host "  - This may take 2-15 minutes depending on data size" -ForegroundColor Yellow
Write-Host "  - Your original database will NOT be modified" -ForegroundColor Yellow
Write-Host ""

$response = Read-Host "Continue? (yes/no)"

if ($response -ne "yes") {
    Write-Host ""
    Write-Host "Migration cancelled." -ForegroundColor Yellow
    Write-Host ""
    exit 0
}

Write-Host ""
Write-Host "Checking prerequisites..." -ForegroundColor Cyan
Write-Host ""

# Check if PostgreSQL tools are available
$pgDumpAvailable = Get-Command pg_dump -ErrorAction SilentlyContinue
$pythonAvailable = Get-Command python -ErrorAction SilentlyContinue

if ($pgDumpAvailable) {
    Write-Host "✓ PostgreSQL tools found (pg_dump available)" -ForegroundColor Green
    Write-Host "  Using Method 1: Native PostgreSQL migration (faster)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Starting migration..." -ForegroundColor Yellow
    Write-Host ""
    
    # Run the PostgreSQL migration script
    & "$PSScriptRoot\migrate_database.ps1"
    
} elseif ($pythonAvailable) {
    Write-Host "○ PostgreSQL tools not found" -ForegroundColor Yellow
    Write-Host "✓ Python found" -ForegroundColor Green
    Write-Host "  Using Method 2: Django-based migration (slower but works)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Starting migration..." -ForegroundColor Yellow
    Write-Host ""
    
    # Run the Python migration script
    python "$PSScriptRoot\migrate_database.py"
    
} else {
    Write-Host "✗ Neither PostgreSQL tools nor Python found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install one of the following:" -ForegroundColor Yellow
    Write-Host "  Option 1: PostgreSQL client tools" -ForegroundColor White
    Write-Host "    Download: https://www.postgresql.org/download/windows/" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Option 2: Python" -ForegroundColor White
    Write-Host "    Download: https://www.python.org/downloads/" -ForegroundColor Cyan
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "1. Update your .env file with new database credentials" -ForegroundColor White
Write-Host "2. Test locally: python manage.py migrate" -ForegroundColor White
Write-Host "3. Update Render environment variables" -ForegroundColor White
Write-Host "4. See DATABASE_MIGRATION_GUIDE.md for detailed instructions" -ForegroundColor White
Write-Host ""
