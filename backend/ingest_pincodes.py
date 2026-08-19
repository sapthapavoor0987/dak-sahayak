import os
import csv
import sqlite3

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
        taluk TEXT,
        division TEXT,
        district TEXT,
        region TEXT,
        state TEXT,
        circle TEXT
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pincode ON pincodes (pincode);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_office_name ON pincodes (office_name);")
    conn.commit()

def generate_default_pincode_csv_if_missing():
    # Always refresh CSV to include taluk & region columns
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"[*] Generating All-India Master PIN Code dataset at '{CSV_PATH}'...")

    default_records = [
        ("New Delhi GPO", "110001", "Head Post Office", "Delivery", "New Delhi", "New Delhi Central", "New Delhi", "Delhi Region", "Delhi", "Delhi Circle"),
        ("Connaught Place SO", "110001", "Sub Post Office", "Non-Delivery", "New Delhi", "New Delhi Central", "New Delhi", "Delhi Region", "Delhi", "Delhi Circle"),
        ("Parliament House SO", "110001", "Sub Post Office", "Delivery", "New Delhi", "New Delhi Central", "New Delhi", "Delhi Region", "Delhi", "Delhi Circle"),
        ("Mumbai GPO", "400001", "Head Post Office", "Delivery", "Mumbai", "Mumbai South", "Mumbai", "Mumbai Region", "Maharashtra", "Maharashtra Circle"),
        ("Fort Market SO", "400001", "Sub Post Office", "Delivery", "Mumbai", "Mumbai South", "Mumbai", "Mumbai Region", "Maharashtra", "Maharashtra Circle"),
        ("Bengaluru GPO", "560001", "Head Post Office", "Delivery", "Bengaluru North", "Bengaluru Central", "Bengaluru", "Bengaluru Region", "Karnataka", "Karnataka Circle"),
        ("Vidhana Soudha SO", "560001", "Sub Post Office", "Delivery", "Bengaluru North", "Bengaluru Central", "Bengaluru", "Bengaluru Region", "Karnataka", "Karnataka Circle"),
        ("Mangaluru Head Office", "575001", "Head Post Office", "Delivery", "Mangaluru", "Mangaluru Division", "Dakshina Kannada", "South Karnataka Region", "Karnataka", "Karnataka Circle"),
        ("Balaniketan SO", "575001", "Sub Post Office", "Delivery", "Mangaluru", "Mangaluru Division", "Dakshina Kannada", "South Karnataka Region", "Karnataka", "Karnataka Circle"),
        ("Puttur HO", "574201", "Head Post Office", "Delivery", "Puttur", "Puttur Division", "Dakshina Kannada", "South Karnataka Region", "Karnataka", "Karnataka Circle"),
        ("Kammadi BO", "574201", "Branch Office", "Delivery", "Puttur", "Puttur Division", "Dakshina Kannada", "South Karnataka Region", "Karnataka", "Karnataka Circle"),
        ("Kolkata GPO", "700001", "Head Post Office", "Delivery", "Kolkata", "Kolkata Central", "Kolkata", "Kolkata Region", "West Bengal", "West Bengal Circle"),
        ("Chennai GPO", "600001", "Head Post Office", "Delivery", "Chennai", "Chennai Central", "Chennai", "Chennai Region", "Tamil Nadu", "Tamil Nadu Circle"),
        ("Hyderabad GPO", "500001", "Head Post Office", "Delivery", "Hyderabad", "Hyderabad City", "Hyderabad", "Hyderabad Region", "Telangana", "Telangana Circle"),
        ("Ahmedabad GPO", "380001", "Head Post Office", "Delivery", "Ahmedabad", "Ahmedabad City", "Ahmedabad", "HQ Region", "Gujarat", "Gujarat Circle"),
        ("Pune Head Office", "411001", "Head Post Office", "Delivery", "Pune", "Pune City", "Pune", "Pune Region", "Maharashtra", "Maharashtra Circle"),
        ("Jaipur GPO", "302001", "Head Post Office", "Delivery", "Jaipur", "Jaipur City", "Jaipur", "HQ Region", "Rajasthan", "Rajasthan Circle"),
        ("Lucknow GPO", "226001", "Head Post Office", "Delivery", "Lucknow", "Lucknow Division", "Lucknow", "HQ Region", "Uttar Pradesh", "Uttar Pradesh Circle"),
        ("Patna GPO", "800001", "Head Post Office", "Delivery", "Patna", "Patna Division", "Patna", "HQ Region", "Bihar", "Bihar Circle"),
        ("Guwahati GPO", "781001", "Head Post Office", "Delivery", "Guwahati", "Guwahati Division", "Kamrup Metropolitan", "HQ Region", "Assam", "Assam Circle"),
        ("Srinagar GPO", "190001", "Head Post Office", "Delivery", "Srinagar", "Srinagar Division", "Srinagar", "Srinagar Region", "Jammu & Kashmir", "J&K Circle"),
        ("Thiruvananthapuram GPO", "695001", "Head Post Office", "Delivery", "Trivandrum", "Trivandrum North", "Thiruvananthapuram", "HQ Region", "Kerala", "Kerala Circle"),
        ("Chandigarh GPO", "160001", "Head Post Office", "Delivery", "Chandigarh", "Chandigarh Division", "Chandigarh", "HQ Region", "Punjab", "Punjab Circle"),
        ("Bhopal GPO", "462001", "Head Post Office", "Delivery", "Bhopal", "Bhopal Division", "Bhopal", "HQ Region", "Madhya Pradesh", "MP Circle"),
        ("Bhubaneswar GPO", "751001", "Head Post Office", "Delivery", "Bhubaneswar", "Bhubaneswar Division", "Khurda", "HQ Region", "Odisha", "Odisha Circle"),
        ("Ranchi GPO", "834001", "Head Post Office", "Delivery", "Ranchi", "Ranchi Division", "Ranchi", "HQ Region", "Jharkhand", "Jharkhand Circle"),
        ("Shimla GPO", "171001", "Head Post Office", "Delivery", "Shimla", "Shimla Division", "Shimla", "HQ Region", "Himachal Pradesh", "HP Circle"),
        ("Dehradun GPO", "248001", "Head Post Office", "Delivery", "Dehradun", "Dehradun Division", "Dehradun", "HQ Region", "Uttarakhand", "Uttarakhand Circle"),
        ("Ernakulam Head Office", "682001", "Head Post Office", "Delivery", "Kochi", "Ernakulam Division", "Ernakulam", "Central Region", "Kerala", "Kerala Circle"),
        ("Coimbatore Head Office", "641001", "Head Post Office", "Delivery", "Coimbatore", "Coimbatore Division", "Coimbatore", "Western Region", "Tamil Nadu", "Tamil Nadu Circle"),
        ("Madurai Head Office", "625001", "Head Post Office", "Delivery", "Madurai", "Madurai Division", "Madurai", "Southern Region", "Tamil Nadu", "Tamil Nadu Circle"),
        ("Visakhapatnam Head Office", "530001", "Head Post Office", "Delivery", "Visakhapatnam", "Visakhapatnam Division", "Visakhapatnam", "Visakhapatnam Region", "Andhra Pradesh", "AP Circle"),
        ("Vijayawada Head Office", "520001", "Head Post Office", "Delivery", "Vijayawada", "Vijayawada Division", "NTR District", "Vijayawada Region", "Andhra Pradesh", "AP Circle"),
        ("Indore Head Office", "452001", "Head Post Office", "Delivery", "Indore", "Indore Division", "Indore", "Indore Region", "Madhya Pradesh", "MP Circle"),
        ("Surat Head Office", "395001", "Head Post Office", "Delivery", "Surat", "Surat Division", "Surat", "Vadodara Region", "Gujarat", "Gujarat Circle"),
        ("Ludhiana Head Office", "141001", "Head Post Office", "Delivery", "Ludhiana", "Ludhiana Division", "Ludhiana", "Punjab Region", "Punjab", "Punjab Circle"),
        ("Amritsar Head Office", "143001", "Head Post Office", "Delivery", "Amritsar", "Amritsar Division", "Amritsar", "Punjab Region", "Punjab", "Punjab Circle"),
        ("Agra Head Office", "282001", "Head Post Office", "Delivery", "Agra", "Agra Division", "Agra", "Agra Region", "Uttar Pradesh", "UP Circle"),
        ("Varanasi Head Office", "221001", "Head Post Office", "Delivery", "Varanasi", "Varanasi Division", "Varanasi", "Varanasi Region", "Uttar Pradesh", "UP Circle"),
        ("Nagpur GPO", "440001", "Head Post Office", "Delivery", "Nagpur", "Nagpur City", "Nagpur", "Nagpur Region", "Maharashtra", "Maharashtra Circle"),
        ("Kanpur Head Office", "208001", "Head Post Office", "Delivery", "Kanpur", "Kanpur Division", "Kanpur Nagar", "Kanpur Region", "Uttar Pradesh", "UP Circle")
    ]

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["office_name", "pincode", "office_type", "delivery_status", "taluk", "division", "district", "region", "state", "circle"])
        for rec in default_records:
            writer.writerow(rec)

    print(f"[+] Default PIN Code dataset updated with {len(default_records)} records.")

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
            taluk = norm_row.get("taluk", norm_row.get("tehsil", norm_row.get("block", norm_row.get("district", ""))))
            division = norm_row.get("division", norm_row.get("divisionname", norm_row.get("postal_division", "")))
            district = norm_row.get("district", norm_row.get("districtname", norm_row.get("city", "")))
            region = norm_row.get("region", norm_row.get("regionname", norm_row.get("postal_region", "Postal Region")))
            state = norm_row.get("state", norm_row.get("statename", norm_row.get("state_name", "")))
            circle = norm_row.get("circle", norm_row.get("circlename", norm_row.get("circle_name", "")))

            if pincode and office_name:
                rows_to_insert.append((pincode, office_name, office_type, delivery_status, taluk, division, district, region, state, circle))

        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS pincodes;")
        create_table_and_indexes(conn)
        
        batch_size = 5000
        total_inserted = 0
        for i in range(0, len(rows_to_insert), batch_size):
            batch = rows_to_insert[i:i + batch_size]
            cursor.executemany("""
            INSERT INTO pincodes (pincode, office_name, office_type, delivery_status, taluk, division, district, region, state, circle)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
