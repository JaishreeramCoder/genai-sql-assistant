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
        "sqlitecloud://cbwb6jhxhk.g1.sqlite.cloud:8860/user_info?apikey=tzKSY69TJgit4JxRZqGYxSSSXXn5EWfmoYezjolRdn8"
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
            "https://dashboard.sqlitecloud.io/organizations/aibej2uhk/projects/cbwb6jhxhk/studio?database=user_info"
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
            buffer = io.BytesIO(file_bytes)

            # Count total rows (excluding header)
            total_rows = sum(1 for _ in io.TextIOWrapper(io.BytesIO(file_bytes), encoding="utf-8")) - 1
            buffer.seek(0)

            # Progress bar + status
            progress = st.progress(0, text=f"Uploading {file.name}...")
            status = st.empty()

            with get_connection() as conn:
                cur = conn.cursor()

                # Create table from header
                buffer.seek(0)
                reader = csv.reader(io.TextIOWrapper(buffer, encoding="utf-8"))
                headers = next(reader)
                cols = ", ".join(f'"{h.strip()}" TEXT' for h in headers)
                cur.execute(f"DROP TABLE IF EXISTS {base_name}")
                cur.execute(f"CREATE TABLE {base_name} ({cols})")
                conn.commit()

                uploaded = 0
                batch = []

                # Stream rows
                for row in reader:
                    batch.append(row)
                    if len(batch) >= CHUNK_SIZE:
                        placeholders = ", ".join("?" * len(headers))
                        cur.executemany(
                            f"INSERT INTO {base_name} VALUES ({placeholders})", batch
                        )
                        conn.commit()
                        uploaded += len(batch)
                        batch.clear()

                        percent = int(uploaded / total_rows * 100)
                        progress.progress(percent, text=f"{file.name}: {percent}% uploaded")
                        status.text(f"{uploaded}/{total_rows} rows uploaded")

                # Insert any leftovers
                if batch:
                    placeholders = ", ".join("?" * len(headers))
                    cur.executemany(
                        f"INSERT INTO {base_name} VALUES ({placeholders})", batch
                    )
                    conn.commit()
                    uploaded += len(batch)

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

        with col2:
            if st.button("❌ Delete Table"):
                with get_connection() as conn:
                    conn.execute(f"DROP TABLE IF EXISTS {selected_table};")
                    conn.commit()
                st.warning(f"Table `{selected_table}` has been deleted!")
                st.rerun()
