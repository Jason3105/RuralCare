# 📋 SQL QUERIES TO RUN IN YOUR DATABASE EDITOR

Copy and paste these queries into your database editor to create all required tables and sample data.

---

## ⚠️ IMPORTANT NOTES

1. **For MySQL/MariaDB:** Use these queries as-is
2. **For PostgreSQL:** Replace `CHAR(36)` with `UUID` type
3. **For SQLite:** Django migrations are recommended instead
4. **User Table:** Ensure `authentication_customuser` table exists first

---

## 🗃️ TABLE CREATION QUERIES

### 1. Government Schemes Table

```sql
CREATE TABLE IF NOT EXISTS Insurance_SIP_governmentscheme (
    id CHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    scheme_type VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    short_description VARCHAR(300) NOT NULL,
    state VARCHAR(100),
    coverage_amount DECIMAL(12, 2) NOT NULL,
    benefits TEXT NOT NULL,
    required_documents TEXT NOT NULL,
    application_steps TEXT NOT NULL,
    official_website VARCHAR(200),
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_scheme_type (scheme_type),
    INDEX idx_state (state),
    INDEX idx_is_active (is_active)
);
```

### 2. Eligibility Criteria Table

```sql
CREATE TABLE IF NOT EXISTS Insurance_SIP_eligibility (
    id CHAR(36) PRIMARY KEY,
    scheme_id CHAR(36) NOT NULL UNIQUE,
    min_age INT NOT NULL,
    max_age INT NOT NULL,
    max_income DECIMAL(12, 2),
    state VARCHAR(100),
    gender VARCHAR(20),
    additional_criteria TEXT,
    FOREIGN KEY (scheme_id) REFERENCES Insurance_SIP_governmentscheme(id) ON DELETE CASCADE,
    INDEX idx_age_range (min_age, max_age),
    INDEX idx_income (max_income)
);
```

### 3. Insurance Policies Table

```sql
CREATE TABLE IF NOT EXISTS Insurance_SIP_insurancepolicy (
    id CHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    policy_type VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    short_description VARCHAR(300) NOT NULL,
    premium_per_month DECIMAL(10, 2) NOT NULL,
    coverage_amount DECIMAL(12, 2) NOT NULL,
    key_features TEXT NOT NULL,
    cashless_hospitals BOOLEAN DEFAULT TRUE,
    claim_support BOOLEAN DEFAULT TRUE,
    add_ons_available TEXT,
    min_age INT DEFAULT 18,
    max_age INT DEFAULT 65,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_policy_type (policy_type),
    INDEX idx_is_active (is_active),
    INDEX idx_premium (premium_per_month)
);
```

### 4. Applications Table

```sql
CREATE TABLE IF NOT EXISTS Insurance_SIP_application (
    id CHAR(36) PRIMARY KEY,
    application_id VARCHAR(20) UNIQUE NOT NULL,
    user_id INT NOT NULL,
    scheme_id CHAR(36),
    policy_id CHAR(36),
    status VARCHAR(30) DEFAULT 'draft',
    applicant_name VARCHAR(255) NOT NULL,
    applicant_age INT NOT NULL,
    applicant_income DECIMAL(12, 2),
    applicant_state VARCHAR(100) NOT NULL,
    documents_uploaded JSON,
    notes TEXT,
    admin_notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES authentication_customuser(id) ON DELETE CASCADE,
    FOREIGN KEY (scheme_id) REFERENCES Insurance_SIP_governmentscheme(id) ON DELETE SET NULL,
    FOREIGN KEY (policy_id) REFERENCES Insurance_SIP_insurancepolicy(id) ON DELETE SET NULL,
    INDEX idx_user (user_id),
    INDEX idx_status (status),
    INDEX idx_application_id (application_id),
    INDEX idx_created_at (created_at)
);
```

---

## 📊 SAMPLE DATA INSERTION

### Sample Government Schemes

