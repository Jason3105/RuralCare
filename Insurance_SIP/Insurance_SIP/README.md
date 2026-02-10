# Insurance_SIP - Government Schemes & Insurance Platform

A modern, trustworthy insurance web application for exploring government schemes and purchasing insurance policies.

## Features

### 🏛️ Government Schemes
- Browse verified government insurance schemes
- Check eligibility instantly
- Apply online with paperless process
- Track application status

### 🛡️ Insurance Policies
- Compare multiple insurance plans
- Health, Life, Accident, Family, and Senior Citizen plans
- Transparent pricing
- 24/7 claim support

### 🔒 Trust & Security
- End-to-end encryption
- Verified scheme information
- Secure document upload
- Bank-grade security

## Installation

1. **Add to INSTALLED_APPS** in `cancer_treatment_system/settings.py`:
```python
INSTALLED_APPS = [
    # ... existing apps
    'Insurance_SIP',
]
```

2. **Add URL pattern** to `cancer_treatment_system/urls.py`:
```python
urlpatterns = [
    # ... existing patterns
    path('insurance/', include('Insurance_SIP.urls')),
]
```

3. **Run migrations**:
```bash
python manage.py makemigrations Insurance_SIP
python manage.py migrate
```

4. **Create superuser** (if not exists):
```bash
python manage.py createsuperuser
```

5. **Load sample data** (optional):
```bash
# Run the SQL queries from database_schema.sql in your database editor
# Or use Django shell to create sample data
```

## Database Setup

### Option 1: Using Django Migrations (Recommended)
```bash
python manage.py makemigrations Insurance_SIP
python manage.py migrate Insurance_SIP
```

### Option 2: Using SQL Directly
Run the queries in `database_schema.sql` using your database editor or command line:
```bash
mysql -u username -p database_name < Insurance_SIP/database_schema.sql
```

## Admin Panel

Access the admin panel at `http://localhost:8000/admin/` to:
- Add/Edit Government Schemes
- Add/Edit Insurance Policies
- Manage Applications
- Set Eligibility Criteria

## URL Structure

- `/insurance/` - Landing page
- `/insurance/schemes/` - Government schemes listing
- `/insurance/policies/` - Insurance policies listing
- `/insurance/check-eligibility/` - Eligibility checker
- `/insurance/track/` - Track applications

## Models

### GovernmentScheme
Stores government insurance schemes with details, eligibility, and benefits.

### InsurancePolicy
Stores private insurance policies with pricing and features.

### Application
Tracks user applications for schemes and policies.

### Eligibility
Defines eligibility criteria for government schemes.

## Design Features

✅ Modern, clean UI with Tailwind CSS
✅ Trust-building elements (verified badges, stats)
✅ Mobile-responsive design
✅ Dark mode support
✅ Smooth animations and transitions
✅ Professional fintech styling
✅ User-friendly for rural users

## Sample Data Included

The SQL script includes sample data for:
- 3 Government Schemes (Ayushman Bharat, PMSBY, APY)
- 3 Insurance Policies (Health, Family, Senior)
- Eligibility criteria for each scheme

## Support

For issues or questions, contact the development team.

## License

Proprietary - Part of RuralCare Platform
