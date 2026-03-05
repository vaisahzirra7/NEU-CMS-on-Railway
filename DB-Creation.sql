-- =============================================================================
-- VanaraUniCare HMS — University Health Center Management System
-- Full MySQL Database Schema
-- Version: 1.0
-- Modules: User Management, Patient Records & EMR, Appointments, Drug & Inventory
-- =============================================================================

CREATE DATABASE IF NOT EXISTS vanara_unicare_hms
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE vanara_unicare_hms;

SET FOREIGN_KEY_CHECKS = 0;

-- =============================================================================
-- SECTION 1: USER MANAGEMENT & ROLE-BASED ACCESS CONTROL
-- =============================================================================

-- ----------------------------------------------------------------------------
-- Modules/Pages registry — every page in the system is registered here
-- This is what the admin sees when configuring role permissions (the checklist)
-- ----------------------------------------------------------------------------
CREATE TABLE system_modules (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(100)    NOT NULL,                   -- e.g. "Patient Records"
    slug            VARCHAR(100)    NOT NULL UNIQUE,            -- e.g. "patient-records"
    description     VARCHAR(255),
    icon            VARCHAR(100),                               -- icon class e.g. "fa-user-injured"
    parent_id       INT UNSIGNED    DEFAULT NULL,               -- for sub-modules
    sort_order      INT UNSIGNED    DEFAULT 0,
    is_active       BOOLEAN         DEFAULT TRUE,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (parent_id) REFERENCES system_modules(id) ON DELETE SET NULL
);

