import streamlit as st
from google import genai
import re
import mysql.connector
from mysql.connector import Error
from config import API_KEY, MODEL_ID


st.set_page_config(page_title="DB Design Assistant", layout="wide")

st.title("🤖 AI Powered Database Designer (MySQL)")
st.markdown(f"Using Model: `{MODEL_ID}`")


def generate_text(prompt: str) -> str:
    if not API_KEY:
        raise RuntimeError("GEMINI_API_KEY is missing. Add it to the project's .env file.")
    client = genai.Client(api_key=API_KEY)
    response = client.models.generate_content(model=MODEL_ID, contents=prompt)
    if not response.text:
        raise RuntimeError("The model returned an empty response.")
    return response.text

# ================== STAGE 1: PROJECT DEFINITION ==================
st.header("1. Project Definition")

col1, col2 = st.columns(2)

with col1:
    domain = st.text_input("Domain", placeholder="E-commerce (customers, orders, payments, shipments)")
    primary_entity = st.text_input("Primary Entity Focus", placeholder="Payments")
    constraints = st.text_area("Constraint / Rule", height=100, placeholder="Enforce unique customer email")
    advanced_features = st.text_area("Advanced Feature", height=100, placeholder="Trigger: decrement inventory on OrderItems insert; increment on Return approval")

with col2:
    security = st.text_area("Security / Access Control", height=100, placeholder="Cashiers can record payments but cannot modify inventory")
    reporting = st.text_area("Reporting Requirement", height=100, placeholder="Abandoned carts and conversion rate")
    common_tasks = st.text_area("Common Tasks", height=100, placeholder="Create an ERD, design a relational schema with keys & constraints, write SQL DDL/DML, implement the business rule (constraint/trigger/proc), apply the advanced feature, configure role-based security, and generate the required report.")

# ================== STAGE 2 ==================
if st.button("Stage 2 – Extract Business Rules"):
    try:
        prompt = f"""
        You are a database design expert. Extract BUSINESS RULES from:
        Domain: {domain} | Entity: {primary_entity} | Constraints: {constraints}
        Features: {advanced_features} | Security: {security} | Reporting: {reporting}
        Tasks: {common_tasks}
        
        OUTPUT: Markdown table (BR-ID, Type, Rule Statement, Component, Tip).
        """
        with st.spinner("Analyzing requirements..."):
            st.session_state["br"] = generate_text(prompt)
    except Exception as e: st.error(f"API Error: {e}")

if "br" in st.session_state:
    st.subheader("Stage 2 – Business Rules")
    st.markdown(st.session_state["br"])

# ================== STAGE 3 & 4 ==================
if "br" in st.session_state:
    if st.button("Stage 3 & 4 – Table Design"):
        try:
            prompt = f"""
            Based on rules: {st.session_state["br"]}
            1. Define tables/attributes (Stage 3)
            2. Identify missing rules (Stage 4)
            OUTPUT: Markdown sections.
            """
            with st.spinner("Designing tables..."):
                st.session_state["tables"] = generate_text(prompt)
        except Exception as e: st.error(f"API Error: {e}")

if "tables" in st.session_state:
    st.subheader("Stage 3 & 4 – Tables")
    st.markdown(st.session_state["tables"])

# ================== STAGE 5 ==================
if "tables" in st.session_state:
    if st.button("Stage 5 – Normalization"):
        try:
            prompt = f"Normalize these tables 0NF->3NF:\n{st.session_state['tables']}"
            with st.spinner("Normalizing..."):
                st.session_state["norm"] = generate_text(prompt)
        except Exception as e: st.error(f"API Error: {e}")

if "norm" in st.session_state:
    st.subheader("Stage 5 – Normalization")
    st.markdown(st.session_state["norm"])

