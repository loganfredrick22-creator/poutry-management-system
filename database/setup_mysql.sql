-- FarmLink MySQL Database Setup Script
-- Run this script in MySQL to create the farmlink database and all tables

-- Create database if it doesn't exist
CREATE DATABASE IF NOT EXISTS farmlink CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Use the farmlink database
USE farmlink;

-- Drop existing tables if they exist (for clean setup)
DROP TABLE IF EXISTS audit_log;
DROP TABLE IF EXISTS egg_production;
DROP TABLE IF EXISTS weight_record;
DROP TABLE IF EXISTS mortality_log;
DROP TABLE IF EXISTS health_event;
DROP TABLE IF EXISTS bird;
DROP TABLE IF EXISTS flock;
DROP TABLE IF EXISTS user;

-- Create users table
CREATE TABLE user (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(30) NOT NULL DEFAULT 'admin',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_username (username)
);

-- Create flocks table
CREATE TABLE flock (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL UNIQUE,
    house_location VARCHAR(120) NOT NULL,
    category VARCHAR(30) NOT NULL,
    start_date DATE NOT NULL,
    notes TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_flock_name (name)
);

-- Create birds table
CREATE TABLE bird (
    id INT AUTO_INCREMENT PRIMARY KEY,
    leg_band_number VARCHAR(50) NOT NULL UNIQUE,
    breed VARCHAR(80) NOT NULL,
    category VARCHAR(30) NOT NULL,
    hatch_date DATE NOT NULL,
    flock_id INT,
    status VARCHAR(20) NOT NULL DEFAULT 'alive',
    registration_date DATE NOT NULL DEFAULT (CURDATE()),
    weight_kg DECIMAL(10,3),
    notes TEXT,
    FOREIGN KEY (flock_id) REFERENCES flock(id) ON DELETE SET NULL,
    INDEX idx_leg_band (leg_band_number),
    INDEX idx_flock_id (flock_id),
    INDEX idx_status (status)
);

-- Create health_events table
CREATE TABLE health_event (
    id INT AUTO_INCREMENT PRIMARY KEY,
    bird_id INT NOT NULL,
    event_type VARCHAR(20) NOT NULL,
    event_date DATE NOT NULL,
    description TEXT NOT NULL,
    medicine_used VARCHAR(120),
    dose VARCHAR(80),
    recorded_by VARCHAR(80) NOT NULL,
    severity VARCHAR(10) NOT NULL DEFAULT 'Low',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bird_id) REFERENCES bird(id) ON DELETE CASCADE,
    INDEX idx_bird_id (bird_id),
    INDEX idx_event_date (event_date),
    INDEX idx_event_type (event_type)
);

-- Create mortality_log table
CREATE TABLE mortality_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    bird_id INT NOT NULL,
    death_date DATE NOT NULL,
    cause VARCHAR(120) NOT NULL,
    notes TEXT,
    recorded_by VARCHAR(80) NOT NULL,
    FOREIGN KEY (bird_id) REFERENCES bird(id) ON DELETE CASCADE,
    INDEX idx_bird_id (bird_id),
    INDEX idx_death_date (death_date)
);

-- Create weight_records table
CREATE TABLE weight_record (
    id INT AUTO_INCREMENT PRIMARY KEY,
    bird_id INT NOT NULL,
    recorded_date DATE NOT NULL,
    weight_kg DECIMAL(10,3) NOT NULL,
    FOREIGN KEY (bird_id) REFERENCES bird(id) ON DELETE CASCADE,
    INDEX idx_bird_id (bird_id),
    INDEX idx_recorded_date (recorded_date)
);

-- Create egg_production table
CREATE TABLE egg_production (
    id INT AUTO_INCREMENT PRIMARY KEY,
    bird_id INT NOT NULL,
    flock_id INT NOT NULL,
    date DATE NOT NULL,
    count INT NOT NULL DEFAULT 0,
    FOREIGN KEY (bird_id) REFERENCES bird(id) ON DELETE CASCADE,
    FOREIGN KEY (flock_id) REFERENCES flock(id) ON DELETE CASCADE,
    INDEX idx_bird_id (bird_id),
    INDEX idx_flock_id (flock_id),
    INDEX idx_date (date)
);

-- Create audit_log table
CREATE TABLE audit_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    bird_id INT NOT NULL,
    user_id INT NOT NULL,
    field_changed VARCHAR(80) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bird_id) REFERENCES bird(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
    INDEX idx_bird_id (bird_id),
    INDEX idx_user_id (user_id),
    INDEX idx_timestamp (timestamp)
);

-- Insert default admin user
INSERT INTO user (username, password_hash, role) VALUES 
('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6ukx.LrUpm', 'admin');

-- Create database user for the application (optional - for security)
-- Uncomment and modify as needed
-- CREATE USER 'farmlink_app'@'localhost' IDENTIFIED BY 'secure_password_here';
-- GRANT SELECT, INSERT, UPDATE, DELETE ON farmlink.* TO 'farmlink_app'@'localhost';
-- FLUSH PRIVILEGES;

-- Show created tables
SHOW TABLES;

-- Display setup completion message
SELECT 'FarmLink MySQL database setup completed successfully!' as message;