-- ----------------------------------------------------------------------------
-- Roles — created and named by admin (e.g. "Doctor", "QA Team", "Management")
-- ----------------------------------------------------------------------------
CREATE TABLE roles (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(100)    NOT NULL UNIQUE,            -- e.g. "Head Nurse"
    slug            VARCHAR(100)    NOT NULL UNIQUE,            -- e.g. "head-nurse"
    description     TEXT,
    is_system_role  BOOLEAN         DEFAULT FALSE,              -- TRUE = built-in, cannot be deleted
    is_active       BOOLEAN         DEFAULT TRUE,
    created_by      INT UNSIGNED    DEFAULT NULL,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- Role Permissions — the checkbox matrix: role + module + what they can do
-- ----------------------------------------------------------------------------
CREATE TABLE role_permissions (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    role_id         INT UNSIGNED    NOT NULL,
    module_id       INT UNSIGNED    NOT NULL,
    can_view        BOOLEAN         DEFAULT FALSE,
    can_create      BOOLEAN         DEFAULT FALSE,
    can_edit        BOOLEAN         DEFAULT FALSE,
    can_delete      BOOLEAN         DEFAULT FALSE,
    can_export      BOOLEAN         DEFAULT FALSE,             -- export reports, download data
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uq_role_module (role_id, module_id),
    FOREIGN KEY (role_id)   REFERENCES roles(id)          ON DELETE CASCADE,
    FOREIGN KEY (module_id) REFERENCES system_modules(id) ON DELETE CASCADE
);

-- ----------------------------------------------------------------------------
-- Users — all staff accounts (doctors, nurses, pharmacists, admin, ICT etc.)
-- ----------------------------------------------------------------------------
CREATE TABLE users (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    staff_id            VARCHAR(50)     UNIQUE,                 -- university staff ID
    first_name          VARCHAR(100)    NOT NULL,
    last_name           VARCHAR(100)    NOT NULL,
    other_names         VARCHAR(100),
    email               VARCHAR(150)    NOT NULL UNIQUE,
    phone               VARCHAR(20),
    password_hash       VARCHAR(255)    NOT NULL,
    role_id             INT UNSIGNED    NOT NULL,
    department          VARCHAR(150),
    job_title           VARCHAR(150),
    qualification       VARCHAR(255),                           -- e.g. "MBBS, FWACS"
    reg_number          VARCHAR(100),                           -- professional reg number
    profile_photo       VARCHAR(255),                           -- file path
    digital_signature   VARCHAR(255),                           -- file path — used on prescriptions
    gender              ENUM('Male','Female','Other'),
    date_of_birth       DATE,
    date_joined         DATE,
    is_active           BOOLEAN         DEFAULT TRUE,
    is_verified         BOOLEAN         DEFAULT FALSE,
    must_change_password BOOLEAN        DEFAULT TRUE,           -- force password change on first login
    last_login          TIMESTAMP       NULL,
    last_login_ip       VARCHAR(45),
    created_by          INT UNSIGNED    DEFAULT NULL,           -- admin who created this account
    created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (role_id)    REFERENCES roles(id) ON DELETE RESTRICT,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

-- ----------------------------------------------------------------------------
-- User Permission Overrides — per-user exceptions above or below their role
-- e.g. one specific nurse needs inventory access others in her role don't have
-- ----------------------------------------------------------------------------
CREATE TABLE user_permission_overrides (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id         INT UNSIGNED    NOT NULL,
    module_id       INT UNSIGNED    NOT NULL,
    can_view        BOOLEAN         DEFAULT NULL,               -- NULL = inherit from role
    can_create      BOOLEAN         DEFAULT NULL,
    can_edit        BOOLEAN         DEFAULT NULL,
    can_delete      BOOLEAN         DEFAULT NULL,
    can_export      BOOLEAN         DEFAULT NULL,
    reason          TEXT,                                       -- why this override exists
    granted_by      INT UNSIGNED,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uq_user_module (user_id, module_id),
    FOREIGN KEY (user_id)   REFERENCES users(id)          ON DELETE CASCADE,
    FOREIGN KEY (module_id) REFERENCES system_modules(id) ON DELETE CASCADE,
    FOREIGN KEY (granted_by) REFERENCES users(id)         ON DELETE SET NULL
);

-- ----------------------------------------------------------------------------
-- Login / Session Audit Log — every login attempt, success or failure
-- ----------------------------------------------------------------------------
CREATE TABLE login_audit (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id         INT UNSIGNED    DEFAULT NULL,               -- NULL if username not found
    attempted_email VARCHAR(150),
    ip_address      VARCHAR(45)     NOT NULL,
    user_agent      TEXT,
    status          ENUM('success','failed','locked') NOT NULL,
    failure_reason  VARCHAR(255),
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- ----------------------------------------------------------------------------
-- System Audit Trail — every create, edit, delete action across the system
-- ----------------------------------------------------------------------------
CREATE TABLE audit_trail (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id         INT UNSIGNED    NOT NULL,
    action          ENUM('CREATE','UPDATE','DELETE','VIEW','EXPORT','LOGIN','LOGOUT') NOT NULL,
    module          VARCHAR(100)    NOT NULL,                   -- which part of system
    record_id       VARCHAR(50),                                -- ID of affected record
    old_values      JSON,                                       -- what it was before
    new_values      JSON,                                       -- what it became
    ip_address      VARCHAR(45),
    description     TEXT,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT,
    INDEX idx_module_record (module, record_id),
    INDEX idx_user_action   (user_id, action),
    INDEX idx_created_at    (created_at)
);

-- ----------------------------------------------------------------------------
-- Password Reset Tokens
-- ----------------------------------------------------------------------------
CREATE TABLE password_reset_tokens (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id         INT UNSIGNED    NOT NULL,
    token           VARCHAR(255)    NOT NULL UNIQUE,
    expires_at      TIMESTAMP       NOT NULL,
    used            BOOLEAN         DEFAULT FALSE,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);


-- =============================================================================
-- SECTION 2: STUDENT / PATIENT REGISTRY
-- =============================================================================

-- ----------------------------------------------------------------------------
-- Faculties
-- ----------------------------------------------------------------------------
CREATE TABLE faculties (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(200)    NOT NULL,
    code            VARCHAR(20)     UNIQUE,
    is_active       BOOLEAN         DEFAULT TRUE,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- Departments
-- ----------------------------------------------------------------------------
CREATE TABLE departments (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    faculty_id      INT UNSIGNED    NOT NULL,
    name            VARCHAR(200)    NOT NULL,
    code            VARCHAR(20)     UNIQUE,
    is_active       BOOLEAN         DEFAULT TRUE,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (faculty_id) REFERENCES faculties(id) ON DELETE RESTRICT
);

-- ----------------------------------------------------------------------------
-- Patients — students and any other persons registered at the clinic
-- ----------------------------------------------------------------------------
CREATE TABLE patients (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    patient_uid         VARCHAR(20)     NOT NULL UNIQUE,        -- system-generated e.g. UHC-2025-00001
    matric_number       VARCHAR(30)     UNIQUE,                 -- NULL for non-students
    first_name          VARCHAR(100)    NOT NULL,
    last_name           VARCHAR(100)    NOT NULL,
    other_names         VARCHAR(100),
    date_of_birth       DATE            NOT NULL,
    gender              ENUM('Male','Female','Other') NOT NULL,
    blood_group         ENUM('A+','A-','B+','B-','AB+','AB-','O+','O-','Unknown') DEFAULT 'Unknown',
    genotype            ENUM('AA','AS','SS','AC','SC','Unknown') DEFAULT 'Unknown',
    phone               VARCHAR(20),
    email               VARCHAR(150),
    home_address        TEXT,
    state_of_origin     VARCHAR(100),
    nationality         VARCHAR(100)    DEFAULT 'Nigerian',
    religion            VARCHAR(100),
    passport_photo      VARCHAR(255),                           -- file path

    -- Academic info (students only)
    patient_type        ENUM('Student','Staff','Dependent','Walk-in') DEFAULT 'Student',
    department_id       INT UNSIGNED    DEFAULT NULL,
    level               ENUM('100','200','300','400','500','600','PG','Staff','Other') DEFAULT NULL,
    admission_year      YEAR            DEFAULT NULL,
    programme_type      ENUM('Full-time','Part-time','Distance') DEFAULT 'Full-time',

    -- Emergency contact
    emergency_contact_name      VARCHAR(200),
    emergency_contact_phone     VARCHAR(20),
    emergency_contact_relation  VARCHAR(100),

    -- Health insurance
    has_insurance       BOOLEAN         DEFAULT FALSE,
    insurance_provider  VARCHAR(200),
    insurance_number    VARCHAR(100),

    -- Status
    is_active           BOOLEAN         DEFAULT TRUE,
    registered_by       INT UNSIGNED,                           -- staff who registered
    created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL,
    FOREIGN KEY (registered_by) REFERENCES users(id)       ON DELETE SET NULL,
    INDEX idx_matric      (matric_number),
    INDEX idx_patient_uid (patient_uid)
);

-- ----------------------------------------------------------------------------
-- Medical History — declared conditions and known history
-- ----------------------------------------------------------------------------
CREATE TABLE patient_medical_history (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    patient_id          INT UNSIGNED    NOT NULL,
    has_chronic_illness BOOLEAN         DEFAULT FALSE,
    chronic_illnesses   TEXT,                                   -- comma or JSON list
    has_disability      BOOLEAN         DEFAULT FALSE,
    disability_details  TEXT,
    past_surgeries      TEXT,
    family_history      TEXT,
    immunization_history TEXT,
    current_medications TEXT,                                   -- medications taken before registration
    additional_notes    TEXT,
    declared_by         INT UNSIGNED,                           -- staff or self (student portal)
    created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (patient_id)  REFERENCES patients(id) ON DELETE CASCADE,
    FOREIGN KEY (declared_by) REFERENCES users(id)    ON DELETE SET NULL
);

-- ----------------------------------------------------------------------------
-- Allergies — separate table so we can alert on specific allergens
-- ----------------------------------------------------------------------------
CREATE TABLE patient_allergies (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    patient_id      INT UNSIGNED    NOT NULL,
    allergen        VARCHAR(200)    NOT NULL,                   -- drug name, food, substance
    allergen_type   ENUM('Drug','Food','Environmental','Other') DEFAULT 'Drug',
    reaction        TEXT,                                       -- description of allergic reaction
    severity        ENUM('Mild','Moderate','Severe','Life-threatening') DEFAULT 'Moderate',
    noted_by        INT UNSIGNED,
    noted_at        TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
    FOREIGN KEY (noted_by)   REFERENCES users(id)    ON DELETE SET NULL
);

-- ----------------------------------------------------------------------------
-- Vital Signs — recorded at each visit or during admission
-- ----------------------------------------------------------------------------
CREATE TABLE patient_vitals (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    patient_id          INT UNSIGNED    NOT NULL,
    visit_id            INT UNSIGNED    DEFAULT NULL,           -- linked to a consultation
    temperature         DECIMAL(4,1),                           -- °C
    blood_pressure_sys  INT,                                    -- systolic mmHg
    blood_pressure_dia  INT,                                    -- diastolic mmHg
    pulse_rate          INT,                                    -- beats per minute
    respiratory_rate    INT,                                    -- breaths per minute
    oxygen_saturation   DECIMAL(4,1),                           -- SpO2 %
    weight              DECIMAL(5,2),                           -- kg
    height              DECIMAL(5,2),                           -- cm
    bmi                 DECIMAL(4,2),                           -- auto-calculated
    blood_glucose       DECIMAL(5,1),                           -- mg/dL
    recorded_by         INT UNSIGNED    NOT NULL,
    recorded_at         TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (patient_id)  REFERENCES patients(id) ON DELETE CASCADE,
    FOREIGN KEY (recorded_by) REFERENCES users(id)    ON DELETE RESTRICT
);

-- ----------------------------------------------------------------------------
-- Medical Clearance — 100L registration clearance workflow
-- ----------------------------------------------------------------------------
CREATE TABLE medical_clearance (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    patient_id          INT UNSIGNED    NOT NULL UNIQUE,        -- one clearance per student
    academic_session    VARCHAR(20)     NOT NULL,               -- e.g. "2025/2026"
    submission_date     DATE            NOT NULL,
    status              ENUM('Pending','Under Review','Approved','Rejected','Referred') DEFAULT 'Pending',
    reviewed_by         INT UNSIGNED    DEFAULT NULL,
    review_date         DATE,
    review_notes        TEXT,
    clearance_cert_path VARCHAR(255),                           -- generated certificate file
    cleared_at          TIMESTAMP       NULL,
    created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (patient_id)  REFERENCES patients(id) ON DELETE CASCADE,
    FOREIGN KEY (reviewed_by) REFERENCES users(id)    ON DELETE SET NULL
);

-- ----------------------------------------------------------------------------
-- Clearance Documents — uploaded by student during registration
-- ----------------------------------------------------------------------------
CREATE TABLE clearance_documents (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    clearance_id    INT UNSIGNED    NOT NULL,
    document_type   VARCHAR(100)    NOT NULL,                   -- e.g. "Birth Certificate", "WAEC Result"
    file_path       VARCHAR(255)    NOT NULL,
    uploaded_at     TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (clearance_id) REFERENCES medical_clearance(id) ON DELETE CASCADE
);


-- =============================================================================
-- SECTION 3: CONSULTATIONS & CLINICAL RECORDS (EMR)
-- =============================================================================

-- ----------------------------------------------------------------------------
-- ICD-10 Diagnosis Codes — reference table for standardised diagnoses
-- ----------------------------------------------------------------------------
CREATE TABLE diagnosis_codes (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    code        VARCHAR(20)     NOT NULL UNIQUE,                -- e.g. "J06.9"
    description VARCHAR(500)    NOT NULL,                       -- e.g. "Acute upper respiratory infection"
    category    VARCHAR(200),
    is_active   BOOLEAN         DEFAULT TRUE
);

-- ----------------------------------------------------------------------------
-- Visits / Consultations — the core clinical event
-- ----------------------------------------------------------------------------
CREATE TABLE visits (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    visit_uid           VARCHAR(30)     NOT NULL UNIQUE,        -- e.g. VIS-2025-00001
    patient_id          INT UNSIGNED    NOT NULL,
    appointment_id      INT UNSIGNED    DEFAULT NULL,           -- linked if booked
    visit_type          ENUM('Walk-in','Appointment','Emergency','Follow-up','Referral') DEFAULT 'Walk-in',
    visit_date          DATE            NOT NULL,
    check_in_time       TIME,
    check_out_time      TIME,

    -- Triage
    triage_level        ENUM('Emergency','Urgent','Semi-urgent','Routine') DEFAULT 'Routine',
    chief_complaint     TEXT            NOT NULL,               -- reason for visit

    -- Consultation
    attending_doctor    INT UNSIGNED    DEFAULT NULL,
    attending_nurse     INT UNSIGNED    DEFAULT NULL,
    history_of_illness  TEXT,
    examination_findings TEXT,
    working_diagnosis   TEXT,                                   -- free text initial diagnosis
    doctor_notes        TEXT,
    nurse_notes         TEXT,

    -- Outcome
    status              ENUM('Waiting','With Nurse','With Doctor','Completed','Referred','Admitted','No-show') DEFAULT 'Waiting',
    outcome             ENUM('Treated & Discharged','Admitted','Referred Externally','Referred Internally','Follow-up Scheduled','Deceased') DEFAULT NULL,
    referral_destination VARCHAR(255),
    follow_up_date      DATE,

    created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (patient_id)       REFERENCES patients(id) ON DELETE RESTRICT,
    FOREIGN KEY (attending_doctor) REFERENCES users(id)    ON DELETE SET NULL,
    FOREIGN KEY (attending_nurse)  REFERENCES users(id)    ON DELETE SET NULL,
    INDEX idx_patient_visit (patient_id, visit_date),
    INDEX idx_visit_date    (visit_date)
);

-- ----------------------------------------------------------------------------
-- Visit Diagnoses — one visit can have multiple diagnoses
-- ----------------------------------------------------------------------------
CREATE TABLE visit_diagnoses (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    visit_id        INT UNSIGNED    NOT NULL,
    diagnosis_code_id INT UNSIGNED  DEFAULT NULL,               -- ICD-10 if available
    diagnosis_text  TEXT            NOT NULL,                   -- free text always allowed
    diagnosis_type  ENUM('Primary','Secondary','Differential') DEFAULT 'Primary',
    noted_by        INT UNSIGNED    NOT NULL,
    noted_at        TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (visit_id)          REFERENCES visits(id)          ON DELETE CASCADE,
    FOREIGN KEY (diagnosis_code_id) REFERENCES diagnosis_codes(id) ON DELETE SET NULL,
    FOREIGN KEY (noted_by)          REFERENCES users(id)           ON DELETE RESTRICT
);

-- ----------------------------------------------------------------------------
-- Referral Letters — formal referrals generated for external/internal use
-- ----------------------------------------------------------------------------
CREATE TABLE referral_letters (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    referral_uid        VARCHAR(30)     NOT NULL UNIQUE,        -- e.g. REF-2025-00001
    visit_id            INT UNSIGNED    NOT NULL,
    patient_id          INT UNSIGNED    NOT NULL,
    referred_by         INT UNSIGNED    NOT NULL,
    referral_type       ENUM('External','Internal') DEFAULT 'External',
    destination         VARCHAR(255)    NOT NULL,               -- hospital or department name
    destination_doctor  VARCHAR(255),
    reason              TEXT            NOT NULL,
    clinical_summary    TEXT,
    urgency             ENUM('Routine','Urgent','Emergency') DEFAULT 'Routine',
    document_path       VARCHAR(255),
    outcome_received    BOOLEAN         DEFAULT FALSE,
    outcome_notes       TEXT,
    outcome_date        DATE,
    created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (visit_id)    REFERENCES visits(id)   ON DELETE RESTRICT,
    FOREIGN KEY (patient_id)  REFERENCES patients(id) ON DELETE RESTRICT,
    FOREIGN KEY (referred_by) REFERENCES users(id)    ON DELETE RESTRICT
);


-- =============================================================================
-- SECTION 4: APPOINTMENTS
-- =============================================================================

-- ----------------------------------------------------------------------------
-- Doctor / Staff Availability — when each staff member is available
-- ----------------------------------------------------------------------------
CREATE TABLE staff_availability (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id         INT UNSIGNED    NOT NULL,
    day_of_week     TINYINT         NOT NULL,                   -- 0=Sunday, 6=Saturday
    start_time      TIME            NOT NULL,
    end_time        TIME            NOT NULL,
    slot_duration   INT             DEFAULT 20,                 -- minutes per appointment
    max_patients    INT             DEFAULT 20,                 -- max patients per session
    is_active       BOOLEAN         DEFAULT TRUE,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ----------------------------------------------------------------------------
-- Blocked Dates — when a doctor/nurse is unavailable (leave, meetings etc.)
-- ----------------------------------------------------------------------------
CREATE TABLE blocked_dates (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id         INT UNSIGNED    NOT NULL,
    blocked_date    DATE            NOT NULL,
    reason          VARCHAR(255),
    all_day         BOOLEAN         DEFAULT TRUE,
    start_time      TIME            DEFAULT NULL,
    end_time        TIME            DEFAULT NULL,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_date (user_id, blocked_date)
);

-- ----------------------------------------------------------------------------
-- Appointments
-- ----------------------------------------------------------------------------
CREATE TABLE appointments (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    appointment_uid     VARCHAR(30)     NOT NULL UNIQUE,        -- e.g. APT-2025-00001
    patient_id          INT UNSIGNED    NOT NULL,
    doctor_id           INT UNSIGNED    DEFAULT NULL,
    appointment_date    DATE            NOT NULL,
    appointment_time    TIME            NOT NULL,
    duration_minutes    INT             DEFAULT 20,
    appointment_type    ENUM('General','Follow-up','Specialist','Emergency','Teleconsultation') DEFAULT 'General',
    priority            ENUM('Routine','Urgent','Emergency') DEFAULT 'Routine',
    reason              TEXT,                                   -- patient's stated reason
    status              ENUM('Booked','Confirmed','Checked-in','In-progress','Completed','Cancelled','No-show','Rescheduled') DEFAULT 'Booked',

    -- Booking info
    booked_by           INT UNSIGNED    DEFAULT NULL,           -- staff or NULL if self-booked
    booked_via          ENUM('Portal','Staff','Walk-in') DEFAULT 'Portal',
    booked_at           TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,

    -- Cancellation
    cancelled_by        INT UNSIGNED    DEFAULT NULL,
    cancellation_reason TEXT,
    cancelled_at        TIMESTAMP       NULL,

    -- Rescheduling
    rescheduled_from    INT UNSIGNED    DEFAULT NULL,           -- original appointment ID
    reschedule_reason   TEXT,

    -- Reminders
    reminder_sent_24h   BOOLEAN         DEFAULT FALSE,
    reminder_sent_1h    BOOLEAN         DEFAULT FALSE,

    -- Visit link
    visit_id            INT UNSIGNED    DEFAULT NULL,

    notes               TEXT,
    created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (patient_id)       REFERENCES patients(id)     ON DELETE RESTRICT,
    FOREIGN KEY (doctor_id)        REFERENCES users(id)        ON DELETE SET NULL,
    FOREIGN KEY (booked_by)        REFERENCES users(id)        ON DELETE SET NULL,
    FOREIGN KEY (cancelled_by)     REFERENCES users(id)        ON DELETE SET NULL,
    FOREIGN KEY (rescheduled_from) REFERENCES appointments(id) ON DELETE SET NULL,
    FOREIGN KEY (visit_id)         REFERENCES visits(id)       ON DELETE SET NULL,
    INDEX idx_apt_date_doctor (appointment_date, doctor_id),
    INDEX idx_apt_patient     (patient_id)
);

-- ----------------------------------------------------------------------------
-- Appointment Reminders Log — track what reminders were sent and when
-- ----------------------------------------------------------------------------
CREATE TABLE appointment_reminders (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    appointment_id  INT UNSIGNED    NOT NULL,
    reminder_type   ENUM('24h','1h','custom') NOT NULL,
    channel         ENUM('email','sms','both') DEFAULT 'email',
    sent_at         TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    status          ENUM('sent','failed') DEFAULT 'sent',
    error_message   TEXT,

    FOREIGN KEY (appointment_id) REFERENCES appointments(id) ON DELETE CASCADE
);


-- =============================================================================
-- SECTION 5: BED & WARD MANAGEMENT
-- =============================================================================

-- ----------------------------------------------------------------------------
-- Wards
-- ----------------------------------------------------------------------------
CREATE TABLE wards (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(100)    NOT NULL,                   -- e.g. "Male Ward", "Female Ward"
    code            VARCHAR(20)     UNIQUE,
    ward_type       ENUM('General','Male','Female','Paediatric','Isolation','Observation','Emergency','ICU') DEFAULT 'General',
    capacity        INT             NOT NULL DEFAULT 0,
    description     TEXT,
    is_active       BOOLEAN         DEFAULT TRUE,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- Beds
-- ----------------------------------------------------------------------------
CREATE TABLE beds (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    ward_id         INT UNSIGNED    NOT NULL,
    bed_number      VARCHAR(20)     NOT NULL,                   -- e.g. "M-01", "F-05"
    bed_type        ENUM('Standard','ICU','Isolation','Paediatric') DEFAULT 'Standard',
    status          ENUM('Vacant','Occupied','Reserved','Maintenance') DEFAULT 'Vacant',
    notes           TEXT,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uq_ward_bed (ward_id, bed_number),
    FOREIGN KEY (ward_id) REFERENCES wards(id) ON DELETE RESTRICT
);

-- ----------------------------------------------------------------------------
-- Admissions — when a patient is formally admitted to a ward/bed
-- ----------------------------------------------------------------------------
CREATE TABLE admissions (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    admission_uid       VARCHAR(30)     NOT NULL UNIQUE,        -- e.g. ADM-2025-00001
    patient_id          INT UNSIGNED    NOT NULL,
    visit_id            INT UNSIGNED    DEFAULT NULL,
    ward_id             INT UNSIGNED    NOT NULL,
    bed_id              INT UNSIGNED    NOT NULL,
    admitting_doctor    INT UNSIGNED    NOT NULL,
    admitting_nurse     INT UNSIGNED    DEFAULT NULL,
    admission_date      DATE            NOT NULL,
    admission_time      TIME            NOT NULL,
    admission_reason    TEXT            NOT NULL,
    admission_diagnosis TEXT,
    expected_stay_days  INT             DEFAULT NULL,
    status              ENUM('Admitted','Discharged','Transferred','Absconded','Deceased') DEFAULT 'Admitted',

    -- Discharge
    discharge_date      DATE            DEFAULT NULL,
    discharge_time      TIME            DEFAULT NULL,
    discharged_by       INT UNSIGNED    DEFAULT NULL,
    discharge_notes     TEXT,
    discharge_condition ENUM('Improved','Stable','Referred','Deceased','Absconded') DEFAULT NULL,

    created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (patient_id)       REFERENCES patients(id) ON DELETE RESTRICT,
    FOREIGN KEY (visit_id)         REFERENCES visits(id)   ON DELETE SET NULL,
    FOREIGN KEY (ward_id)          REFERENCES wards(id)    ON DELETE RESTRICT,
    FOREIGN KEY (bed_id)           REFERENCES beds(id)     ON DELETE RESTRICT,
    FOREIGN KEY (admitting_doctor) REFERENCES users(id)    ON DELETE RESTRICT,
    FOREIGN KEY (admitting_nurse)  REFERENCES users(id)    ON DELETE SET NULL,
    FOREIGN KEY (discharged_by)    REFERENCES users(id)    ON DELETE SET NULL,
    INDEX idx_admission_status (status),
    INDEX idx_admission_patient (patient_id)
);

-- ----------------------------------------------------------------------------
-- Admission Condition Logs — nurses log patient condition updates during stay
-- ----------------------------------------------------------------------------
CREATE TABLE admission_condition_logs (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    admission_id    INT UNSIGNED    NOT NULL,
    condition_note  TEXT            NOT NULL,
    condition_level ENUM('Stable','Fair','Serious','Critical','Improved','Deteriorating') DEFAULT 'Stable',
    logged_by       INT UNSIGNED    NOT NULL,
    logged_at       TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (admission_id) REFERENCES admissions(id) ON DELETE CASCADE,
    FOREIGN KEY (logged_by)    REFERENCES users(id)      ON DELETE RESTRICT
);

-- ----------------------------------------------------------------------------
-- Visitor Log — optional, for contact tracing and security
-- ----------------------------------------------------------------------------
CREATE TABLE visitor_log (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    admission_id    INT UNSIGNED    NOT NULL,
    visitor_name    VARCHAR(200)    NOT NULL,
    visitor_phone   VARCHAR(20),
    relationship    VARCHAR(100),
    visit_date      DATE            NOT NULL,
    time_in         TIME,
    time_out        TIME,
    logged_by       INT UNSIGNED,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (admission_id) REFERENCES admissions(id) ON DELETE CASCADE,
    FOREIGN KEY (logged_by)    REFERENCES users(id)      ON DELETE SET NULL
);


-- =============================================================================
-- SECTION 6: DRUG & INVENTORY MANAGEMENT
-- =============================================================================

-- ----------------------------------------------------------------------------
-- Drug Categories
-- ----------------------------------------------------------------------------
CREATE TABLE drug_categories (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(100)    NOT NULL UNIQUE,            -- e.g. "Antibiotics", "Analgesics"
    description     TEXT,
    is_active       BOOLEAN         DEFAULT TRUE,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- Drugs Master List — all drugs that can be stocked and prescribed
-- ----------------------------------------------------------------------------
CREATE TABLE drugs (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    drug_uid            VARCHAR(20)     NOT NULL UNIQUE,        -- e.g. DRG-00001
    name                VARCHAR(200)    NOT NULL,               -- generic name
    brand_name          VARCHAR(200),
    category_id         INT UNSIGNED    DEFAULT NULL,
    drug_form           ENUM('Tablet','Capsule','Syrup','Injection','Cream','Ointment','Drops','Inhaler','Suppository','Powder','Solution','Other') DEFAULT 'Tablet',
    strength            VARCHAR(100),                           -- e.g. "500mg", "250mg/5ml"
    unit_of_measure     VARCHAR(50)     NOT NULL,               -- e.g. "Tablet", "Bottle", "Vial"
    is_controlled       BOOLEAN         DEFAULT FALSE,           -- controlled substance
    requires_prescription BOOLEAN       DEFAULT TRUE,
    storage_conditions  VARCHAR(255),                           -- e.g. "Store below 25°C"
    description         TEXT,
    contraindications   TEXT,
    side_effects        TEXT,
    reorder_level       INT             DEFAULT 50,             -- alert when stock drops below this
    is_active           BOOLEAN         DEFAULT TRUE,
    added_by            INT UNSIGNED,
    created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (category_id) REFERENCES drug_categories(id) ON DELETE SET NULL,
    FOREIGN KEY (added_by)    REFERENCES users(id)           ON DELETE SET NULL,
    INDEX idx_drug_name (name)
);

-- ----------------------------------------------------------------------------
-- Suppliers
-- ----------------------------------------------------------------------------
CREATE TABLE suppliers (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(200)    NOT NULL,
    contact_person  VARCHAR(200),
    phone           VARCHAR(20),
    email           VARCHAR(150),
    address         TEXT,
    registration_number VARCHAR(100),
    is_active       BOOLEAN         DEFAULT TRUE,
    notes           TEXT,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- Drug Batches / Stock — every supply delivery creates a new batch
-- ----------------------------------------------------------------------------
CREATE TABLE drug_batches (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    batch_uid           VARCHAR(30)     NOT NULL UNIQUE,        -- e.g. BAT-2025-00001
    drug_id             INT UNSIGNED    NOT NULL,
    supplier_id         INT UNSIGNED    DEFAULT NULL,
    batch_number        VARCHAR(100),                           -- supplier's batch/lot number
    manufacture_date    DATE,
    expiry_date         DATE            NOT NULL,
    quantity_received   INT             NOT NULL,
    quantity_remaining  INT             NOT NULL,
    unit_cost           DECIMAL(10,2)   DEFAULT NULL,
    total_cost          DECIMAL(10,2)   DEFAULT NULL,
    currency            VARCHAR(10)     DEFAULT 'NGN',
    received_date       DATE            NOT NULL,
    received_by         INT UNSIGNED    NOT NULL,               -- staff who logged the delivery
    delivery_staff      VARCHAR(200),                           -- person who brought the drugs to clinic
    purchase_order_ref  VARCHAR(100),
    invoice_number      VARCHAR(100),
    storage_location    VARCHAR(100),                           -- e.g. "Shelf A3", "Fridge 2"
    expiry_alert_sent   BOOLEAN         DEFAULT FALSE,
    is_active           BOOLEAN         DEFAULT TRUE,
    notes               TEXT,
    created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (drug_id)     REFERENCES drugs(id)     ON DELETE RESTRICT,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE SET NULL,
    FOREIGN KEY (received_by) REFERENCES users(id)     ON DELETE RESTRICT,
    INDEX idx_drug_expiry    (drug_id, expiry_date),
    INDEX idx_expiry_date    (expiry_date),
    INDEX idx_batch_active   (is_active, quantity_remaining)
);

-- ----------------------------------------------------------------------------
-- Drug Stock Summary — live view of total stock per drug (updated by triggers)
-- ----------------------------------------------------------------------------
CREATE TABLE drug_stock (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    drug_id             INT UNSIGNED    NOT NULL UNIQUE,
    total_quantity      INT             NOT NULL DEFAULT 0,
    reserved_quantity   INT             NOT NULL DEFAULT 0,     -- allocated but not dispensed
    available_quantity  INT GENERATED ALWAYS AS (total_quantity - reserved_quantity) STORED,
    last_restocked      TIMESTAMP       NULL,
    last_dispensed      TIMESTAMP       NULL,
    updated_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (drug_id) REFERENCES drugs(id) ON DELETE CASCADE
);

-- ----------------------------------------------------------------------------
-- Equipment Inventory
-- ----------------------------------------------------------------------------
CREATE TABLE equipment (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    equipment_uid       VARCHAR(20)     NOT NULL UNIQUE,
    name                VARCHAR(200)    NOT NULL,
    category            VARCHAR(100),
    serial_number       VARCHAR(100)    UNIQUE,
    model               VARCHAR(100),
    manufacturer        VARCHAR(200),
    purchase_date       DATE,
    purchase_cost       DECIMAL(10,2),
    location            VARCHAR(100),                           -- where it's kept
    equipment_condition ENUM('Excellent','Good','Fair','Poor','Out of Service') DEFAULT 'Good',
    status              ENUM('Available','In Use','Under Maintenance','Disposed') DEFAULT 'Available',
    last_maintenance    DATE,
    next_maintenance    DATE,
    maintenance_notes   TEXT,
    assigned_to         INT UNSIGNED    DEFAULT NULL,
    notes               TEXT,
    added_by            INT UNSIGNED,
    created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (added_by)    REFERENCES users(id) ON DELETE SET NULL
);

-- ----------------------------------------------------------------------------
-- Consumables Inventory (gloves, syringes, bandages etc.)
-- ----------------------------------------------------------------------------
CREATE TABLE consumables (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(200)    NOT NULL,
    category        VARCHAR(100),
    unit            VARCHAR(50)     NOT NULL,                   -- e.g. "Box", "Piece", "Pack"
    quantity        INT             NOT NULL DEFAULT 0,
    reorder_level   INT             DEFAULT 20,
    last_restocked  TIMESTAMP       NULL,
    notes           TEXT,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- Consumable Restock Log
-- ----------------------------------------------------------------------------
CREATE TABLE consumable_restock_log (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    consumable_id   INT UNSIGNED    NOT NULL,
    quantity_added  INT             NOT NULL,
    restocked_by    INT UNSIGNED    NOT NULL,
    supplier_id     INT UNSIGNED    DEFAULT NULL,
    restocked_at    TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    notes           TEXT,

    FOREIGN KEY (consumable_id) REFERENCES consumables(id)  ON DELETE CASCADE,
    FOREIGN KEY (restocked_by)  REFERENCES users(id)        ON DELETE RESTRICT,
    FOREIGN KEY (supplier_id)   REFERENCES suppliers(id)    ON DELETE SET NULL
);


-- =============================================================================
-- SECTION 7: PRESCRIPTIONS
-- =============================================================================

-- ----------------------------------------------------------------------------
-- Prescriptions — digital prescription documents
-- ----------------------------------------------------------------------------
CREATE TABLE prescriptions (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    prescription_uid    VARCHAR(30)     NOT NULL UNIQUE,        -- e.g. UHCMS-2025-00001
    visit_id            INT UNSIGNED    NOT NULL,
    patient_id          INT UNSIGNED    NOT NULL,
    prescribed_by       INT UNSIGNED    NOT NULL,               -- doctor
    prescription_date   DATE            NOT NULL,
    valid_until         DATE            NOT NULL,               -- expiry date of prescription
    status              ENUM('Active','Partially Dispensed','Fully Dispensed','Expired','Cancelled') DEFAULT 'Active',
    general_notes       TEXT,                                   -- doctor's overall notes
    document_path       VARCHAR(255),                           -- generated PDF path
    qr_code_path        VARCHAR(255),                           -- QR verification code
    created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (visit_id)      REFERENCES visits(id)   ON DELETE RESTRICT,
    FOREIGN KEY (patient_id)    REFERENCES patients(id) ON DELETE RESTRICT,
    FOREIGN KEY (prescribed_by) REFERENCES users(id)    ON DELETE RESTRICT,
    INDEX idx_prescription_patient (patient_id),
    INDEX idx_prescription_status  (status)
);

-- ----------------------------------------------------------------------------
-- Prescription Items — each drug on a prescription
-- ----------------------------------------------------------------------------
CREATE TABLE prescription_items (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    prescription_id     INT UNSIGNED    NOT NULL,
    drug_id             INT UNSIGNED    DEFAULT NULL,           -- NULL for custom prescriptions
    drug_name           VARCHAR(200)    NOT NULL,               -- always stored as text too
    is_custom           BOOLEAN         DEFAULT FALSE,          -- TRUE if drug not in system
    dosage              VARCHAR(200)    NOT NULL,               -- e.g. "500mg"
    frequency           VARCHAR(200)    NOT NULL,               -- e.g. "Twice daily", "Every 8 hours"
    duration            VARCHAR(200),                           -- e.g. "7 days", "2 weeks"
    quantity_prescribed INT             NOT NULL,
    route               VARCHAR(100)    DEFAULT 'Oral',         -- e.g. Oral, IV, Topical, IM
    special_instructions TEXT,
    doctor_comment      TEXT,                                   -- especially for custom items
    dispensing_location ENUM('In-clinic','External','Pending') DEFAULT 'Pending',

    -- Dispensing tracking
    quantity_dispensed  INT             DEFAULT 0,
    dispensed_by        INT UNSIGNED    DEFAULT NULL,
    dispensed_at        TIMESTAMP       NULL,
    batch_id            INT UNSIGNED    DEFAULT NULL,           -- which batch was used
    dispensing_notes    TEXT,

    created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (prescription_id) REFERENCES prescriptions(id)  ON DELETE CASCADE,
    FOREIGN KEY (drug_id)         REFERENCES drugs(id)          ON DELETE SET NULL,
    FOREIGN KEY (dispensed_by)    REFERENCES users(id)          ON DELETE SET NULL,
    FOREIGN KEY (batch_id)        REFERENCES drug_batches(id)   ON DELETE SET NULL
);

-- ----------------------------------------------------------------------------
-- Dispensing Log — detailed record of every drug dispensed
-- This gives management full accountability of every drug that leaves the shelf
-- ----------------------------------------------------------------------------
CREATE TABLE dispensing_log (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    prescription_item_id INT UNSIGNED   NOT NULL,
    drug_id             INT UNSIGNED    NOT NULL,
    batch_id            INT UNSIGNED    NOT NULL,
    patient_id          INT UNSIGNED    NOT NULL,
    quantity_dispensed  INT             NOT NULL,
    dispensed_by        INT UNSIGNED    NOT NULL,
    dispensed_at        TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    notes               TEXT,

    FOREIGN KEY (prescription_item_id) REFERENCES prescription_items(id) ON DELETE RESTRICT,
    FOREIGN KEY (drug_id)              REFERENCES drugs(id)               ON DELETE RESTRICT,
    FOREIGN KEY (batch_id)             REFERENCES drug_batches(id)        ON DELETE RESTRICT,
    FOREIGN KEY (patient_id)           REFERENCES patients(id)            ON DELETE RESTRICT,
    FOREIGN KEY (dispensed_by)         REFERENCES users(id)               ON DELETE RESTRICT,
    INDEX idx_dispensing_drug    (drug_id, dispensed_at),
    INDEX idx_dispensing_patient (patient_id)
);

-- ----------------------------------------------------------------------------
-- Drug Returns — when a patient returns unused medication
-- ----------------------------------------------------------------------------
CREATE TABLE drug_returns (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    prescription_item_id INT UNSIGNED  NOT NULL,
    drug_id         INT UNSIGNED    NOT NULL,
    batch_id        INT UNSIGNED    NOT NULL,
    patient_id      INT UNSIGNED    NOT NULL,
    quantity_returned INT           NOT NULL,
    reason          TEXT,
    return_to_stock BOOLEAN         DEFAULT TRUE,
    processed_by    INT UNSIGNED    NOT NULL,
    returned_at     TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (prescription_item_id) REFERENCES prescription_items(id) ON DELETE RESTRICT,
    FOREIGN KEY (drug_id)              REFERENCES drugs(id)               ON DELETE RESTRICT,
    FOREIGN KEY (batch_id)             REFERENCES drug_batches(id)        ON DELETE RESTRICT,
    FOREIGN KEY (patient_id)           REFERENCES patients(id)            ON DELETE RESTRICT,
    FOREIGN KEY (processed_by)         REFERENCES users(id)               ON DELETE RESTRICT
);


-- =============================================================================
-- SECTION 8: LABORATORY
-- =============================================================================

-- ----------------------------------------------------------------------------
-- Lab Test Types
-- ----------------------------------------------------------------------------
CREATE TABLE lab_test_types (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(200)    NOT NULL,                   -- e.g. "Full Blood Count"
    code            VARCHAR(50)     UNIQUE,
    category        VARCHAR(100),                               -- e.g. "Haematology", "Microbiology"
    normal_range    TEXT,
    turnaround_days INT             DEFAULT 1,
    is_active       BOOLEAN         DEFAULT TRUE,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- Lab Requests
-- ----------------------------------------------------------------------------
CREATE TABLE lab_requests (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    request_uid     VARCHAR(30)     NOT NULL UNIQUE,            -- e.g. LAB-2025-00001
    visit_id        INT UNSIGNED    NOT NULL,
    patient_id      INT UNSIGNED    NOT NULL,
    requested_by    INT UNSIGNED    NOT NULL,
    request_date    DATE            NOT NULL,
    urgency         ENUM('Routine','Urgent','Emergency') DEFAULT 'Routine',
    lab_location    ENUM('In-clinic','External') DEFAULT 'In-clinic',
    external_lab    VARCHAR(200),
    status          ENUM('Requested','Sample Collected','Processing','Completed','Cancelled') DEFAULT 'Requested',
    clinical_notes  TEXT,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (visit_id)     REFERENCES visits(id)   ON DELETE RESTRICT,
    FOREIGN KEY (patient_id)   REFERENCES patients(id) ON DELETE RESTRICT,
    FOREIGN KEY (requested_by) REFERENCES users(id)    ON DELETE RESTRICT
);

-- ----------------------------------------------------------------------------
-- Lab Request Items — each test on a request
-- ----------------------------------------------------------------------------
CREATE TABLE lab_request_items (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    request_id      INT UNSIGNED    NOT NULL,
    test_type_id    INT UNSIGNED    NOT NULL,
    result_value    TEXT,
    result_unit     VARCHAR(50),
    reference_range VARCHAR(100),
    is_abnormal     BOOLEAN         DEFAULT FALSE,
    result_notes    TEXT,
    result_date     DATE,
    result_file     VARCHAR(255),                               -- uploaded result PDF
    entered_by      INT UNSIGNED    DEFAULT NULL,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (request_id)  REFERENCES lab_requests(id)   ON DELETE CASCADE,
    FOREIGN KEY (test_type_id) REFERENCES lab_test_types(id) ON DELETE RESTRICT,
    FOREIGN KEY (entered_by)  REFERENCES users(id)           ON DELETE SET NULL
);


-- =============================================================================
-- SECTION 9: NOTIFICATIONS & COMMUNICATIONS
-- =============================================================================

-- ----------------------------------------------------------------------------
-- Notifications — system-generated alerts to staff and students
-- ----------------------------------------------------------------------------
CREATE TABLE notifications (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    recipient_type  ENUM('user','patient') NOT NULL,
    recipient_id    INT UNSIGNED    NOT NULL,
    title           VARCHAR(255)    NOT NULL,
    message         TEXT            NOT NULL,
    type            ENUM('appointment','prescription','inventory','expiry','lab','general','alert') DEFAULT 'general',
    channel         ENUM('in-app','email','sms','all') DEFAULT 'in-app',
    related_module  VARCHAR(100),
    related_id      INT UNSIGNED,
    is_read         BOOLEAN         DEFAULT FALSE,
    read_at         TIMESTAMP       NULL,
    sent_at         TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_recipient (recipient_type, recipient_id, is_read)
);

-- ----------------------------------------------------------------------------
-- Internal Messages — staff to staff messaging within the system
-- ----------------------------------------------------------------------------
CREATE TABLE internal_messages (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    sender_id       INT UNSIGNED    NOT NULL,
    recipient_id    INT UNSIGNED    NOT NULL,
    subject         VARCHAR(255),
    body            TEXT            NOT NULL,
    is_read         BOOLEAN         DEFAULT FALSE,
    read_at         TIMESTAMP       NULL,
    sent_at         TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (sender_id)    REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (recipient_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_recipient_unread (recipient_id, is_read)
);


-- =============================================================================
-- SECTION 10: STUDENT PORTAL
-- =============================================================================

-- ----------------------------------------------------------------------------
-- Student Portal Accounts — linked to patient records
-- ----------------------------------------------------------------------------
CREATE TABLE student_accounts (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    patient_id      INT UNSIGNED    NOT NULL UNIQUE,
    matric_number   VARCHAR(30)     NOT NULL UNIQUE,
    email           VARCHAR(150)    NOT NULL UNIQUE,
    password_hash   VARCHAR(255)    NOT NULL,
    is_active       BOOLEAN         DEFAULT TRUE,
    is_verified     BOOLEAN         DEFAULT FALSE,
    email_verified_at TIMESTAMP     NULL,
    last_login      TIMESTAMP       NULL,
    must_change_password BOOLEAN    DEFAULT FALSE,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
);

-- ----------------------------------------------------------------------------
-- Student Portal Verification Tokens
-- ----------------------------------------------------------------------------
CREATE TABLE student_verification_tokens (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    account_id  INT UNSIGNED    NOT NULL,
    token       VARCHAR(255)    NOT NULL UNIQUE,
    type        ENUM('email_verify','password_reset') DEFAULT 'email_verify',
    expires_at  TIMESTAMP       NOT NULL,
    used        BOOLEAN         DEFAULT FALSE,
    created_at  TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (account_id) REFERENCES student_accounts(id) ON DELETE CASCADE
);


-- =============================================================================
-- SECTION 11: OFFICIAL DOCUMENTS
-- =============================================================================

-- ----------------------------------------------------------------------------
-- Generated Documents — all official documents produced by the system
-- ----------------------------------------------------------------------------
CREATE TABLE official_documents (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    document_uid    VARCHAR(30)     NOT NULL UNIQUE,            -- e.g. DOC-2025-00001
    document_type   ENUM('Sick Leave Certificate','Medical Fitness Certificate','Referral Letter','Prescription','Medical Clearance','Other') NOT NULL,
    patient_id      INT UNSIGNED    NOT NULL,
    visit_id        INT UNSIGNED    DEFAULT NULL,
    generated_by    INT UNSIGNED    NOT NULL,
    title           VARCHAR(255)    NOT NULL,
    content         TEXT,
    file_path       VARCHAR(255),
    qr_code_path    VARCHAR(255),
    valid_from      DATE,
    valid_until     DATE,
    is_revoked      BOOLEAN         DEFAULT FALSE,
    revoked_by      INT UNSIGNED    DEFAULT NULL,
    revoked_at      TIMESTAMP       NULL,
    revoke_reason   TEXT,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (patient_id)  REFERENCES patients(id) ON DELETE RESTRICT,
    FOREIGN KEY (visit_id)    REFERENCES visits(id)   ON DELETE SET NULL,
    FOREIGN KEY (generated_by) REFERENCES users(id)   ON DELETE RESTRICT,
    FOREIGN KEY (revoked_by)  REFERENCES users(id)    ON DELETE SET NULL
);


-- =============================================================================
-- SECTION 12: SYSTEM SETTINGS
-- =============================================================================

-- ----------------------------------------------------------------------------
-- System Configuration — key-value settings for the application
-- ----------------------------------------------------------------------------
CREATE TABLE system_settings (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    setting_key     VARCHAR(150)    NOT NULL UNIQUE,
    setting_value   TEXT,
    setting_type    ENUM('string','integer','boolean','json') DEFAULT 'string',
    description     TEXT,
    updated_by      INT UNSIGNED    DEFAULT NULL,
    updated_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL
);

-- ----------------------------------------------------------------------------
-- Academic Sessions
-- ----------------------------------------------------------------------------
CREATE TABLE academic_sessions (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    session_name    VARCHAR(20)     NOT NULL UNIQUE,            -- e.g. "2025/2026"
    start_date      DATE            NOT NULL,
    end_date        DATE            NOT NULL,
    is_current      BOOLEAN         DEFAULT FALSE,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);


-- =============================================================================
-- TRIGGERS — Auto-update drug stock when batches are modified or drugs dispensed
-- =============================================================================

DELIMITER $$

-- When a new batch is received, add to stock summary
CREATE TRIGGER trg_batch_insert_stock
AFTER INSERT ON drug_batches
FOR EACH ROW
BEGIN
    INSERT INTO drug_stock (drug_id, total_quantity, last_restocked)
    VALUES (NEW.drug_id, NEW.quantity_received, NEW.created_at)
    ON DUPLICATE KEY UPDATE
        total_quantity = total_quantity + NEW.quantity_received,
        last_restocked = NEW.created_at;
END$$

-- When a batch quantity is updated (dispensing reduces remaining)
CREATE TRIGGER trg_batch_update_stock
AFTER UPDATE ON drug_batches
FOR EACH ROW
BEGIN
    IF NEW.quantity_remaining != OLD.quantity_remaining THEN
        UPDATE drug_stock
        SET total_quantity = total_quantity + (NEW.quantity_remaining - OLD.quantity_remaining),
            updated_at = CURRENT_TIMESTAMP
        WHERE drug_id = NEW.drug_id;
    END IF;
END$$

-- When a bed admission is created, mark bed as occupied
CREATE TRIGGER trg_admission_bed_occupied
AFTER INSERT ON admissions
FOR EACH ROW
BEGIN
    UPDATE beds SET status = 'Occupied', updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.bed_id;
END$$

-- When a patient is discharged, free the bed
CREATE TRIGGER trg_discharge_bed_vacant
AFTER UPDATE ON admissions
FOR EACH ROW
BEGIN
    IF NEW.status = 'Discharged' AND OLD.status = 'Admitted' THEN
        UPDATE beds SET status = 'Vacant', updated_at = CURRENT_TIMESTAMP
        WHERE id = NEW.bed_id;
    END IF;
END$$

DELIMITER ;


-- =============================================================================
-- SEED DATA — Default system setup
-- =============================================================================

-- Default system modules (pages)
INSERT INTO system_modules (name, slug, description, icon, sort_order) VALUES
('Dashboard',                   'dashboard',                'Main overview dashboard',              'fa-home',              1),
('Patient Records',             'patient-records',          'Patient registration and EMR',         'fa-user-injured',      2),
('Appointments',                'appointments',             'Appointment scheduling and queue',     'fa-calendar-check',    3),
('Consultations',               'consultations',            'Visit and consultation records',       'fa-stethoscope',       4),
('Prescriptions',               'prescriptions',            'Digital prescriptions',                'fa-prescription',      5),
('Drug Inventory',              'drug-inventory',           'Drug stock and batch management',      'fa-pills',             6),
('Dispensing',                  'dispensing',               'Drug dispensing and returns',          'fa-hand-holding-medical', 7),
('Ward Management',             'ward-management',          'Wards, beds and admissions',           'fa-bed',               8),
('Laboratory',                  'laboratory',               'Lab requests and results',             'fa-flask',             9),
('Medical Clearance',           'medical-clearance',        '100L student clearance workflow',      'fa-certificate',       10),
('Official Documents',          'official-documents',       'Certificates and letters',             'fa-file-medical',      11),
('Reports & Analytics',         'reports',                  'Statistics and reports',               'fa-chart-bar',         12),
('User Management',             'user-management',          'Staff accounts and roles',             'fa-users-cog',         13),
('Role Permissions',            'role-permissions',         'Role and permission configuration',    'fa-shield-alt',        14),
('Equipment Inventory',         'equipment-inventory',      'Equipment tracking',                   'fa-tools',             15),
('Consumables',                 'consumables',              'Consumables stock management',         'fa-boxes',             16),
('System Settings',             'system-settings',          'Application configuration',            'fa-cog',               17),
('Audit Trail',                 'audit-trail',              'Full system activity log',             'fa-history',           18),
('Notifications',               'notifications',            'System notifications',                 'fa-bell',              19),
('Student Portal',              'student-portal',           'Student self-service portal',          'fa-user-graduate',     20);

-- Default system roles
INSERT INTO roles (name, slug, description, is_system_role) VALUES
('Super Admin',     'super-admin',  'Full unrestricted access to all modules',               TRUE),
('Doctor',          'doctor',       'Clinical consultations, prescriptions, lab requests',   TRUE),
('Nurse',           'nurse',        'Patient care, vitals, ward management, appointments',   TRUE),
('Pharmacist',      'pharmacist',   'Drug inventory, dispensing, prescription review',       TRUE),
('Lab Technician',  'lab-tech',     'Lab requests and results entry',                        TRUE),
('Management',      'management',   'Reports, analytics, inventory overview — view only',    TRUE),
('QA Team',         'qa-team',      'Audit access — read only across all modules',           TRUE),
('ICT Admin',       'ict-admin',    'System settings, user management, no clinical data',    TRUE);

-- Default system settings
INSERT INTO system_settings (setting_key, setting_value, setting_type, description) VALUES
('clinic_name',             'University Health Center',         'string',  'Official clinic name'),
('university_name',         'University Name',                  'string',  'University full name'),
('clinic_address',          '',                                 'string',  'Clinic physical address'),
('clinic_phone',            '',                                 'string',  'Clinic phone number'),
('clinic_email',            '',                                 'string',  'Clinic email address'),
('prescription_validity_days', '30',                           'integer', 'Days before a prescription expires'),
('expiry_alert_days_90',    'true',                             'boolean', 'Send alert 90 days before drug expiry'),
('expiry_alert_days_60',    'true',                             'boolean', 'Send alert 60 days before drug expiry'),
('expiry_alert_days_30',    'true',                             'boolean', 'Send alert 30 days before drug expiry'),
('appointment_slot_minutes','20',                               'integer', 'Default appointment slot duration'),
('session_timeout_minutes', '30',                               'integer', 'Auto logout after inactivity'),
('max_login_attempts',      '5',                                'integer', 'Max failed logins before account lock'),
('smtp_host',               '',                                 'string',  'Email server host'),
('smtp_port',               '587',                              'integer', 'Email server port'),
('sms_api_key',             '',                                 'string',  'SMS gateway API key'),
('patient_uid_prefix',      'UHC',                              'string',  'Prefix for patient IDs e.g. UHC-2025-00001'),
('prescription_uid_prefix', 'UHCMS',                            'string',  'Prefix for prescription IDs'),
('system_version',          '1.0.0',                            'string',  'Current system version');

-- Default drug categories
INSERT INTO drug_categories (name, description) VALUES
('Analgesics',          'Pain relief medications'),
('Antibiotics',         'Bacterial infection treatment'),
('Antimalarials',       'Malaria prevention and treatment'),
('Antivirals',          'Viral infection treatment'),
('Antifungals',         'Fungal infection treatment'),
('Antihistamines',      'Allergy and histamine response medications'),
('Antihypertensives',   'Blood pressure management'),
('Antidiabetics',       'Blood sugar management'),
('Vitamins & Supplements', 'Vitamins, minerals, and supplements'),
('Gastrointestinal',    'Digestive system medications'),
('Respiratory',         'Respiratory and pulmonary medications'),
('Dermatological',      'Skin condition medications'),
('Controlled Substances', 'Restricted medications requiring special handling'),
('IV Fluids',           'Intravenous fluids and solutions'),
('Vaccines',            'Immunisation and vaccines'),
('Contraceptives',      'Family planning medications'),
('Other',               'Uncategorised medications');

-- Default common lab test types
INSERT INTO lab_test_types (name, code, category, turnaround_days) VALUES
('Full Blood Count',            'FBC',      'Haematology',      1),
('Blood Group & Genotype',      'BGG',      'Haematology',      1),
('Malaria Parasite Test',       'MPS',      'Parasitology',     1),
('Urinalysis',                  'URA',      'Microbiology',     1),
('Random Blood Glucose',        'RBG',      'Biochemistry',     1),
('Fasting Blood Glucose',       'FBG',      'Biochemistry',     1),
('Hepatitis B Surface Antigen', 'HBsAg',   'Serology',         1),
('HIV Screening',               'HIV',      'Serology',         1),
('Pregnancy Test',              'PT',       'Immunology',       1),
('Widal Test',                  'WID',      'Serology',         2),
('Stool Microscopy',            'STL',      'Microbiology',     2),
('Sputum AFB',                  'AFB',      'Microbiology',     3),
('Liver Function Test',         'LFT',      'Biochemistry',     2),
('Kidney Function Test',        'KFT',      'Biochemistry',     2),
('Lipid Profile',               'LIP',      'Biochemistry',     2),
('Urine Culture & Sensitivity', 'UCS',      'Microbiology',     3);

SET FOREIGN_KEY_CHECKS = 1;

-- =============================================================================
-- END OF SCHEMA — VanaraUniCare HMS v1.0
-- Total Tables: 52
-- Sections: User Management, Patient Records, EMR, Appointments,
--           Ward Management, Drug Inventory, Prescriptions,
--           Laboratory, Notifications, Student Portal,
--           Official Documents, System Settings
-- =============================================================================