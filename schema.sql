CREATE TABLE modbus_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                device_name TEXT NOT NULL,
                current_a REAL,
                current_b REAL,
                current_c REAL,
                power_active REAL,
                power_reactive REAL,
                power_apparent REAL,
                power_factor REAL,
                voltage_an REAL,
                voltage_bn REAL,
                voltage_cn REAL,
                voltage_ab REAL,
                voltage_bc REAL,
                voltage_ca REAL,
                cumulative_active_energy REAL,
                UNIQUE(timestamp, device_name)
            );
CREATE TABLE sqlite_sequence(name,seq);
