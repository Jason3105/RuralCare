"""
Script to add sample data to Insurance_SIP models
Run this with: python manage.py shell < Insurance_SIP/add_sample_data.py
"""
import uuid
from Insurance_SIP.models import GovernmentScheme, Eligibility, InsurancePolicy

# Create Government Schemes
print("Creating Government Schemes...")

scheme1 = GovernmentScheme.objects.create(
    id=uuid.uuid4(),
    name='Ayushman Bharat (PM-JAY)',
    scheme_type='health',
    description='Ayushman Bharat Pradhan Mantri Jan Arogya Yojana (PM-JAY) is a flagship scheme of Government of India which was launched as recommended by the National Health Policy 2017, to achieve the vision of Universal Health Coverage (UHC).',
    short_description='Free health insurance coverage up to ₹5 lakh per family per year for secondary and tertiary hospitalization.',
    state=None,
    coverage_amount=500000.00,
    benefits='• Cashless treatment at empanelled hospitals\n• Coverage for 1,393+ procedures\n• Pre and post-hospitalization expenses\n• No cap on family size\n• Coverage across India',
    required_documents='• Ration Card\n• SECC Data\n• Aadhaar Card\n• Address Proof\n• Income Certificate',
    application_steps='1. Check eligibility on official website\n2. Visit nearest Ayushman Mitra\n3. Submit required documents\n4. Get your Ayushman Card\n5. Visit empanelled hospitals',
    official_website='https://pmjay.gov.in/',
    is_active=True
)

scheme2 = GovernmentScheme.objects.create(
    id=uuid.uuid4(),
    name='Pradhan Mantri Suraksha Bima Yojana',
    scheme_type='accident',
    description='PMSBY is a one year accident insurance scheme offering coverage for death or disability due to accident. The scheme is renewable on an annual basis.',
    short_description='Accident insurance cover of ₹2 lakh at just ₹12 per year premium.',
    state=None,
    coverage_amount=200000.00,
    benefits='• Death benefit: ₹2 lakh\n• Total permanent disability: ₹2 lakh\n• Partial permanent disability: ₹1 lakh\n• Annual premium: Only ₹12\n• Auto-debit facility',
    required_documents='• Bank Account\n• Aadhaar Card\n• Age Proof (18-70 years)\n• Consent Form',
    application_steps='1. Visit your bank branch\n2. Fill enrolment form\n3. Give auto-debit consent\n4. Premium will be deducted annually\n5. Get SMS confirmation',
    official_website='https://www.india.gov.in/spotlight/pradhan-mantri-suraksha-bima-yojana',
    is_active=True
)

scheme3 = GovernmentScheme.objects.create(
    id=uuid.uuid4(),
    name='Atal Pension Yojana',
    scheme_type='pension',
    description='APY is a pension scheme for all citizens of India, particularly the poor, the underprivileged and the workers in the unorganised sector.',
    short_description='Guaranteed monthly pension starting from ₹1,000 to ₹5,000 after age 60.',
    state=None,
    coverage_amount=60000.00,
    benefits='• Guaranteed pension amount\n• Government co-contribution\n• Nomination facility\n• Minimum pension: ₹1,000/month\n• Maximum pension: ₹5,000/month',
    required_documents='• Aadhaar Card\n• Bank Account\n• Mobile Number\n• Age Proof (18-40 years)',
    application_steps='1. Visit your bank\n2. Fill APY registration form\n3. Choose pension amount\n4. Start monthly contributions\n5. Get pension at age 60',
    official_website='https://npscra.nsdl.co.in/atal-pension-yojana.php',
    is_active=True
)

print(f"✓ Created scheme: {scheme1.name}")
print(f"✓ Created scheme: {scheme2.name}")
print(f"✓ Created scheme: {scheme3.name}")

# Create Eligibility Criteria
print("\nCreating Eligibility Criteria...")

