-- MySQL 8.0.16+ / InnoDB: 1 staging + 7 normalized/domain tables.
-- DDL initializes empty tables. load_data replaces their contents transactionally.

CREATE TABLE IF NOT EXISTS staging_bank_full (
    source_row_id INT PRIMARY KEY CHECK (source_row_id > 0),
    `age` INT NOT NULL CHECK (`age` BETWEEN 1 AND 120),
    `job` VARCHAR(32) NOT NULL CHECK (`job` IN ('admin.', 'blue-collar', 'entrepreneur', 'housemaid', 'management', 'retired', 'self-employed', 'services', 'student', 'technician', 'unemployed', 'unknown')),
    `marital` VARCHAR(32) NOT NULL CHECK (`marital` IN ('divorced', 'married', 'single')),
    `education` VARCHAR(32) NOT NULL CHECK (`education` IN ('primary', 'secondary', 'tertiary', 'unknown')),
    `default` VARCHAR(32) NOT NULL CHECK (`default` IN ('yes', 'no')),
    `balance` INT NOT NULL CHECK (`balance` BETWEEN -2147483648 AND 2147483647),
    `housing` VARCHAR(32) NOT NULL CHECK (`housing` IN ('yes', 'no')),
    `loan` VARCHAR(32) NOT NULL CHECK (`loan` IN ('yes', 'no')),
    `contact` VARCHAR(32) NOT NULL CHECK (`contact` IN ('cellular', 'telephone', 'unknown')),
    `day` INT NOT NULL CHECK (`day` BETWEEN 1 AND 31),
    `month` VARCHAR(32) NOT NULL CHECK (`month` IN ('jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec')),
    `duration` INT NOT NULL CHECK (`duration` BETWEEN 0 AND 2147483647),
    `campaign` INT NOT NULL CHECK (`campaign` BETWEEN 1 AND 2147483647),
    `pdays` INT NOT NULL CHECK (`pdays` BETWEEN -1 AND 2147483647),
    `previous` INT NOT NULL CHECK (`previous` BETWEEN 0 AND 2147483647),
    `poutcome` VARCHAR(32) NOT NULL CHECK (`poutcome` IN ('failure', 'other', 'success', 'unknown')),
    `y` VARCHAR(32) NOT NULL CHECK (`y` IN ('yes', 'no'))
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS job (
    id INT PRIMARY KEY,
    value VARCHAR(32) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS marital_status (
    id INT PRIMARY KEY,
    value VARCHAR(32) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS education (
    id INT PRIMARY KEY,
    value VARCHAR(32) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS contact_method (
    id INT PRIMARY KEY,
    value VARCHAR(32) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS previous_outcome (
    id INT PRIMARY KEY,
    value VARCHAR(32) NOT NULL UNIQUE
) ENGINE=InnoDB;

-- source_row_id identifies a CSV row, not a persistent bank customer.
CREATE TABLE IF NOT EXISTS client_record (
    source_row_id INT PRIMARY KEY,
    age INT NOT NULL CHECK (age BETWEEN 1 AND 120),
    job_id INT NOT NULL,
    marital_status_id INT NOT NULL,
    education_id INT NOT NULL,
    default_credit ENUM('yes', 'no') NOT NULL,
    balance INT NOT NULL,
    housing ENUM('yes', 'no') NOT NULL,
    loan ENUM('yes', 'no') NOT NULL,
    FOREIGN KEY (source_row_id) REFERENCES staging_bank_full(source_row_id),
    FOREIGN KEY (job_id) REFERENCES job(id),
    FOREIGN KEY (marital_status_id) REFERENCES marital_status(id),
    FOREIGN KEY (education_id) REFERENCES education(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS campaign_contact (
    source_row_id INT PRIMARY KEY,
    contact_method_id INT NOT NULL,
    day INT NOT NULL CHECK (day BETWEEN 1 AND 31),
    month ENUM('jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec') NOT NULL,
    duration INT NOT NULL CHECK (duration >= 0),
    campaign INT NOT NULL CHECK (campaign >= 1),
    pdays INT NOT NULL CHECK (pdays >= -1),
    previous INT NOT NULL CHECK (previous >= 0),
    previous_outcome_id INT NOT NULL,
    subscribed ENUM('yes', 'no') NOT NULL,
    FOREIGN KEY (source_row_id) REFERENCES client_record(source_row_id),
    FOREIGN KEY (contact_method_id) REFERENCES contact_method(id),
    FOREIGN KEY (previous_outcome_id) REFERENCES previous_outcome(id)
) ENGINE=InnoDB;
