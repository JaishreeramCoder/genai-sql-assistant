import pandas as pd
import streamlit as st
import os
import sqlitecloud  # Use sqlitecloud instead of sqlite3
import io
import csv

# -------------------------
# Connection Helper
# -------------------------
def get_connection():
    return sqlitecloud.connect(
        "sqlitecloud://cltnsqbxhz.g2.sqlite.cloud:8860/uploaded_db.sqlite?apikey=sAxlghIjO7aOpDdaLQgSIPrvemFEyBrv5Mh3cKutPNs"
    )


def admin_panel():
    st.title("🔐 Admin Panel")

    # -------------------------
    # Password Protection
    # -------------------------
    PASSWORD = "admin_123"

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.subheader("Login Required")
        password_input = st.text_input("Enter password:", type="password")
        if st.button("Login"):
            if password_input == PASSWORD:
                st.session_state.authenticated = True
                st.success("✅ Logged in successfully!")
                st.rerun()
            else:
                st.error("❌ Wrong password. Try again.")
        return

    # -------------------------
    # Logout and Open in Cloud buttons row
    # -------------------------
    col_left, col_spacer, col_right = st.columns([15, 10, 8])

    with col_left:
        if st.button("🔓 Logout"):
            st.session_state.authenticated = False
            st.rerun()

   
    with col_right:
        st.link_button(
            "🌐 Open in SQLite Cloud",
            "https://dashboard.sqlitecloud.io/organizations/j5hy3buhz/projects/cltnsqbxhz/studio?database=uploaded_db.sqlite"
        )


    st.subheader("📂 Upload CSV Files to SQLite Cloud Database")

    # -------------------------
    # Upload CSV files only
    # -------------------------
    uploaded_files = st.file_uploader(
        "Upload CSV files",
        type=["csv"],
        accept_multiple_files=True
    )
    CHUNK_SIZE = 500  # Number of rows to insert per batch

    if uploaded_files:
        for file in uploaded_files:
            base_name = os.path.splitext(file.name)[0].strip().replace(" ", "_")

            # Read file bytes into buffer
            file_bytes = file.read()
            # --- Changed: decode bytes once and use StringIO to avoid TextIOWrapper closing issues ---
            text = file_bytes.decode("utf-8", errors="replace")

            # Count total rows (excluding header)
            total_rows = sum(1 for _ in io.StringIO(text)) - 1

            # Progress bar + status
            progress = st.progress(0, text=f"Uploading {file.name}...")
            status = st.empty()

            with get_connection() as conn:
                cur = conn.cursor()

                # -------------------------
                # Infer dtypes & create table with inferred SQLite types (with dd-mm-yyyy support)
                # -------------------------
                # Sample the CSV with pandas to infer column characteristics (uses up to nrows sample)
                try:
                    sample_df = pd.read_csv(io.StringIO(text), encoding="utf-8", nrows=1000)
                except Exception:
                    # Fallback: empty DataFrame if pandas can't parse sample
                    sample_df = pd.DataFrame()

                # Normalize sample columns (strip spaces)
                if not sample_df.empty:
                    sample_df.columns = [str(c).strip() for c in sample_df.columns]

                # Read headers from raw CSV to preserve exact ordering and names (raw from csv.reader)
                reader = csv.reader(io.StringIO(text))
                raw_headers = next(reader)
                # canonical header names (stripped) we'll use for table creation and row-ordering
                headers = [h.strip() for h in raw_headers]

                # --- helper: detect whether a series is mostly date-parsable with dayfirst ---
                def is_date_like(series, min_fraction=0.6):
                    ser = series.dropna().astype(str)
                    if ser.empty:
                        return False
                    parsed = pd.to_datetime(ser, dayfirst=True, errors="coerce")
                    frac = parsed.notna().sum() / len(ser)
                    return frac >= min_fraction

                # Build a simple marker-based dtype map for each header (keyed by stripped header):
                # markers: "int", "float", "datetime", "text"
                dtypes = {}
                for h in headers:
                    if not sample_df.empty and h in sample_df.columns:
                        col = sample_df[h]
                        # First try date-detection (useful for dd-mm-yyyy)
                        try:
                            if is_date_like(col):
                                dtypes[h] = "datetime"
                                continue
                        except Exception:
                            pass

                        # Use pandas' dtype checks
                        try:
                            if pd.api.types.is_integer_dtype(col):
                                dtypes[h] = "int"
                                continue
                            if pd.api.types.is_float_dtype(col):
                                dtypes[h] = "float"
                                continue
                        except Exception:
                            pass

                        # If pandas kept it object, try coercion to numeric
                        coerced = pd.to_numeric(col.dropna().astype(str), errors="coerce")
                        if not coerced.empty and coerced.notna().sum() == len(col.dropna()):
                            # all non-null values are numeric
                            # choose int if values are all integral; else float
                            if (coerced.dropna() % 1 == 0).all():
                                dtypes[h] = "int"
                            else:
                                dtypes[h] = "float"
                        else:
                            dtypes[h] = "text"
                    else:
                        dtypes[h] = "text"  # fallback if header not present in sample

                # Map markers to SQLite affinity/type for CREATE TABLE
                def sqlite_type_from_marker(marker):
                    if marker == "int":
                        return "INTEGER"
                    if marker == "float":
                        return "REAL"
                    if marker == "datetime":
                        # TIMESTAMP is fine — SQLite treats it as TEXT affinity
                        return "TIMESTAMP"
                    return "TEXT"

                cols_def = ", ".join(
                    f'"{h}" {sqlite_type_from_marker(dtypes.get(h))}' for h in headers
                )

                # Drop/create table (quote table name)
                cur.execute(f'DROP TABLE IF EXISTS "{base_name}"')
                cur.execute(f'CREATE TABLE "{base_name}" ({cols_def})')
                conn.commit()

                # Helper to convert CSV string cell -> Python value according to marker
                def convert_cell(val, marker):
                    if val is None:
                        return None
                    s = str(val).strip()
                    if s == "":
                        return None
                    try:
                        if marker == "int":
                            # handle "1.0" -> 1
                            return int(float(s))
                        if marker == "float":
                            return float(s)
                        if marker == "datetime":
                            # parse with dayfirst to support dd-mm-yyyy and dd-mm-yyyy HH:MM:SS
                            dt = pd.to_datetime(s, dayfirst=True, errors="coerce")
                            if pd.isna(dt):
                                # fallback to raw string if parse fails
                                return s
                            # Adaptive formatting:
                            # if time portion is exactly 00:00:00 (no explicit time in input), store date-only
                            t = dt.time()
                            if t.hour == 0 and t.minute == 0 and t.second == 0 and (" " not in s and "T" not in s):
                                # original string probably had no time; keep date-only
                                return dt.date().isoformat()
                            # otherwise store full timestamp (YYYY-MM-DD HH:MM:SS)
                            return dt.strftime("%Y-%m-%d %H:%M:%S")
                        # default: text
                        return s
                    except Exception:
                        # fallback to raw string if conversion fails
                        return s

                # -------------------------
                # Read entire CSV with pandas for robust parsing/alignment, then insert in chunks
                # -------------------------
                try:
                    full_df = pd.read_csv(io.StringIO(text), encoding="utf-8", dtype=str)
                except Exception:
                    # Fallback: try pandas with more relaxed options
                    full_df = pd.read_csv(io.StringIO(text), encoding="utf-8", dtype=str, engine="python")

                # Normalize columns and ensure ordering matches 'headers'
                full_df.columns = [str(c).strip() for c in full_df.columns]

                # Ensure all expected headers present; if missing, add as empty columns
                for h in headers:
                    if h not in full_df.columns:
                        full_df[h] = None

                # Reorder to match CSV header order (headers is stripped names)
                full_df = full_df[headers]

                # Insert rows in chunks, converting each cell according to dtypes[header]
                uploaded = 0
                nrows = len(full_df)
                for start in range(0, nrows, CHUNK_SIZE):
                    chunk = full_df.iloc[start:start + CHUNK_SIZE]
                    batch = []
                    for _, row in chunk.iterrows():
                        converted_row = [
                            convert_cell(row[h], dtypes.get(h)) for h in headers
                        ]
                        batch.append(converted_row)

                    if batch:
                        placeholders = ", ".join("?" * len(headers))
                        cur.executemany(
                            f'INSERT INTO "{base_name}" VALUES ({placeholders})', batch
                        )
                        conn.commit()
                        uploaded += len(batch)

                        percent = int(uploaded / max(total_rows, 1) * 100)
                        progress.progress(percent, text=f"{file.name}: {percent}% uploaded")
                        status.text(f"{uploaded}/{total_rows} rows uploaded")

                progress.progress(100, text=f"✅ {file.name} upload complete")
                status.text(f"Finished uploading {uploaded} rows")


    # -------------------------
    # Fetch Tables Function
    # -------------------------
    def fetch_tables():
        with get_connection() as conn:
            tables = pd.read_sql(
                "SELECT name FROM sqlite_master WHERE type='table';",
                conn
            )
        # Filter out system/AI tables
        return tables[~tables["name"].str.startswith(("sqlite_", "_sqliteai_"))]

    # -------------------------
    # Display Tables
    # -------------------------
    tables = fetch_tables()
    tables.index = range(1, len(tables)+1)
    st.subheader("📋 Tables in Database")
    st.dataframe(tables, use_container_width=True)

    # -------------------------
    # Table Actions
    # -------------------------
    if not tables.empty:
        selected_table = st.selectbox("Select a table", tables["name"])
        col1, col2 = st.columns([6, 3])

        with col1:
            if st.button("🔍 View Table Data"):
                with get_connection() as conn:
                    df = pd.read_sql(f"SELECT * FROM {selected_table};", conn)
                st.subheader(f"Contents of `{selected_table}`")
                st.dataframe(df, use_container_width=True)

        # Define the dialog once
        @st.dialog("⚠️ Confirm Delete")
        def confirm_delete_dialog(table_name):
            st.warning(f"Are you sure you want to delete the table `{table_name}`? This action cannot be undone.")
            
            col1, col2 = st.columns(2)
            if col1.button("✅ Yes — delete", key="confirm_delete"):
                with get_connection() as conn:
                    conn.execute(f'DROP TABLE IF EXISTS "{table_name}";')
                    conn.commit()
                st.success(f"Table `{table_name}` has been deleted!")
                st.rerun()

            if col2.button("❌ Cancel", key="cancel_delete"):
                st.info("Delete action cancelled.")
                st.rerun()


        # Trigger dialog on button click
        with col2:
            if st.button("❌ Delete Table"):
                confirm_delete_dialog(selected_table)
