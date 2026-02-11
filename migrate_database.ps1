# Database Migration Script
# Migrates data from filled DB to empty DB

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "RuralCare Database Migration" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Source Database (FILLED)
$SOURCE_HOST = "aws-1-ap-northeast-2.pooler.supabase.com"
$SOURCE_PORT = "6543"
$SOURCE_DB = "postgres"
$SOURCE_USER = "postgres.wotccnylbziwbmiuvhff"
$SOURCE_PASSWORD = "Jacell@100"

# Target Database (EMPTY)
$TARGET_HOST = "aws-1-ap-south-1.pooler.supabase.com"
$TARGET_PORT = "5432"
$TARGET_DB = "postgres"
$TARGET_USER = "postgres.kdbsweordecndyyaltos"
$TARGET_PASSWORD = "JacellJamble"

$TIMESTAMP = Get-Date -Format "yyyyMMdd_HHmmss"
$DUMP_FILE = "ruralcare_backup_$TIMESTAMP.sql"

Write-Host "Step 1: Dumping data from source database..." -ForegroundColor Yellow
Write-Host "Source: $SOURCE_HOST" -ForegroundColor Gray
Write-Host ""

# Set password for source
$env:PGPASSWORD = $SOURCE_PASSWORD

# Dump the database
pg_dump -h $SOURCE_HOST `
        -p $SOURCE_PORT `
        -U $SOURCE_USER `
        -d $SOURCE_DB `
        -F p `
        --no-owner `
        --no-acl `
        --clean `
        --if-exists `
        -f $DUMP_FILE

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Database dump successful!" -ForegroundColor Green
    Write-Host "Dump file: $DUMP_FILE" -ForegroundColor Gray
    Write-Host ""
} else {
    Write-Host "✗ Database dump failed!" -ForegroundColor Red
    Write-Host "Error: pg_dump command failed with exit code $LASTEXITCODE" -ForegroundColor Red
    Write-Host ""
    Write-Host "Make sure PostgreSQL client tools are installed:" -ForegroundColor Yellow
    Write-Host "Download from: https://www.postgresql.org/download/windows/" -ForegroundColor Cyan
    exit 1
}

Write-Host "Step 2: Importing data to target database..." -ForegroundColor Yellow
Write-Host "Target: $TARGET_HOST" -ForegroundColor Gray
Write-Host ""

# Set password for target
$env:PGPASSWORD = $TARGET_PASSWORD

# Import to target database
psql -h $TARGET_HOST `
     -p $TARGET_PORT `
     -U $TARGET_USER `
     -d $TARGET_DB `
     -f $DUMP_FILE `
     --quiet

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Database import successful!" -ForegroundColor Green
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Migration Complete!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Yellow
    Write-Host "1. Update your .env file with new database credentials" -ForegroundColor White
    Write-Host "2. Run: python manage.py migrate" -ForegroundColor White
    Write-Host "3. Test your application with the new database" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host "✗ Database import failed!" -ForegroundColor Red
    Write-Host "Error: psql command failed with exit code $LASTEXITCODE" -ForegroundColor Red
    Write-Host ""
    Write-Host "Check the dump file for errors: $DUMP_FILE" -ForegroundColor Yellow
    exit 1
}

# Clear password from environment
$env:PGPASSWORD = $null

Write-Host "Backup file saved: $DUMP_FILE" -ForegroundColor Gray
Write-Host "Keep this file safe in case you need to rollback!" -ForegroundColor Cyan
