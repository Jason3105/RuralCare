"""
Add 3 more affordable insurance policies
Run this with: Get-Content Insurance_SIP\add_more_policies.py | python manage.py shell
"""
import uuid
from Insurance_SIP.models import InsurancePolicy

print("Adding 3 more affordable insurance policies...")

# Policy 4: Life Insurance
policy4 = InsurancePolicy.objects.create(
    id=uuid.uuid4(),
    name='SecureLife Term Plan',
    policy_type='life',
    description='Affordable term life insurance providing financial security to your family in case of unfortunate events. Pure protection plan with high coverage at low premium.',
    short_description='Term life insurance with coverage up to ₹50 lakh at just ₹299/month. Protect your family\'s future.',
    premium_per_month=299.00,
    coverage_amount=5000000.00,
    key_features='• Life cover up to ₹50 lakh\n• Affordable monthly premium\n• Tax benefits under 80C & 10(10D)\n• Online policy issuance\n• Flexible payment terms\n• Accidental death benefit',
    cashless_hospitals=False,
    claim_support=True,
    add_ons_available='• Critical illness rider\n• Accidental disability benefit\n• Waiver of premium\n• Income benefit',
    min_age=18,
    max_age=60,
    is_active=True
)

# Policy 5: Accident Cover
policy5 = InsurancePolicy.objects.create(
    id=uuid.uuid4(),
    name='SafeGuard Accident Shield',
    policy_type='accident',
    description='Comprehensive personal accident insurance covering death, permanent disability, and temporary disability due to accidents. 24x7 protection wherever you go.',
    short_description='Complete accident protection with ₹10 lakh cover at ₹199/month. Includes hospitalization expenses.',
    premium_per_month=199.00,
    coverage_amount=1000000.00,
    key_features='• Accidental death cover: ₹10 lakh\n• Permanent disability: ₹10 lakh\n• Temporary disability: Weekly benefit\n• Hospitalization expenses covered\n• Ambulance charges included\n• No medical tests required',
    cashless_hospitals=True,
    claim_support=True,
    add_ons_available='• Child education benefit\n• EMI protection cover\n• Broken bone benefit\n• Burns treatment cover',
    min_age=18,
    max_age=70,
    is_active=True
)

# Policy 6: Budget Family Plan
policy6 = InsurancePolicy.objects.create(
    id=uuid.uuid4(),
    name='Family Care Essential',
    policy_type='family',
    description='Budget-friendly family health insurance covering spouse and 2 children. Basic hospitalization coverage with essential features at affordable premium.',
    short_description='Protect your family of 4 with ₹5 lakh health cover at just ₹499/month. Includes children vaccination.',
    premium_per_month=499.00,
    coverage_amount=500000.00,
    key_features='• Family floater: Self, spouse, 2 kids\n• Hospitalization coverage\n• Daycare procedures\n• Pre-existing after 2 years\n• Free health checkup\n• Child vaccination covered',
    cashless_hospitals=True,
    claim_support=True,
    add_ons_available='• Maternity cover\n• New born baby cover\n• Dental treatment\n• OPD expenses',
    min_age=21,
    max_age=65,
    is_active=True
)

print(f"✓ Created policy: {policy4.name} - ₹{policy4.premium_per_month}/month")
print(f"✓ Created policy: {policy5.name} - ₹{policy5.premium_per_month}/month")
print(f"✓ Created policy: {policy6.name} - ₹{policy6.premium_per_month}/month")

print(f"\n✅ 3 more policies added successfully!")
print(f"Total policies now: {InsurancePolicy.objects.count()}")
