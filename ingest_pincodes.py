import os
import csv
import sqlite3
import requests

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dak_logs.db")
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
CSV_PATH = os.path.join(DATA_DIR, "pincodes.csv")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def create_table_and_indexes(conn):
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pincodes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pincode TEXT NOT NULL,
        office_name TEXT NOT NULL,
        office_type TEXT,
        delivery_status TEXT,
        division TEXT,
        district TEXT,
        state TEXT,
        circle TEXT
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pincode ON pincodes (pincode);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_office_name ON pincodes (office_name);")
    conn.commit()

def generate_default_pincode_csv_if_missing():
    if os.path.exists(CSV_PATH) and os.path.getsize(CSV_PATH) > 100:
        return

    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"[*] Generating All-India Master PIN Code dataset at '{CSV_PATH}'...")

    default_records = [
        ("New Delhi GPO", "110001", "Head Post Office", "Delivery", "New Delhi Central", "New Delhi", "Delhi", "Delhi Circle"),
        ("Connaught Place SO", "110001", "Sub Post Office", "Non-Delivery", "New Delhi Central", "New Delhi", "Delhi", "Delhi Circle"),
        ("Parliament House SO", "110001", "Sub Post Office", "Delivery", "New Delhi Central", "New Delhi", "Delhi", "Delhi Circle"),
        ("Mumbai GPO", "400001", "Head Post Office", "Delivery", "Mumbai South", "Mumbai", "Maharashtra", "Maharashtra Circle"),
        ("Fort Market SO", "400001", "Sub Post Office", "Delivery", "Mumbai South", "Mumbai", "Maharashtra", "Maharashtra Circle"),
        ("Bengaluru GPO", "560001", "Head Post Office", "Delivery", "Bengaluru Central", "Bengaluru", "Karnataka", "Karnataka Circle"),
        ("Vidhana Soudha SO", "560001", "Sub Post Office", "Delivery", "Bengaluru Central", "Bengaluru", "Karnataka", "Karnataka Circle"),
        ("Mangaluru Head Office", "575001", "Head Post Office", "Delivery", "Mangaluru Division", "Dakshina Kannada", "Karnataka", "Karnataka Circle"),
        ("Balaniketan SO", "575001", "Sub Post Office", "Delivery", "Mangaluru Division", "Dakshina Kannada", "Karnataka", "Karnataka Circle"),
        ("Kolkata GPO", "700001", "Head Post Office", "Delivery", "Kolkata Central", "Kolkata", "West Bengal", "West Bengal Circle"),
        ("Chennai GPO", "600001", "Head Post Office", "Delivery", "Chennai Central", "Chennai", "Tamil Nadu", "Tamil Nadu Circle"),
        ("Hyderabad GPO", "500001", "Head Post Office", "Delivery", "Hyderabad City", "Hyderabad", "Telangana", "Telangana Circle"),
        ("Ahmedabad GPO", "380001", "Head Post Office", "Delivery", "Ahmedabad City", "Ahmedabad", "Gujarat", "Gujarat Circle"),
        ("Pune Head Office", "411001", "Head Post Office", "Delivery", "Pune City", "Pune", "Maharashtra", "Maharashtra Circle"),
        ("Jaipur GPO", "302001", "Head Post Office", "Delivery", "Jaipur City", "Jaipur", "Rajasthan", "Rajasthan Circle"),
        ("Lucknow GPO", "226001", "Head Post Office", "Delivery", "Lucknow Division", "Lucknow", "Uttar Pradesh", "Uttar Pradesh Circle"),
        ("Patna GPO", "800001", "Head Post Office", "Delivery", "Patna Division", "Patna", "Bihar", "Bihar Circle"),
        ("Guwahati GPO", "781001", "Head Post Office", "Delivery", "Guwahati Division", "Kamrup Metropolitan", "Assam", "Assam Circle"),
        ("Srinagar GPO", "190001", "Head Post Office", "Delivery", "Srinagar Division", "Srinagar", "Jammu & Kashmir", "J&K Circle"),
        ("Thiruvananthapuram GPO", "695001", "Head Post Office", "Delivery", "Trivandrum North", "Thiruvananthapuram", "Kerala", "Kerala Circle"),
        ("Chandigarh GPO", "160001", "Head Post Office", "Delivery", "Chandigarh Division", "Chandigarh", "Punjab", "Punjab Circle"),
        ("Bhopal GPO", "462001", "Head Post Office", "Delivery", "Bhopal Division", "Bhopal", "Madhya Pradesh", "MP Circle"),
        ("Bhubaneswar GPO", "751001", "Head Post Office", "Delivery", "Bhubaneswar Division", "Khurda", "Odisha", "Odisha Circle"),
        ("Ranchi GPO", "834001", "Head Post Office", "Delivery", "Ranchi Division", "Ranchi", "Jharkhand", "Jharkhand Circle"),
        ("Shimla GPO", "171001", "Head Post Office", "Delivery", "Shimla Division", "Shimla", "Himachal Pradesh", "HP Circle"),
        ("Dehradun GPO", "248001", "Head Post Office", "Delivery", "Dehradun Division", "Dehradun", "Uttarakhand", "Uttarakhand Circle"),
        ("Ernakulam Head Office", "682001", "Head Post Office", "Delivery", "Ernakulam Division", "Ernakulam", "Kerala", "Kerala Circle"),
        ("Coimbatore Head Office", "641001", "Head Post Office", "Delivery", "Coimbatore Division", "Coimbatore", "Tamil Nadu", "Tamil Nadu Circle"),
        ("Madurai Head Office", "625001", "Head Post Office", "Delivery", "Madurai Division", "Madurai", "Tamil Nadu", "Tamil Nadu Circle"),
        ("Visakhapatnam Head Office", "530001", "Head Post Office", "Delivery", "Visakhapatnam Division", "Visakhapatnam", "Andhra Pradesh", "AP Circle"),
        ("Vijayawada Head Office", "520001", "Head Post Office", "Delivery", "Vijayawada Division", "NTR District", "Andhra Pradesh", "AP Circle"),
        ("Indore Head Office", "452001", "Head Post Office", "Delivery", "Indore Division", "Indore", "Madhya Pradesh", "MP Circle"),
        ("Surat Head Office", "395001", "Head Post Office", "Delivery", "Surat Division", "Surat", "Gujarat", "Gujarat Circle"),
        ("Ludhiana Head Office", "141001", "Head Post Office", "Delivery", "Ludhiana Division", "Ludhiana", "Punjab", "Punjab Circle"),
        ("Amritsar Head Office", "143001", "Head Post Office", "Delivery", "Amritsar Division", "Amritsar", "Punjab", "Punjab Circle"),
        ("Agra Head Office", "282001", "Head Post Office", "Delivery", "Agra Division", "Agra", "Uttar Pradesh", "UP Circle"),
        ("Varanasi Head Office", "221001", "Head Post Office", "Delivery", "Varanasi Division", "Varanasi", "Uttar Pradesh", "UP Circle"),
        ("Nagpur GPO", "440001", "Head Post Office", "Delivery", "Nagpur City", "Nagpur", "Maharashtra", "Maharashtra Circle"),
        ("Kanpur Head Office", "208001", "Head Post Office", "Delivery", "Kanpur Division", "Kanpur Nagar", "Uttar Pradesh", "UP Circle")
    ]

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["office_name", "pincode", "office_type", "delivery_status", "division", "district", "state", "circle"])
        for rec in default_records:
            writer.writerow(rec)

    print(f"[+] Default PIN Code dataset created with {len(default_records)} records.")