Eligibility.objects.create(
    id=uuid.uuid4(),
    scheme=scheme1,
    min_age=0,
    max_age=100,
    max_income=500000,
    state=None,
    gender=None,
    additional_criteria='Must be from economically weaker sections as per SECC 2011 data'
)

Eligibility.objects.create(
    id=uuid.uuid4(),
    scheme=scheme2,
    min_age=18,
    max_age=70,
    max_income=None,
    state=None,
    gender=None,
    additional_criteria='Must have savings bank account. Enrolled through auto-debit facility.'
)

Eligibility.objects.create(
    id=uuid.uuid4(),
    scheme=scheme3,
    min_age=18,
    max_age=40,
    max_income=None,
    state=None,
    gender=None,
    additional_criteria='Must have savings bank account. Not covered under any statutory social security scheme.'
)

print("✓ Created eligibility criteria for all schemes")

# Create Insurance Policies
print("\nCreating Insurance Policies...")

policy1 = InsurancePolicy.objects.create(
    id=uuid.uuid4(),
    name='HealthFirst Plus',
    policy_type='health',
    description='Comprehensive health insurance plan covering hospitalization, pre and post hospitalization expenses, daycare procedures, and ambulance charges.',
    short_description='Complete health protection with coverage up to ₹10 lakh and cashless treatment at 10,000+ hospitals.',
    premium_per_month=599.00,
    coverage_amount=1000000.00,
    key_features='• Cashless treatment at 10,000+ network hospitals\n• Coverage for 30 days pre-hospitalization\n• 60 days post-hospitalization coverage\n• Daycare procedures covered\n• Free health checkup every year\n• No room rent capping',
    cashless_hospitals=True,
    claim_support=True,
    add_ons_available='• Critical illness cover\n• Personal accident cover\n• Maternity cover\n• Mental health cover',
    min_age=18,
    max_age=65,
    is_active=True
)

policy2 = InsurancePolicy.objects.create(
    id=uuid.uuid4(),
    name='LifeSecure Family Plan',
    policy_type='family',
    description='Affordable family health insurance covering parents, spouse, and children with lifetime renewability.',
    short_description='Cover entire family with single premium starting at ₹899/month.',
    premium_per_month=899.00,
    coverage_amount=1500000.00,
    key_features='• Family floater coverage\n• Covers parents, spouse, children\n• Cashless hospitals across India\n• Maternity coverage included\n• New born baby covered from day 1\n• Unlimited automatic restoration',
    cashless_hospitals=True,
    claim_support=True,
    add_ons_available='• International coverage\n• Home healthcare\n• Second medical opinion\n• Organ donor expenses',
    min_age=21,
    max_age=75,
    is_active=True
)

policy3 = InsurancePolicy.objects.create(
    id=uuid.uuid4(),
    name='Senior Care Shield',
    policy_type='senior',
    description='Specially designed health insurance for senior citizens with pre-existing disease coverage.',
    short_description='Senior citizen plan with coverage up to ₹5 lakh, covering pre-existing diseases.',
    premium_per_month=1299.00,
    coverage_amount=500000.00,
    key_features='• Pre-existing diseases covered\n• No medical tests up to age 70\n• Coverage for age-related illnesses\n• Domiciliary hospitalization\n• AYUSH treatment covered\n• Free annual health checkup',
    cashless_hospitals=True,
    claim_support=True,
    add_ons_available='• Alzheimers cover\n• Long term care benefit\n• Mobility aids\n• Home nursing',
    min_age=60,
    max_age=80,
    is_active=True
)

print(f"✓ Created policy: {policy1.name}")
print(f"✓ Created policy: {policy2.name}")
print(f"✓ Created policy: {policy3.name}")

print("\n✅ Sample data added successfully!")
print(f"Total schemes: {GovernmentScheme.objects.count()}")
print(f"Total eligibility records: {Eligibility.objects.count()}")
print(f"Total policies: {InsurancePolicy.objects.count()}")
