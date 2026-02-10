# Insurance_SIP Setup Guide

## Quick Setup Instructions

### Step 1: Run Migrations
```bash
python manage.py makemigrations Insurance_SIP
python manage.py migrate
```

### Step 2: Create Sample Data (Optional)

You can either use the SQL file or create data through Django admin:

#### Option A: Using SQL File
```bash
# For MySQL
mysql -u your_username -p your_database_name < Insurance_SIP/database_schema.sql

# For SQLite (use Django shell instead - see Option B)
```

#### Option B: Using Django Shell
```bash
python manage.py shell
```

Then run:
```python
from Insurance_SIP.models import GovernmentScheme, InsurancePolicy, Eligibility
import uuid

# Create Government Scheme
scheme1 = GovernmentScheme.objects.create(
    name="Ayushman Bharat (PM-JAY)",
    scheme_type="health",
    description="Ayushman Bharat Pradhan Mantri Jan Arogya Yojana (PM-JAY) is a flagship scheme...",
    short_description="Free health insurance coverage up to ₹5 lakh per family per year",
    coverage_amount=500000.00,
    benefits="• Cashless treatment\n• Coverage for 1,393+ procedures\n• Pre and post hospitalization",
    required_documents="• Ration Card\n• SECC Data\n• Aadhaar Card",
    application_steps="1. Check eligibility\n2. Visit Ayushman Mitra\n3. Submit documents",
    official_website="https://pmjay.gov.in/",
    is_active=True
)

# Create Eligibility
Eligibility.objects.create(
    scheme=scheme1,
    min_age=0,
    max_age=100,
    max_income=500000,
    additional_criteria="Must be from economically weaker sections"
)

# Create Insurance Policy
policy1 = InsurancePolicy.objects.create(
    name="HealthFirst Plus",
    policy_type="health",
    description="Comprehensive health insurance plan covering hospitalization...",
    short_description="Complete health protection with coverage up to ₹10 lakh",
    premium_per_month=599.00,
    coverage_amount=1000000.00,
    key_features="• Cashless treatment\n• Coverage for 30 days pre-hospitalization\n• Free health checkup",
    cashless_hospitals=True,
    claim_support=True,
    min_age=18,
    max_age=65,
    is_active=True
)

print("Sample data created successfully!")
```

### Step 3: Access the Application

Visit: `http://localhost:8000/insurance/`

### Step 4: Access Admin Panel

1. Visit: `http://localhost:8000/admin/`
2. Login with your superuser credentials
3. Navigate to "Insurance & Government Schemes" section
4. Add/Edit schemes, policies, and manage applications

## Database Tables Created

1. **Insurance_SIP_governmentscheme** - Government schemes
2. **Insurance_SIP_eligibility** - Eligibility criteria
3. **Insurance_SIP_insurancepolicy** - Insurance policies
4. **Insurance_SIP_application** - User applications

## Features Available

- ✅ Landing page with hero section
- ✅ Government schemes browsing
- ✅ Insurance policies comparison
- ✅ Eligibility checker
- ✅ Application tracking
- ✅ Secure document upload
- ✅ Admin management

## URLs

| URL | Description |
|-----|-------------|
| `/insurance/` | Landing page |
| `/insurance/schemes/` | Browse government schemes |
| `/insurance/schemes/<id>/` | Scheme details |
| `/insurance/schemes/<id>/apply/` | Apply for scheme |
| `/insurance/policies/` | Browse insurance policies |
| `/insurance/policies/<id>/` | Policy details |
| `/insurance/policies/<id>/apply/` | Apply for policy |
| `/insurance/check-eligibility/` | Check eligibility |
| `/insurance/track/` | Track all applications |
| `/insurance/track/<app_id>/` | Track specific application |

## Troubleshooting

### Issue: Tables not created
**Solution:** Run migrations:
```bash
python manage.py makemigrations Insurance_SIP
python manage.py migrate
```

### Issue: No sample data showing
**Solution:** Create data via admin panel or Django shell

### Issue: Templates not loading
**Solution:** Check that `Insurance_SIP` is in INSTALLED_APPS

### Issue: Static files not loading
**Solution:** Run:
```bash
python manage.py collectstatic
```

## Next Steps

1. Customize the landing page design
2. Add more government schemes through admin
3. Add more insurance policies
4. Configure email notifications for applications
5. Add payment gateway integration for policies
6. Add document upload functionality
7. Customize eligibility checking logic

## Support

For questions or issues, refer to the README.md file or contact the development team.