```sql
-- Ayushman Bharat Scheme
INSERT INTO Insurance_SIP_governmentscheme 
(id, name, scheme_type, description, short_description, state, coverage_amount, benefits, required_documents, application_steps, official_website, is_active) 
VALUES
('550e8400-e29b-41d4-a716-446655440001', 'Ayushman Bharat (PM-JAY)', 'health', 
'Ayushman Bharat Pradhan Mantri Jan Arogya Yojana (PM-JAY) is a flagship scheme of Government of India which was launched as recommended by the National Health Policy 2017, to achieve the vision of Universal Health Coverage (UHC).', 
'Free health insurance coverage up to ₹5 lakh per family per year for secondary and tertiary hospitalization.',
NULL, 500000.00,
'• Cashless treatment at empanelled hospitals
• Coverage for 1,393+ procedures
• Pre and post-hospitalization expenses
• No cap on family size
• Coverage across India',
'• Ration Card
• SECC Data
• Aadhaar Card
• Address Proof
• Income Certificate',
'1. Check eligibility on official website
2. Visit nearest Ayushman Mitra
3. Submit required documents
4. Get your Ayushman Card
5. Visit empanelled hospitals',
'https://pmjay.gov.in/', TRUE);

-- Pradhan Mantri Suraksha Bima Yojana
INSERT INTO Insurance_SIP_governmentscheme 
(id, name, scheme_type, description, short_description, state, coverage_amount, benefits, required_documents, application_steps, official_website, is_active) 
VALUES
('550e8400-e29b-41d4-a716-446655440002', 'Pradhan Mantri Suraksha Bima Yojana', 'accident', 
'PMSBY is a one year accident insurance scheme offering coverage for death or disability due to accident. The scheme is renewable on an annual basis.',
'Accident insurance cover of ₹2 lakh at just ₹12 per year premium.',
NULL, 200000.00,
'• Death benefit: ₹2 lakh
• Total permanent disability: ₹2 lakh
• Partial permanent disability: ₹1 lakh
• Annual premium: Only ₹12
• Auto-debit facility',
'• Bank Account
• Aadhaar Card
• Age Proof (18-70 years)
• Consent Form',
'1. Visit your bank branch
2. Fill enrolment form
3. Give auto-debit consent
4. Premium will be deducted annually
5. Get SMS confirmation',
'https://www.india.gov.in/spotlight/pradhan-mantri-suraksha-bima-yojana', TRUE);

-- Atal Pension Yojana
INSERT INTO Insurance_SIP_governmentscheme 
(id, name, scheme_type, description, short_description, state, coverage_amount, benefits, required_documents, application_steps, official_website, is_active) 
VALUES
('550e8400-e29b-41d4-a716-446655440003', 'Atal Pension Yojana', 'pension', 
'APY is a pension scheme for all citizens of India, particularly the poor, the underprivileged and the workers in the unorganised sector.',
'Guaranteed monthly pension starting from ₹1,000 to ₹5,000 after age 60.',
NULL, 60000.00,
'• Guaranteed pension amount
• Government co-contribution
• Nomination facility
• Minimum pension: ₹1,000/month
• Maximum pension: ₹5,000/month',
'• Aadhaar Card
• Bank Account
• Mobile Number
• Age Proof (18-40 years)',
'1. Visit your bank
2. Fill APY registration form
3. Choose pension amount
4. Start monthly contributions
5. Get pension at age 60',
'https://npscra.nsdl.co.in/atal-pension-yojana.php', TRUE);
```

### Sample Eligibility Criteria

```sql
-- Eligibility for Ayushman Bharat
INSERT INTO Insurance_SIP_eligibility 
(id, scheme_id, min_age, max_age, max_income, state, gender, additional_criteria)
VALUES
('650e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440001', 
0, 100, 500000, NULL, NULL, 'Must be from economically weaker sections as per SECC 2011 data');

-- Eligibility for PMSBY
INSERT INTO Insurance_SIP_eligibility 
(id, scheme_id, min_age, max_age, max_income, state, gender, additional_criteria)
VALUES
('650e8400-e29b-41d4-a716-446655440002', '550e8400-e29b-41d4-a716-446655440002', 
18, 70, NULL, NULL, NULL, 'Must have savings bank account. Enrolled through auto-debit facility.');

-- Eligibility for APY
INSERT INTO Insurance_SIP_eligibility 
(id, scheme_id, min_age, max_age, max_income, state, gender, additional_criteria)
VALUES
('650e8400-e29b-41d4-a716-446655440003', '550e8400-e29b-41d4-a716-446655440003', 
18, 40, NULL, NULL, NULL, 'Must have savings bank account. Not covered under any statutory social security scheme.');
```

### Sample Insurance Policies