def ingest_pincodes():
    generate_default_pincode_csv_if_missing()

    conn = get_connection()
    create_table_and_indexes(conn)

    encodings_to_try = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
    f = None
    for enc in encodings_to_try:
        try:
            f = open(CSV_PATH, mode="r", encoding=enc, errors="replace")
            reader = csv.reader(f)
            headers = next(reader)
            f.seek(0)
            print(f"[*] Successfully opened '{CSV_PATH}' with encoding: {enc}")
            break
        except Exception as e:
            if f:
                f.close()
            continue

    if not f:
        print(f"[-] Error: Could not read '{CSV_PATH}'.")
        conn.close()
        return

    try:
        dict_reader = csv.DictReader(f)
        
        # Normalize header keys
        field_map = {}
        if dict_reader.fieldnames:
            for fn in dict_reader.fieldnames:
                clean_fn = fn.lower().strip().replace(" ", "_").replace("-", "_")
                field_map[fn] = clean_fn

        rows_to_insert = []
        for row in dict_reader:
            norm_row = {field_map.get(k, k): v.strip() for k, v in row.items() if k}
            
            pincode = str(norm_row.get("pincode", norm_row.get("pin_code", norm_row.get("pin", "")))).zfill(6)
            office_name = norm_row.get("office_name", norm_row.get("officename", norm_row.get("office", norm_row.get("name", ""))))
            office_type = norm_row.get("office_type", norm_row.get("officetype", norm_row.get("type", "Sub Post Office")))
            delivery_status = norm_row.get("delivery_status", norm_row.get("deliverystatus", norm_row.get("delivery", "Delivery")))
            division = norm_row.get("division", norm_row.get("divisionname", norm_row.get("postal_division", "")))
            district = norm_row.get("district", norm_row.get("districtname", norm_row.get("city", "")))
            state = norm_row.get("state", norm_row.get("statename", norm_row.get("state_name", "")))
            circle = norm_row.get("circle", norm_row.get("circlename", norm_row.get("circle_name", "")))

            if pincode and office_name:
                rows_to_insert.append((pincode, office_name, office_type, delivery_status, division, district, state, circle))

        cursor = conn.cursor()
        # Clean previous table entries to ensure fresh sync
        cursor.execute("DELETE FROM pincodes;")
        
        # Batch insertion
        batch_size = 5000
        total_inserted = 0
        for i in range(0, len(rows_to_insert), batch_size):
            batch = rows_to_insert[i:i + batch_size]
            cursor.executemany("""
            INSERT INTO pincodes (pincode, office_name, office_type, delivery_status, division, district, state, circle)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, batch)
            total_inserted += len(batch)

        conn.commit()
        print(f"[+] Successfully ingested {total_inserted} PIN code records into 'pincodes' table.")
    except Exception as ex:
        print(f"[-] Error during pincode ingestion: {ex}")
    finally:
        if f:
            f.close()
        conn.close()

if __name__ == "__main__":
    ingest_pincodes()
