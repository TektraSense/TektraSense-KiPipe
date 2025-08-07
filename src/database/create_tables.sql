-- =============================================================================
-- KICAD COMPONENT PIPELINE - PROFESSIONAL DATABASE SETUP SCRIPT
-- =============================================================================

-- Step 1: Create a Dedicated User and Role for the Application
-- สร้าง User ใหม่ชื่อ 'kicad_app' พร้อมรหัสผ่านที่ปลอดภัย
-- DO NOT use the 'postgres' superuser for the application.
CREATE ROLE kicad_app WITH LOGIN PASSWORD 'YOUR_VERY_SECURE_PASSWORD';
ALTER ROLE kicad_app SET client_encoding TO 'utf8';
ALTER ROLE kicad_app SET default_transaction_isolation TO 'read committed';
ALTER ROLE kicad_app SET timezone TO 'UTC';

-- Grant connection ability to the new user on your database
-- (Replace 'YOUR_DATABASE_NAME' with your actual database name, e.g., 'kicad_components')
GRANT CONNECT ON DATABASE "YOUR_DATABASE_NAME" TO kicad_app;

-- Step 2: Create a Dedicated Schema
-- สร้าง Schema ใหม่เพื่อเก็บตารางทั้งหมดของโปรเจกต์นี้ไว้ด้วยกัน
CREATE SCHEMA IF NOT EXISTS kicad_library;
GRANT USAGE ON SCHEMA kicad_library TO kicad_app;

-- Step 3: Create All Tables within the New Schema
-- Note: All tables are now prefixed with 'kicad_library.'

-- `categories` Table
CREATE TABLE IF NOT EXISTS kicad_library.categories (
    category_id SERIAL PRIMARY KEY,
    parent_id INTEGER REFERENCES kicad_library.categories(category_id),
    category_name VARCHAR(255) UNIQUE NOT NULL,
    category_prefix VARCHAR(10) UNIQUE NOT NULL
);

-- `components` Table
CREATE TABLE IF NOT EXISTS kicad_library.components (
    partid SERIAL PRIMARY KEY,
    internal_part_id VARCHAR(255) UNIQUE,
    category_id INTEGER REFERENCES kicad_library.categories(category_id),
    manufacturer_part_number VARCHAR(255) UNIQUE NOT NULL,
    manufacturer VARCHAR(100),
    description TEXT,
    kicad_symbol VARCHAR(512),
    kicad_footprint VARCHAR(512),
    datasheet_url VARCHAR(512),
    parameters JSONB,
    lastupdated TIMESTAMPTZ DEFAULT NOW(),
    component_value VARCHAR(255),
    supplier_1 VARCHAR(100),
    supplier_part_number_1 VARCHAR(100),
    supplier_product_url_1 VARCHAR(255),
    supplier_2 VARCHAR(100),
    supplier_part_number_2 VARCHAR(100),
    supplier_product_url_2 VARCHAR(255),
    product_status VARCHAR(50),
    mounting_type VARCHAR(100),
    package_case VARCHAR(100),
    rohs_status VARCHAR(50),
    operating_temperature VARCHAR(100)
);

-- `category_mappings` Table
CREATE TABLE IF NOT EXISTS kicad_library.category_mappings (
    mapping_id SERIAL PRIMARY KEY,
    supplier_name VARCHAR(100) NOT NULL,
    supplier_category VARCHAR(255) NOT NULL,
    category_id INTEGER NOT NULL REFERENCES kicad_library.categories(category_id),
    UNIQUE (supplier_name, supplier_category)
);

-- `symbols` Table
CREATE TABLE IF NOT EXISTS kicad_library.symbols (
    symbol_id SERIAL PRIMARY KEY,
    library_nickname VARCHAR(255) NOT NULL,
    symbol_name VARCHAR(255) UNIQUE NOT NULL,
    keywords TEXT,
    description TEXT,
    datasheet VARCHAR(512)
);

-- `footprints` Table
CREATE TABLE IF NOT EXISTS kicad_library.footprints (
    footprint_id SERIAL PRIMARY KEY,
    library_nickname VARCHAR(255) NOT NULL,
    footprint_name VARCHAR(255) UNIQUE NOT NULL,
    keywords TEXT
);

-- `footprint_mappings` Table
CREATE TABLE IF NOT EXISTS kicad_library.footprint_mappings (
    mapping_id SERIAL PRIMARY KEY,
    manufacturer_part_number VARCHAR(255) NOT NULL,
    footprint_link VARCHAR(512) NOT NULL,
    UNIQUE (manufacturer_part_number, footprint_link)
);

-- `unmapped_categories` Table
CREATE TABLE IF NOT EXISTS kicad_library.unmapped_categories (
    id SERIAL PRIMARY KEY,
    supplier_name TEXT,
    supplier_category TEXT UNIQUE,
    first_seen_on TIMESTAMPTZ DEFAULT NOW()
);


-- Step 4: Grant Permissions to the Application User
-- ให้สิทธิ์ User 'kicad_app' ในการทำงานกับตารางทั้งหมดใน Schema 'kicad_library'
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA kicad_library TO kicad_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA kicad_library TO kicad_app;


