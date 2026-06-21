from database.database import get_connection


def create_plc_master():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS plc_master (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        plc_name TEXT UNIQUE NOT NULL,

        ip_address TEXT NOT NULL,
        
        description TEXT,

        active INTEGER DEFAULT 1,

        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


def create_users():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        username TEXT UNIQUE NOT NULL,

        password_hash TEXT NOT NULL,

        role TEXT NOT NULL,

        active INTEGER DEFAULT 1,

        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

        last_login DATETIME,

        created_by TEXT
    )
    """)

    conn.commit()
    conn.close()


def create_recipe_master():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recipe_master (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        recipe_code TEXT UNIQUE NOT NULL,

        recipe_name TEXT,
        
        recipe_description TEXT,

        current_version INTEGER DEFAULT 1,
        
        recipe_status TEXT DEFAULT 'DRAFT',

        active INTEGER DEFAULT 1,

        created_by TEXT,

        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

        last_modified_by TEXT,

        last_modified_at DATETIME
    )
    """)

    conn.commit()
    conn.close()


def create_recipe_parameters():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recipe_parameters (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        recipe_code TEXT NOT NULL,

        version INTEGER DEFAULT 1,

        display_order INTEGER,

        plc_array_index INTEGER,

        category TEXT,
        
        parameter_group TEXT,

        parameter_name TEXT NOT NULL,

        recipe_parameter_description TEXT,

        plc_tag_name TEXT,

        parameter_value REAL,

        data_type TEXT,

        unit TEXT,

        min_value REAL,

        max_value REAL,

        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

        UNIQUE (
            recipe_code,
            version,
            parameter_name
        )
    )
    """)

    conn.commit()
    conn.close()

def create_recipe_phase_control():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recipe_phase_control (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        recipe_code TEXT NOT NULL,

        version INTEGER DEFAULT 1,

        phase_order INTEGER NOT NULL,

        machine_side TEXT,

        phase_description TEXT,

        stop_flag TEXT,

        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()
    


def create_audit_log():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_log (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

        username TEXT,

        role TEXT,

        workstation_name TEXT,

        client_ip TEXT,

        plc_name TEXT,

        recipe_code TEXT,

        recipe_version INTEGER,

        record_id INTEGER,

        parameter_name TEXT,

        old_value TEXT,

        new_value TEXT,

        action TEXT,

        change_source TEXT,

        reason TEXT
    )
    """)

    conn.commit()
    conn.close()


def create_recipe_upload_history():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recipe_upload_history (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        plc_name TEXT,

        recipe_code TEXT,

        recipe_version INTEGER,

        uploaded_by TEXT,

        uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,

        status TEXT,

        remarks TEXT
    )
    """)

    conn.commit()
    conn.close()
    
def create_recipe_download_history():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recipe_download_history (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        plc_name TEXT NOT NULL,

        recipe_code TEXT NOT NULL,

        recipe_version INTEGER NOT NULL,

        download_status TEXT NOT NULL,

        downloaded_by TEXT,

        download_time DATETIME
        DEFAULT CURRENT_TIMESTAMP

    )
    """)

    conn.commit()
    conn.close()

    print(
        ">>> create_recipe_download_history called"
    )


def create_user_sessions():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_sessions (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        username TEXT,

        login_time DATETIME DEFAULT CURRENT_TIMESTAMP,

        logout_time DATETIME,

        client_ip TEXT,

        workstation_name TEXT
    )
    """)

    conn.commit()
    conn.close()
    
    
def create_recipe_plc_mapping():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recipe_plc_mapping (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        recipe_code TEXT NOT NULL,

        plc_name TEXT NOT NULL,

        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

    
def create_recipe_parameters_index():

    print(">>> create_recipe_parameters_index called")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_recipe_parameters
    ON recipe_parameters (
        recipe_code,
        version
    )
    """)

    conn.commit()
    conn.close()


def create_phase_control_index():

    print(">>> create_phase_control_index called")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_phase_control
    ON recipe_phase_control (
        recipe_code,
        version
    )
    """)

    conn.commit()
    conn.close()
    
def create_plc_parameter_mapping():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS plc_parameter_mapping (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        plc_name TEXT NOT NULL,

        parameter_name TEXT NOT NULL,

        plc_array_index INTEGER NOT NULL,

        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()