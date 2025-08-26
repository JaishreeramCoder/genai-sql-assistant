# 📊 GenAI SQL Assistant

## 📌 Overview

This project is an **interactive dashboard** built with **Streamlit** that allows:

* **Admins** to manage database tables (upload, delete, update).
* **Users** to query and filter data dynamically with SQL or text instructions.
* **Visualization** of tables and datasets stored in the database.

The app is powered by **SQLite (local or cloud)** and keeps both the admin and user views synchronized in real-time.

---

## 🚀 Features

### 🔑 Admin Panel (`admin.py`)

* Password-protected access
* Upload CSV/Excel files → automatically stored as database tables
* View and delete tables dynamically
* One-click access to the **SQLite Cloud dashboard**
* Ensures **real-time sync** with the user and visualization sections

### 👥 User Panel (`user.py`)

* Enter natural language or raw **SQL queries** to fetch data
* View query results in tabular format
* Built-in **query history tracking** to revisit past searches
* Filter and refine tables interactively

### 📈 Visualization Panel (`visualize.py`)

* Overview of all tables in the database
* Explore schema and table contents
* Visual data exploration for better insights

---

## 🔧 Installation

1. **Clone the repository**

```bash
git clone https://github.com/Ishu2002k/Streamlit.git
```

2. **Create virtual environment (recommended)**

```bash
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate.bat      # Windows Command Prompt
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

---

## ▶️ Usage

### Run Admin Panel from the `src` folder

streamlit run app.py

---

## ⚡ Database

* By default, the app uses **`uploaded_db.sqlite`** stored in the project folder.
* To connect to a **SQLite Cloud database**, update the connection string in `admin.py`, `user.py`, and `visualize.py`:

```python
import sqlitecloud
conn = sqlitecloud.connect(
    "sqlitecloud://<project-id>.g1.sqlite.cloud:8860/uploaded_db.sqlite?apikey=<your-api-key>"
)
```
