import pandas as pd
import streamlit as st
import os
import sqlitecloud  # Use sqlitecloud instead of sqlite3

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
            "https://dashboard.sqlitecloud.io/organizations/aibej2uhk/projects/cbwb6jhxhk/studio?database=uploaded_db.sqlite"
        )

    st.subheader("📂 Upload Files to SQLite Cloud Database")

    # -------------------------
    # Connect to SQLite Cloud
    # -------------------------
    conn = sqlitecloud.connect(
        "sqlitecloud://cbwb6jhxhk.g1.sqlite.cloud:8860/uploaded_db.sqlite?apikey=tzKSY69TJgit4JxRZqGYxSSSXXn5EWfmoYezjolRdn8"
    )

    # -------------------------
    # Upload CSV/Excel files
    # -------------------------
    uploaded_files = st.file_uploader(
        "Upload CSV or Excel files",
        type=["csv", "xlsx", "xls"],
        accept_multiple_files=True
    )

    if uploaded_files:
        for file in uploaded_files:
            base_name = os.path.splitext(file.name)[0].strip().replace(" ", "_")

            if file.name.endswith(".csv"):
                df = pd.read_csv(file)
                df.to_sql(base_name, conn, if_exists="replace", index=False)
                st.success(f"✅ Uploaded `{file.name}` as table `{base_name}`")
            else:  # Excel → loop through all sheets
                xls = pd.ExcelFile(file)
                for sheet in xls.sheet_names:
                    df = pd.read_excel(file, sheet_name=sheet)
                    table_name = f"{base_name}_{sheet}".strip().replace(" ", "_")
                    df.to_sql(table_name, conn, if_exists="replace", index=False)
                    st.success(f"✅ Uploaded `{file.name}` (sheet: {sheet}) as table `{table_name}`")

    # -------------------------
    # Fetch Tables Function
    # -------------------------
    def fetch_tables():
        return pd.read_sql(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';",
            conn
        )

    # -------------------------
    # Display Tables
    # -------------------------
    tables = fetch_tables()
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
                df = pd.read_sql(f"SELECT * FROM {selected_table};", conn)
                st.subheader(f"Contents of `{selected_table}`")
                st.dataframe(df, use_container_width=True)

        with col2:
            if st.button("❌ Delete Table"):
                conn.execute(f"DROP TABLE IF EXISTS {selected_table};")
                conn.commit()
                st.warning(f"Table `{selected_table}` has been deleted!")
                st.rerun()

    conn.close()
