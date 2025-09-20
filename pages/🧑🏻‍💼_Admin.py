import os
import streamlit as st
import pandas as pd
import altair as alt
import io
from github import Github
import base64
import re
from github import Github, Auth
# Page config
st.set_page_config(page_title="🔐 Admin Portal", layout="wide")
st.title("🔐 College Admin Panel")
st.markdown("---")

# --- Session State for Login ---
if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

# --- Required template columns ---
REQUIRED_COLS = ['CGPA', 'Package', 'Company', 'Branch', 'Internship', 'Year', 'Skills']

# --- Template Excel file creation ---
TEMPLATE_FILE = "placement_template.xlsx"
if not os.path.exists(TEMPLATE_FILE):
    pd.DataFrame(columns=REQUIRED_COLS).to_excel(TEMPLATE_FILE, index=False)

# --- GitHub connection setup ---
token = st.secrets["github"]["token"]
repo_url = st.secrets["github"]["repo_url"]
token = st.secrets["github"]["token"]
g = Github(auth=Auth.Token(token))
match = re.search(r"github\.com/([^/]+)/([^.]+)", repo_url)
owner = match.group(1)
repo_name = match.group(2)
repo = g.get_repo(f"{owner}/{repo_name}")

def upload_file(file_path, file_content, commit_message="Update placement data"):
    try:
        contents = repo.get_contents(file_path)
        repo.update_file(contents.path, commit_message, file_content, contents.sha)
    except:
        repo.create_file(file_path, commit_message, file_content)

def read_file(file_path):
    try:
        contents = repo.get_contents(file_path)
        file_content = base64.b64decode(contents.content).decode("utf-8")
        return file_content
    except:
        return None

# --- Login Page ---
if not st.session_state.admin_logged_in:
    college_code = st.text_input("College Code")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        admins = st.secrets["COLLEGE_CODES"]

        if college_code in admins:
            stored = admins[college_code]
            stored_username, stored_password = stored.split(":")
            if username == stored_username and password == stored_password:
                st.session_state.admin_logged_in = True
                st.session_state.college_code = college_code
                st.session_state.admin_user = username
                st.success(f"✅ Login successful! Welcome {username} from {college_code}.")
                st.rerun()
            else:
                st.error("❌ Invalid username or password.")
        else:
            st.error("❌ Invalid college code.")

# --- Admin Dashboard ---
else:
    st.sidebar.button("Logout", on_click=lambda: st.session_state.update({"admin_logged_in": False}))

    college_code = st.session_state.college_code
    username = st.session_state.admin_user
    data_file_csv = f"placement_data_{college_code}.csv"
    data_file_xlsx = f"placement_data_{college_code}.xlsx"

    st.markdown("""
    ### 📂 Placement Data Upload Instructions

    1. **Download the official template** from the link below **before** entering any data.

    2. **Do not change** the column names or their order.

    3. Keep the file format as `.xlsx` or `.csv`.
    """, unsafe_allow_html=True)

    # Template download
    with open(TEMPLATE_FILE, "rb") as f:
        st.download_button(
            "📥 Download Placement Data Template (Excel)",
            f,
            file_name="placement_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # File existence check on GitHub
    file_content_csv = read_file(data_file_csv)
    file_content_xlsx = read_file(data_file_xlsx)

    if file_content_csv or file_content_xlsx:
        if file_content_csv:
            df = pd.read_csv(io.StringIO(file_content_csv))
        else:
            df = pd.read_excel(io.BytesIO(base64.b64decode(read_file(data_file_xlsx).encode())))

        df.columns = df.columns.str.strip()
        st.session_state[f'placement_df_{college_code}'] = df

        st.markdown(f"### ✅ Using Saved Placement Data for {username} ({college_code})")
        st.dataframe(df.head(10), use_container_width=True)

        if st.button("🗑️ Delete File"):
            try:
                if file_content_csv:
                    contents = repo.get_contents(data_file_csv)
                    repo.delete_file(contents.path, "Delete placement data", contents.sha)
                if file_content_xlsx:
                    contents = repo.get_contents(data_file_xlsx)
                    repo.delete_file(contents.path, "Delete placement data", contents.sha)
                st.session_state.pop(f'placement_df_{college_code}', None)
                st.warning("File deleted. Please upload a new file.")
                st.rerun()
            except Exception as e:
                st.error(f"Error deleting file: {e}")

    else:
        uploaded_file = st.file_uploader("Upload Placement Data (.csv or .xlsx)", type=["csv", "xlsx"])

        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                    file_content = df.to_csv(index=False)
                    upload_file(data_file_csv, file_content)
                else:
                    df = pd.read_excel(uploaded_file)
                    buffer = io.BytesIO()
                    df.to_excel(buffer, index=False)
                    file_content = base64.b64encode(buffer.getvalue()).decode()
                    upload_file(data_file_xlsx, file_content)

                df.columns = df.columns.str.strip()
                missing_cols = [col for col in REQUIRED_COLS if col not in df.columns]

                if missing_cols:
                    st.error(f"❌ Missing required columns: {', '.join(missing_cols)}")
                    st.stop()
                else:
                    df = df[REQUIRED_COLS]
                    st.session_state[f'placement_df_{college_code}'] = df
                    st.success("✅ File validated, extra columns ignored, and saved successfully!")
                    st.rerun()
            except Exception as e:
                st.error(f"Error reading file: {e}")
            st.stop()

    # Show insights if data is available
    if f'placement_df_{college_code}' in st.session_state:
        df = st.session_state[f'placement_df_{college_code}']

        required_cols = ['CGPA', 'Package', 'Company', 'Branch', 'Internship', 'Year']
        missing_cols = [col for col in required_cols if col not in df.columns]

        if not missing_cols:
            st.markdown("## 📊 Visual Insights")
            st.markdown("---")

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### CGPA vs Package")
                st.scatter_chart(df, x="CGPA", y="Package", color="Branch")

            with col2:
                st.markdown("### Top Hiring Companies")
                top_companies = df['Company'].value_counts().head(5)
                st.bar_chart(top_companies)

            col3, col4 = st.columns(2)
            with col3:
                st.markdown("### Internship Impact on Package")
                box_plot = alt.Chart(df).mark_boxplot().encode(
                    x="Internship:N",
                    y="Package:Q"
                )
                st.altair_chart(box_plot, use_container_width=True)

            with col4:
                st.markdown("### Branch-wise Avg Package")
                st.bar_chart(df.groupby('Branch')['Package'].mean())

            col5, col6 = st.columns(2)
            with col5:
                st.markdown("### Year-wise Placement Count")

                if 'Year' in df.columns:
                    placement_data = df.groupby('Year').size().reset_index(name='Count')
                    placement_data = placement_data.sort_values(by='Year')

                    chart = alt.Chart(placement_data).mark_line(point=True).encode(
                        x=alt.X('Year:O', title='Year'),
                        y=alt.Y('Count:Q', title='Number of Students Placed'),
                        tooltip=['Year', 'Count']
                    ).properties(
                        width=400,
                        height=300,
                        title="Year-wise Placement Count"
                    )

                    st.altair_chart(chart, use_container_width=True)
                else:
                    st.warning("⚠️ 'Year' column missing from data. Cannot display placement trend.")
        else:
            st.error(f"Missing required columns: {', '.join(missing_cols)}")
            st.code(", ".join(required_cols))
    else:
        st.info("Please upload a file to begin analysis.")
