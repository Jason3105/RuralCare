-- SQL Queries for Insurance_SIP Database Tables
-- Run these queries in your database editor to create the required tables

-- =============================================================================
-- TABLE 1: Insurance_SIP_governmentscheme
-- Stores all government insurance schemes
-- =============================================================================
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

-- =============================================================================
-- TABLE 2: Insurance_SIP_eligibility
-- Stores eligibility criteria for each scheme
-- =============================================================================
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

-- =============================================================================
-- TABLE 3: Insurance_SIP_insurancepolicy
-- Stores all insurance policies offered by the platform
-- =============================================================================
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

-- =============================================================================
-- TABLE 4: Insurance_SIP_application
-- Stores all user applications for schemes and policies
-- =============================================================================
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

-- =============================================================================
-- SAMPLE DATA: Government Schemes
-- Insert some sample government schemes for testing
-- =============================================================================
INSERT INTO Insurance_SIP_governmentscheme (id, name, scheme_type, description, short_description, state, coverage_amount, benefits, required_documents, application_steps, official_website, is_active) VALUES
(UUID(), 'Ayushman Bharat (PM-JAY)', 'health', 
'Ayushman Bharat Pradhan Mantri Jan Arogya Yojana (PM-JAY) is a flagship scheme of Government of India which was launched as recommended by the National Health Policy 2017, to achieve the vision of Universal Health Coverage (UHC).', 
'Free health insurance coverage up to ₹5 lakh per family per year for secondary and tertiary hospitalization.',
NULL, 500000.00,
'• Cashless treatment at empanelled hospitals\n• Coverage for 1,393+ procedures\n• Pre and post-hospitalization expenses\n• No cap on family size\n• Coverage across India',
'• Ration Card\n• SECC Data\n• Aadhaar Card\n• Address Proof\n• Income Certificate',
'1. Check eligibility on official website\n2. Visit nearest Ayushman Mitra\n3. Submit required documents\n4. Get your Ayushman Card\n5. Visit empanelled hospitals',
'https://pmjay.gov.in/', TRUE),

(UUID(), 'Pradhan Mantri Suraksha Bima Yojana', 'accident', 
'PMSBY is a one year accident insurance scheme offering coverage for death or disability due to accident. The scheme is renewable on an annual basis.',
'Accident insurance cover of ₹2 lakh at just ₹12 per year premium.',
NULL, 200000.00,
'• Death benefit: ₹2 lakh\n• Total permanent disability: ₹2 lakh\n• Partial permanent disability: ₹1 lakh\n• Annual premium: Only ₹12\n• Auto-debit facility',
'• Bank Account\n• Aadhaar Card\n• Age Proof (18-70 years)\n• Consent Form',
'1. Visit your bank branch\n2. Fill enrolment form\n3. Give auto-debit consent\n4. Premium will be deducted annually\n5. Get SMS confirmation',
'https://www.india.gov.in/spotlight/pradhan-mantri-suraksha-bima-yojana', TRUE),

(UUID(), 'Atal Pension Yojana', 'pension', 
'APY is a pension scheme for all citizens of India, particularly the poor, the underprivileged and the workers in the unorganised sector.',
'Guaranteed monthly pension starting from ₹1,000 to ₹5,000 after age 60.',
NULL, 60000.00,
'• Guaranteed pension amount\n• Government co-contribution\n• Nomination facility\n• Minimum pension: ₹1,000/month\n• Maximum pension: ₹5,000/month',
'• Aadhaar Card\n• Bank Account\n• Mobile Number\n• Age Proof (18-40 years)',
'1. Visit your bank\n2. Fill APY registration form\n3. Choose pension amount\n4. Start monthly contributions\n5. Get pension at age 60',
'https://npscra.nsdl.co.in/atal-pension-yojana.php', TRUE);

-- =============================================================================
-- SAMPLE DATA: Eligibility Criteria
-- Insert eligibility for sample schemes
-- =============================================================================
INSERT INTO Insurance_SIP_eligibility (id, scheme_id, min_age, max_age, max_income, state, gender, additional_criteria)
SELECT UUID(), id, 0, 100, 500000, NULL, NULL, 'Must be from economically weaker sections as per SECC 2011 data'
FROM Insurance_SIP_governmentscheme WHERE name = 'Ayushman Bharat (PM-JAY)' LIMIT 1;