```sql
-- HealthFirst Plus
INSERT INTO Insurance_SIP_insurancepolicy 
(id, name, policy_type, description, short_description, premium_per_month, coverage_amount, key_features, cashless_hospitals, claim_support, add_ons_available, min_age, max_age, is_active) 
VALUES
('750e8400-e29b-41d4-a716-446655440001', 'HealthFirst Plus', 'health',
'Comprehensive health insurance plan covering hospitalization, pre and post hospitalization expenses, daycare procedures, and ambulance charges.',
'Complete health protection with coverage up to ₹10 lakh and cashless treatment at 10,000+ hospitals.',
599.00, 1000000.00,
'• Cashless treatment at 10,000+ network hospitals
• Coverage for 30 days pre-hospitalization
• 60 days post-hospitalization coverage
• Daycare procedures covered
• Free health checkup every year
• No room rent capping',
TRUE, TRUE, 
'• Critical illness cover
• Personal accident cover
• Maternity cover
• Mental health cover',
18, 65, TRUE);

-- LifeSecure Family Plan
INSERT INTO Insurance_SIP_insurancepolicy 
(id, name, policy_type, description, short_description, premium_per_month, coverage_amount, key_features, cashless_hospitals, claim_support, add_ons_available, min_age, max_age, is_active) 
VALUES
('750e8400-e29b-41d4-a716-446655440002', 'LifeSecure Family Plan', 'family',
'Affordable family health insurance covering parents, spouse, and children with lifetime renewability.',
'Cover entire family with single premium starting at ₹899/month.',
899.00, 1500000.00,
'• Family floater coverage
• Covers parents, spouse, children
• Cashless hospitals across India
• Maternity coverage included
• New born baby covered from day 1
• Unlimited automatic restoration',
TRUE, TRUE,
'• International coverage
• Home healthcare
• Second medical opinion
• Organ donor expenses',
21, 75, TRUE);

-- Senior Care Shield
INSERT INTO Insurance_SIP_insurancepolicy 
(id, name, policy_type, description, short_description, premium_per_month, coverage_amount, key_features, cashless_hospitals, claim_support, add_ons_available, min_age, max_age, is_active) 
VALUES
('750e8400-e29b-41d4-a716-446655440003', 'Senior Care Shield', 'senior',
'Specially designed health insurance for senior citizens with pre-existing disease coverage.',
'Senior citizen plan with coverage up to ₹5 lakh, covering pre-existing diseases.',
1299.00, 500000.00,
'• Pre-existing diseases covered
• No medical tests up to age 70
• Coverage for age-related illnesses
• Domiciliary hospitalization
• AYUSH treatment covered
• Free annual health checkup',
TRUE, TRUE,
'• Alzheimers cover
• Long term care benefit
• Mobility aids
• Home nursing',
60, 80, TRUE);
```

---

## 🔧 ADDITIONAL PERFORMANCE INDEXES

```sql
CREATE INDEX idx_application_dates ON Insurance_SIP_application(created_at, updated_at);
CREATE INDEX idx_scheme_active_type ON Insurance_SIP_governmentscheme(is_active, scheme_type);
CREATE INDEX idx_policy_active_type ON Insurance_SIP_insurancepolicy(is_active, policy_type);
```

---

## ✅ VERIFICATION QUERIES

Run these to verify your data was inserted correctly:

```sql
-- Check schemes
SELECT COUNT(*) as total_schemes FROM Insurance_SIP_governmentscheme;

-- Check policies
SELECT COUNT(*) as total_policies FROM Insurance_SIP_insurancepolicy;

-- Check eligibility
SELECT COUNT(*) as total_eligibility FROM Insurance_SIP_eligibility;

-- View all schemes
SELECT id, name, scheme_type, coverage_amount FROM Insurance_SIP_governmentscheme;

-- View all policies
SELECT id, name, policy_type, premium_per_month, coverage_amount FROM Insurance_SIP_insurancepolicy;
```

---

## 📝 ALTERNATIVE: Use Django Migrations Instead

If you prefer using Django's built-in system:

```bash
python manage.py makemigrations Insurance_SIP
python manage.py migrate
```

Then create sample data through Django admin or Django shell.

---

## 🎉 DONE!

After running these queries:
1. Start your Django server: `python manage.py runserver`
2. Visit: `http://localhost:8000/insurance/`
3. Access admin: `http://localhost:8000/admin/`