-- Step 5: Initial Data Seeding for `categories`
-- เพิ่มข้อมูลหมวดหมู่เริ่มต้นเพื่อให้ระบบพร้อมใช้งาน
INSERT INTO kicad_library.categories (category_id, parent_id, category_name, category_prefix) VALUES
(1, NULL, 'Integrated Circuits', 'ICS'),
(2, NULL, 'Discrete Semiconductors', 'DSC'),
(3, NULL, 'Passive Components', 'PCP'),
(4, NULL, 'Electromechanical', 'EMC'),
(5, NULL, 'Connectors', 'CON'),
(6, NULL, 'Tools and Supplies', 'TNS'),
(7, NULL, 'Sensors', 'SEN'),
(8, NULL, 'Optoelectronics', 'OPE'),
(9, NULL, 'Circuit Protection', 'CPT'),
(10, NULL, 'Power Products', 'PWR'),
(31, 1, 'Clock and Timing ICs', 'CTM'),
(32, 1, 'Data Converter ICs', 'DCV'),
(33, 1, 'Embedded Processors and Controllers', 'EPC'),
(34, 1, 'Interface ICs', 'IFC'),
(35, 1, 'Linear ICs', 'LNR'),
(36, 1, 'Logic ICs', 'LOG'),
(37, 1, 'Memory ICs', 'MEM'),
(38, 1, 'Power Management ICs', 'PMN'),
(39, 1, 'RF Semiconductors and Devices', 'RFS'),
(40, 2, 'Diodes', 'DIO'),
(41, 2, 'Thyristors', 'THY'),
(42, 2, 'Transistors', 'TRN'),
(43, 3, 'Capacitors', 'CAP'),
(44, 3, 'Crystals and Oscillators', 'COX'),
(45, 3, 'EMI / RFI Components', 'ERC'),
(46, 3, 'Inductors', 'IND'),
(47, 3, 'Resistors', 'RES'),
(48, 3, 'Transformers', 'TRF'),
(49, 4, 'Audio Products', 'AUD'),
(50, 4, 'Motors and Drives', 'MOT'),
(51, 4, 'Relays', 'REL'),
(52, 4, 'Switches', 'SWT'),
(53, 4, 'Thermal Management', 'THM'),
(54, 5, 'Audio / Video Connectors', 'AVC'),
(55, 5, 'Automotive Connectors', 'AUC'),
(56, 5, 'Backplane Connectors', 'BPC'),
(57, 5, 'Board to Board Connectors', 'BBC'),
(58, 5, 'Card Edge Connectors', 'CEC'),
(59, 5, 'Circular Connectors', 'CRC'),
(60, 5, 'D-Sub Connectors', 'DSC'),
(61, 5, 'FFC / FPC', 'FFC'),
(62, 5, 'Fiber Optic Connectors', 'FOC'),
(63, 5, 'Headers and Wire Housings', 'HWH'),
(64, 5, 'IC and Component Sockets', 'ICS'),
(65, 5, 'Memory Connectors', 'MNC'),
(66, 5, 'Modular / Ethernet Connectors', 'MEC'),
(67, 5, 'Photovoltaic / Solar Connectors', 'PSC'),
(68, 5, 'Power Connectors', 'PWC'),
(69, 5, 'RF / Coaxial Connectors', 'RFC'),
(70, 5, 'Terminal Blocks', 'TBK'),
(71, 5, 'Terminals', 'TRM'),
(72, 5, 'USB Connectors', 'USC'),
(73, 6, 'Hardware and Fasteners', 'HWF'),
(74, 6, 'Fiducial Marks', 'FDM'),
(75, 6, 'Logos', 'LGS'),
(76, 6, 'Pad Connections', 'PDC'),
(77, 6, 'Testpoints', 'TST'),
(78, 6, 'Program Connectors', 'PCN'),
(79, 7, 'Current Sensors', 'CUR'),
(80, 7, 'Flow Sensors', 'FLW'),
(81, 7, 'Magnetic Sensors', 'MAG'),
(82, 7, 'Motion Sensors', 'MTS'),
(83, 7, 'Optical Sensors', 'OPT'),
(84, 7, 'Pressure Sensors', 'PRS'),
(85, 7, 'Proximity Sensors', 'PRX'),
(86, 7, 'Temperature and Humidity Sensors', 'THS'),
(87, 8, 'Displays', 'DSP'),
(88, 8, 'Fiber Optics', 'FBO'),
(89, 8, 'LEDs', 'LED'),
(90, 8, 'Lamps', 'LMP'),
(91, 8, 'Laser Products', 'LSP'),
(92, 8, 'Optocouplers', 'OPC'),
(93, 9, 'Circuit Breakers', 'CBR'),
(94, 9, 'ESD and Circuit Protection ICs', 'ESD'),
(95, 9, 'Fuse Holders', 'FUS'),
(96, 9, 'Fuses', 'FUS'),
(97, 9, 'PTC Resettable Fuses', 'PTC'),
(98, 9, 'TVS Diodes', 'TVS'),
(99, 9, 'Varistors', 'VAR'),
(100, 10, 'Power Supply Modules', 'PSM'),
(101, 10, 'Batteries and Accessories', 'BAT')
ON CONFLICT (category_id) DO NOTHING;

-- Reset sequence to avoid issues if IDs were inserted manually before
SELECT setval('kicad_library.categories_category_id_seq', (SELECT MAX(category_id) FROM kicad_library.categories));