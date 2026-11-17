-- ============================================================
-- Face Recognition Attendance System
-- schema.sql — সব 8টা table এক সাথে
-- Run: mysql -u root -p face_attendance_db < schema.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS face_attendance_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE face_attendance_db;

-- ============================================================
-- TABLE 1: admins
-- Admin login credentials
-- ============================================================
CREATE TABLE IF NOT EXISTS admins (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(50)  UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at    DATETIME DEFAULT NOW()
);

-- Default admin: username=admin, password=admin123
-- (password_hash নিচে plain text — প্রথমবার login এর পর bcrypt দিয়ে replace হবে)
-- আসল hash টা Python দিয়ে generate করতে হবে, তাই placeholder রাখা হয়েছে
INSERT IGNORE INTO admins (username, password_hash)
VALUES ('admin', '$2b$12$placeholder_run_setup_py_to_fix');

-- ============================================================
-- TABLE 2: teachers
-- Teacher info + face encoding
-- ============================================================
CREATE TABLE IF NOT EXISTS teachers (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    department    VARCHAR(100) NOT NULL,
    designation   VARCHAR(100),
    face_encoding LONGBLOB     NOT NULL,
    created_at    DATETIME DEFAULT NOW()
);

-- ============================================================
-- TABLE 3: users (Students)
-- Student registration info
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    roll          VARCHAR(30)  UNIQUE NOT NULL,
    name          VARCHAR(100) NOT NULL,
    department    VARCHAR(100) NOT NULL,
    semester      VARCHAR(20)  NOT NULL,
    phone         VARCHAR(20),
    face_encoding LONGBLOB     NOT NULL,
    status        ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
    created_at    DATETIME DEFAULT NOW()
);

-- ============================================================
-- TABLE 4: registration_requests
-- Student self-registration যেগুলো admin approve করেনি
-- ============================================================
CREATE TABLE IF NOT EXISTS registration_requests (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    roll          VARCHAR(30)  NOT NULL,
    name          VARCHAR(100) NOT NULL,
    department    VARCHAR(100) NOT NULL,
    semester      VARCHAR(20)  NOT NULL,
    phone         VARCHAR(20),
    face_encoding LONGBLOB     NOT NULL,
    status        ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
    submitted_at  DATETIME DEFAULT NOW()
);

-- ============================================================
-- TABLE 5: routines
-- Class schedule — admin add করে
-- ============================================================
CREATE TABLE IF NOT EXISTS routines (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    department       VARCHAR(100) NOT NULL,
    semester         VARCHAR(20)  NOT NULL,
    day              VARCHAR(15)  NOT NULL,  -- Monday, Tuesday...
    subject          VARCHAR(100) NOT NULL,
    teacher_id       INT,
    class_start      TIME         NOT NULL,
    class_end        TIME         NOT NULL,
    scan_start_range TIME         NOT NULL,  -- কখন scan-in শুরু
    scan_end_range   TIME         NOT NULL,  -- কখন scan-out শেষ
    created_at       DATETIME DEFAULT NOW(),
    FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE SET NULL
);

-- ============================================================
-- TABLE 6: attendance_sessions
-- প্রতিটা class এর session record
-- ============================================================
CREATE TABLE IF NOT EXISTS attendance_sessions (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    routine_id       INT,
    teacher_id       INT,
    session_date     DATE         NOT NULL,
    subject          VARCHAR(100) NOT NULL,
    teacher_scan_in  DATETIME,
    teacher_scan_out DATETIME,
    status           ENUM('open', 'closed') DEFAULT 'open',
    FOREIGN KEY (routine_id)  REFERENCES routines(id)  ON DELETE SET NULL,
    FOREIGN KEY (teacher_id)  REFERENCES teachers(id)  ON DELETE SET NULL
);

-- ============================================================
-- TABLE 7: attendance_records
-- প্রতিটা student এর attendance entry per session
-- ============================================================
CREATE TABLE IF NOT EXISTS attendance_records (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    session_id   INT NOT NULL,
    user_id      INT NOT NULL,
    scan_in_time DATETIME,
    scan_out_time DATETIME,
    status       ENUM('pending', 'complete') DEFAULT 'pending',
    FOREIGN KEY (session_id) REFERENCES attendance_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id)    REFERENCES users(id)               ON DELETE CASCADE,
    UNIQUE KEY unique_session_user (session_id, user_id)
);

-- ============================================================
-- TABLE 8: unknown_face_logs
-- অচেনা face detect হলে এখানে log হয়
-- ============================================================
CREATE TABLE IF NOT EXISTS unknown_face_logs (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    detected_at  DATETIME     NOT NULL DEFAULT NOW(),
    image_path   VARCHAR(255),
    page_context VARCHAR(100)  -- কোন page থেকে scan হয়েছিল
);

-- ============================================================
-- Indexes for faster queries
-- ============================================================
CREATE INDEX idx_users_roll         ON users(roll);
CREATE INDEX idx_users_status       ON users(status);
CREATE INDEX idx_routines_day       ON routines(day);
CREATE INDEX idx_sessions_date      ON attendance_sessions(session_date);
CREATE INDEX idx_records_session    ON attendance_records(session_id);
CREATE INDEX idx_reg_requests_status ON registration_requests(status);