# ================== STAGE 6: ER DIAGRAM (VISUAL) ==================
# Burayı ayırdık ve Graphviz görselleştirme ekledik
if "norm" in st.session_state:
    st.divider()
    st.header("Stage 6: Visual ER Diagram")
    
    if st.button("Generate ER Diagram (Visual)"):
        try:
            
            # Graphviz (DOT) Kodu İsteyen Prompt
            prompt = f"""
            You are a Data Architect. Based on the normalized schema below, generate a Graphviz DOT script.
            
            SCHEMA:
            {st.session_state["norm"]}
            
            INSTRUCTIONS:
            1. Use 'digraph G' syntax.
            2. Use 'node [shape=record]' for tables.
            3. Inside the record label, list columns with PK/FK markers.
            4. Draw relationships (edges) between tables correctly (1 to n).
            5. Return ONLY the DOT code inside a ```dot block. Do not add explanations.
            """
            
            with st.spinner("Drawing ER Diagram..."):
                response_text = generate_text(prompt)
                
                # Regex ile DOT kodunu ayıkla
                dot_match = re.search(r"```dot(.*?)```", response_text, re.DOTALL)
                if dot_match:
                    st.session_state["er_dot"] = dot_match.group(1).strip()
                else:
                    # Bazen sadece kodu yazar, blok koymazsa diye:
                    st.session_state["er_dot"] = response_text.replace("```dot", "").replace("```", "")
                    
        except Exception as e:
            st.error(f"API Error: {e}")

    # Eğer hafızada DOT kodu varsa çiz
    if "er_dot" in st.session_state:
        try:
            st.graphviz_chart(st.session_state["er_dot"])
            st.caption("Auto-generated ER Diagram using Graphviz")
        except Exception as e:
            st.error(f"Visual render error (Graphviz syntax might be wrong): {e}")
            st.code(st.session_state["er_dot"]) # Hata varsa kodu göster ki inceleyelim

# ================== STAGE 7: SQL & DEPLOY ==================
if "er_dot" in st.session_state: # Stage 6 bittikten sonra açılır
    st.divider()
    st.header("Stage 7: SQL Scripts & Deployment")
    
    if st.button("Generate SQL Scripts (MySQL)"):
        try:

            prompt = f"""
            You are a MySQL 8 database expert.
            
            CONTEXT:
            Tables: {st.session_state["tables"]}
            Normalization: {st.session_state["norm"]}

            TASKS:
            Generate a COMPLETE SQL Script for MySQL 8.
            
            CRITICAL OUTPUT RULES:
            1. Place `/* --- SEPARATOR --- */` after EVERY command (Table, Insert, Trigger, View).
            2. NO `DELIMITER //`.
            3. Standard CREATE TRIGGER syntax.
            4. Include 3 complex SELECT queries at the end.
            
            OUTPUT:
            Put all code in ONE ```sql``` block.
            """

            with st.spinner("Writing SQL Codes..."):
                st.session_state["final_sql"] = generate_text(prompt)
        
        except Exception as e:
            st.error(f"API Error: {e}")

if "final_sql" in st.session_state:
    st.markdown(st.session_state["final_sql"])

    # --- CLEAN & DOWNLOAD ---
    sql_blocks = re.findall(r"```sql(.*?)```", st.session_state["final_sql"], re.DOTALL)
    full_sql = "\n".join(block.strip() for block in sql_blocks)
    clean_file_sql = full_sql.replace("/* --- SEPARATOR --- */", "")

    st.download_button("Download SQL", clean_file_sql, "db_schema.sql", "text/plain")

    # --- DEPLOY TO XAMPP ---
    st.subheader("🚀 Deploy to XAMPP")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        db_name = st.text_input("Database Name", "stage6_test_db")
    with col_d2:
        st.write("")
        st.write("")
        if st.button("Deploy Database"):
            if not full_sql:
                st.error("No SQL code found.")
            else:
                try:
                    conn = mysql.connector.connect(host="localhost", user="root", password="")
                    if conn.is_connected():
                        cursor = conn.cursor(buffered=True)
                        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
                        conn.database = db_name
                        
                        # Komutları ayraç ile böl
                        commands = full_sql.split("/* --- SEPARATOR --- */")
                        
                        my_bar = st.progress(0, text="Deploying...")
                        total = len(commands)
                        
                        for i, cmd in enumerate(commands):
                            stmt = cmd.strip()
                            if stmt:
                                try:
                                    cursor.execute(stmt)
                                    if cursor.with_rows: cursor.fetchall()
                                    while cursor.nextset(): pass
                                except Error as e:
                                    st.warning(f"⚠️ Skipped: {str(e)[:100]}")
                            
                            if total > 0: my_bar.progress(min((i+1)/total, 1.0))
                        
                        conn.commit()
                        cursor.close()
                        conn.close()
                        st.success(f"✅ Deployment to `{db_name}` Successful!")
                except Error as e:
                    st.error(f"Connection Error: {e}")