INSERT INTO Insurance_SIP_eligibility (id, scheme_id, min_age, max_age, max_income, state, gender, additional_criteria)
SELECT UUID(), id, 18, 70, NULL, NULL, NULL, 'Must have savings bank account. Enrolled through auto-debit facility.'
FROM Insurance_SIP_governmentscheme WHERE name = 'Pradhan Mantri Suraksha Bima Yojana' LIMIT 1;

INSERT INTO Insurance_SIP_eligibility (id, scheme_id, min_age, max_age, max_income, state, gender, additional_criteria)
SELECT UUID(), id, 18, 40, NULL, NULL, NULL, 'Must have savings bank account. Not covered under any statutory social security scheme.'
FROM Insurance_SIP_governmentscheme WHERE name = 'Atal Pension Yojana' LIMIT 1;

-- =============================================================================
-- SAMPLE DATA: Insurance Policies
-- Insert some sample insurance policies
-- =============================================================================
INSERT INTO Insurance_SIP_insurancepolicy (id, name, policy_type, description, short_description, premium_per_month, coverage_amount, key_features, cashless_hospitals, claim_support, add_ons_available, min_age, max_age, is_active) VALUES
(UUID(), 'HealthFirst Plus', 'health',
'Comprehensive health insurance plan covering hospitalization, pre and post hospitalization expenses, daycare procedures, and ambulance charges.',
'Complete health protection with coverage up to ₹10 lakh and cashless treatment at 10,000+ hospitals.',
599.00, 1000000.00,
'• Cashless treatment at 10,000+ network hospitals\n• Coverage for 30 days pre-hospitalization\n• 60 days post-hospitalization coverage\n• Daycare procedures covered\n• Free health checkup every year\n• No room rent capping',
TRUE, TRUE, 
'• Critical illness cover\n• Personal accident cover\n• Maternity cover\n• Mental health cover',
18, 65, TRUE),

(UUID(), 'LifeSecure Family Plan', 'family',
'Affordable family health insurance covering parents, spouse, and children with lifetime renewability.',
'Cover entire family with single premium starting at ₹899/month.',
899.00, 1500000.00,
'• Family floater coverage\n• Covers parents, spouse, children\n• Cashless hospitals across India\n• Maternity coverage included\n• New born baby covered from day 1\n• Unlimited automatic restoration',
TRUE, TRUE,
'• International coverage\n• Home healthcare\n• Second medical opinion\n• Organ donor expenses',
21, 75, TRUE),

(UUID(), 'Senior Care Shield', 'senior',
'Specially designed health insurance for senior citizens with pre-existing disease coverage.',
'Senior citizen plan with coverage up to ₹5 lakh, covering pre-existing diseases.',
1299.00, 500000.00,
'• Pre-existing diseases covered\n• No medical tests up to age 70\n• Coverage for age-related illnesses\n• Domiciliary hospitalization\n• AYUSH treatment covered\n• Free annual health checkup',
TRUE, TRUE,
'• Alzheimers cover\n• Long term care benefit\n• Mobility aids\n• Home nursing',
60, 80, TRUE);

-- =============================================================================
-- INDEXES for Performance Optimization
-- =============================================================================
CREATE INDEX idx_application_dates ON Insurance_SIP_application(created_at, updated_at);
CREATE INDEX idx_scheme_active_type ON Insurance_SIP_governmentscheme(is_active, scheme_type);
CREATE INDEX idx_policy_active_type ON Insurance_SIP_insurancepolicy(is_active, policy_type);

-- =============================================================================
-- END OF SQL SCRIPT
-- =============================================================================

-- Notes:
-- 1. Make sure to replace UUID() with appropriate UUID generation for your database
-- 2. Adjust data types if using PostgreSQL (use UUID type instead of CHAR(36))
-- 3. For SQLite, use TEXT instead of VARCHAR and remove INDEX statements
-- 4. Ensure authentication_customuser table exists before running Application table creation
