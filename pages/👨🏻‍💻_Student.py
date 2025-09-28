# Imports
from github import Github, Auth
import streamlit as st
import pandas as pd
import io
import base64
import re
import PyPDF2
from rapidfuzz import fuzz
import altair as alt
from streamlit_option_menu import option_menu
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from PIL import Image, ImageDraw
from sklearn.linear_model import LogisticRegression

# Page configuration
st.set_page_config(page_title="📊 Student Insights", layout="wide")
st.title("📊 Student Section")
st.markdown("---")

# Initialize session state for college code
if "student_college_code" not in st.session_state:
    st.session_state.student_college_code = None

# GitHub setup
token = st.secrets["github"]["token"]
repo_url = st.secrets["github"]["repo_url"]
g = Github(auth=Auth.Token(token))

# Extract owner and repo name from repo URL
match = re.search(r"github\.com/([^/]+)/([^.]+)", repo_url)
owner, repo_name = match.group(1), match.group(2)
repo = g.get_repo(f"{owner}/{repo_name}")

# Function to read file from GitHub
def read_file(file_path):
    try:
        contents = repo.get_contents(file_path)
        return base64.b64decode(contents.content)
    except:
        return None

# College Code Login
if st.session_state.student_college_code is None:
    college_code = st.text_input("Enter your College Code", max_chars=10)
    if st.button("Login"):
        data_file_csv = f"placement_data_{college_code}.csv"
        data_file_xlsx = f"placement_data_{college_code}.xlsx"

        file_csv = read_file(data_file_csv)
        file_xlsx = read_file(data_file_xlsx)

        if file_csv or file_xlsx:
            st.session_state.student_college_code = college_code
            st.success("✅ Login successful!")
            st.rerun()
        else:
            st.error("❌ Invalid College Code or data file not found.")
    st.stop()

college_code = st.session_state.student_college_code
st.markdown(f"Logged in with College Code: **{college_code}**")
if st.button("Logout"):
    st.session_state.student_college_code = None
    st.rerun()

# Load placement data
data_file_csv = f"placement_data_{college_code}.csv"
data_file_xlsx = f"placement_data_{college_code}.xlsx"

df = None
file_csv = read_file(data_file_csv)
file_xlsx = read_file(data_file_xlsx)

if file_csv or file_xlsx:
    try:
        if file_csv:
            df = pd.read_csv(io.StringIO(file_csv.decode()))
        else:
            df = pd.read_excel(io.BytesIO(base64.b64decode(file_xlsx)))
        df.columns = df.columns.str.strip()
    except Exception as e:
        st.warning(f"⚠️ Failed to load placement data. Some insights may be unavailable. Error: {e}")
else:
    st.warning("⚠️ Placement data not found for your college.")

# Navigation menu
selected_section = option_menu(
    None,
    ["Placement Prediction", "Resume Analyzer", "Resume Builder", "College Insights"],
    icons=["bar-chart", "file-text", "book", "building"],
    orientation="horizontal",
    styles={
        "container": {"padding": "5px 0", "background-color": "transparent"},
        "icon": {"color": "#000000", "font-size": "16px"},
        "nav-link": {
            "font-size": "16px",
            "text-align": "center",
            "margin": "0px 0px",
            "padding": "4px 4px",
            "border-radius": "8px",
            "color": "#FFFFFF",
            "transition": "padding 0.4s ease-in-out",
        },
        "nav-link-selected": {"background-color": "rgb(255, 75, 75)", "color": "white"},
    },
)
st.markdown("---")

# Placement Prediction Section
if selected_section == "Placement Prediction":
    st.subheader("Placement Prediction")
    st.markdown("Enter your details to predict your placement chance:")

    with st.form("prediction_form"):
        cgpa_input = st.slider("CGPA", 0.0, 10.0, 7.0, step=0.1)
        skills_input = st.text_input("Skills (comma-separated)", placeholder="e.g. Python, SQL, Java")
        internship_input = st.radio("Internship Completed?", ["Yes", "No"])
        predict_button = st.form_submit_button("Predict")

    if predict_button:
        if df is not None and {'CGPA', 'Internship', 'Skills', 'Package'}.issubset(df.columns):
            # Prepare data
            df['InternshipEncoded'] = df['Internship'].apply(lambda x: 1 if x == 'Yes' else 0)
            df['Placed'] = df['Package'].apply(lambda x: 1 if x > 0 else 0)
            user_skills = [s.strip().lower() for s in skills_input.split(',') if s.strip()]
            df['SkillMatch'] = df['Skills'].fillna("").apply(
                lambda s: len(set(s.lower().split(', ')).intersection(user_skills))
            )

            X = df[['CGPA', 'InternshipEncoded', 'SkillMatch']]
            y = df['Placed']
            model = LogisticRegression()

            if len(y.unique()) >= 2:
                model.fit(X, y)
                user_input = pd.DataFrame([{
                    'CGPA': cgpa_input,
                    'InternshipEncoded': 1 if internship_input == "Yes" else 0,
                    'SkillMatch': len(user_skills)
                }])
                prediction = model.predict(user_input)[0]
                prob = model.predict_proba(user_input)[0][1] * 100
                if prediction == 1:
                    st.success(f"You have a high chance of getting placed! (Confidence: {prob:.2f}%)")
                else:
                    st.warning(f"Your placement chance is currently low. (Confidence: {prob:.2f}%)")
            else:
                st.info("⚠️ Not enough diverse placement data to train prediction model.")
        else:
            st.info("⚠️ Prediction model requires placement data. Only manual suggestions available.")

# Resume Analyzer Section
elif selected_section == "Resume Analyzer":
    st.subheader("Resume Analyzer")
    st.markdown("Upload your resume PDF to get improvement suggestions.")
    resume_file = st.file_uploader("Upload Resume (PDF)", type=["pdf"])

    if resume_file is not None:
        pdf_reader = PyPDF2.PdfReader(resume_file)
        resume_text = "".join(page.extract_text() for page in pdf_reader.pages)
        st.success("Resume uploaded and scanned.")

        resume_text = resume_text.lower()
        resume_words = re.findall(r'\b[a-z]{2,}\b', resume_text)

        if df is not None and "Skills" in df.columns and "Internship" in df.columns:
            # Top skills from placed students
            placed_df = df[df["Package"] > 0]
            skill_series = placed_df["Skills"].dropna().str.lower().str.split(",")
            all_skills = [skill.strip() for sublist in skill_series for skill in sublist]
            top_skills = dict(pd.Series(all_skills).value_counts().head(10))

            # Match skills
            matched_skills = [skill for skill in top_skills for word in resume_words if fuzz.ratio(skill, word) > 85]
            missing_skills = [skill for skill in top_skills if skill not in matched_skills]

            st.markdown("### Skills Found in Your Resume:")
            st.write(", ".join(matched_skills) if matched_skills else "None of the top skills found.")

            st.markdown("### Skills You May Add:")
            st.write(", ".join(missing_skills) if missing_skills else "You already have most top skills!")

            # Internship suggestion
            internship_important = placed_df["Internship"].value_counts().get("Yes", 0) > \
                                   placed_df["Internship"].value_counts().get("No", 0)
            if internship_important and "intern" not in resume_text:
                st.markdown("### Internship Suggestion:")
                st.info("Consider completing an internship to improve your placement chances.")
        else:
            st.info("⚠️ Resume scanned, but placement dataset missing. Skill gap analysis unavailable.")

# Resume Builder Section
elif selected_section == "Resume Builder":
    st.subheader("Resume Builder")
    st.markdown("Fill in your details to generate a professional PDF resume.")

    with st.form("resume_form"):
        name = st.text_input("Full Name")
        title = st.text_input("Title (e.g., Data Scientist)")
        about = st.text_area("About Me")
        email = st.text_input("Email")
        phone = st.text_input("Phone Number")
        address = st.text_input("Address")
        website = st.text_input("Website/Portfolio")
        profile_pic = st.file_uploader("Upload Profile Picture", type=["jpg", "png", "jpeg"])
        education = st.text_area("Education (e.g., B.Tech CSE, XYZ University, GPA 8.5)")
        skills = st.text_area("Skills (comma-separated)")
        experience = st.text_area("Work/Internship Experience")
        submit_resume = st.form_submit_button("Generate Resume PDF")

    if submit_resume:
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # Header
        c.setFillColorRGB(0.15, 0.15, 0.2)
        c.rect(0, height - 80, width, 80, fill=1)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 24)
        c.drawString(150, height - 50, name)
        c.setFont("Helvetica", 14)
        c.drawString(150, height - 65, title)

        # Profile picture
        if profile_pic is not None:
            img = Image.open(profile_pic).convert("RGB").resize((90, 90))
            mask = Image.new("L", img.size, 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, img.size[0], img.size[1]), fill=255)
            img.putalpha(mask)
            img_io = io.BytesIO()
            img.save(img_io, format="PNG")
            img_io.seek(0)
            c.drawImage(ImageReader(img_io), 40, height - 110, 90, 90, mask='auto')

        # Contact info
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, height - 140, "Contact")
        c.setFont("Helvetica", 11)
        c.drawString(40, height - 155, phone)
        c.drawString(40, height - 170, email)
        c.drawString(40, height - 185, address)
        c.drawString(40, height - 200, website)

        # Skills
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, height - 230, "Skills")
        c.setFont("Helvetica", 11)
        for i, skill in enumerate(skills.split(",")):
            c.drawString(40, height - 245 - (i * 15), skill.strip())

        # About Me
        c.setFont("Helvetica-Bold", 14)
        c.drawString(200, height - 140, "About Me")
        text_obj = c.beginText(200, height - 155)
        text_obj.setFont("Helvetica", 11)
        for line in about.split("\n"):
            text_obj.textLine(line)
        c.drawText(text_obj)

        # Education
        c.setFont("Helvetica-Bold", 14)
        c.drawString(200, height - 230, "Education")
        text_obj = c.beginText(200, height - 245)
        text_obj.setFont("Helvetica", 11)
        for line in education.split("\n"):
            text_obj.textLine(line)
        c.drawText(text_obj)

        # Experience
        c.setFont("Helvetica-Bold", 14)
        c.drawString(200, height - 320, "Experience")
        text_obj = c.beginText(200, height - 335)
        text_obj.setFont("Helvetica", 11)
        for line in experience.split("\n"):
            text_obj.textLine(line)
        c.drawText(text_obj)

        c.showPage()
        c.save()
        buffer.seek(0)

        st.success("✅ Resume Generated Successfully!")
        st.download_button(
            label="Download Resume",
            data=buffer,
            file_name="Styled_Resume.pdf",
            mime="application/pdf"
        )

# College Insights Section
elif selected_section == "College Insights":
    st.subheader("College Insights")

    if df is None:
        st.warning("⚠️ Placement data not available. Upload required to view insights.")
    else:
        branch_filter = st.selectbox("Filter by Branch", options=["All"] + sorted(df['Branch'].dropna().unique()))
        year_filter = st.selectbox("Filter by Year", options=["All"] + sorted(df['Year'].dropna().astype(str).unique()))

        filtered_df = df.copy()
        if branch_filter != "All":
            filtered_df = filtered_df[filtered_df['Branch'] == branch_filter]
        if year_filter != "All":
            filtered_df = filtered_df[filtered_df['Year'].astype(str) == year_filter]

        required_cols = ['CGPA', 'Package', 'Company', 'Branch', 'Internship', 'Year']
        if all(col in filtered_df.columns for col in required_cols):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### CGPA vs Package")
                st.scatter_chart(filtered_df, x='CGPA', y='Package', color='Branch')

            with col2:
                st.markdown("#### Top Hiring Companies")
                top_companies = filtered_df['Company'].value_counts().head(5)
                st.bar_chart(top_companies)

            col3, col4 = st.columns(2)
            with col3:
                st.markdown("#### Internship Impact")
                box_plot = alt.Chart(filtered_df).mark_boxplot().encode(
                    x="Internship:N",
                    y="Package:Q"
                )
                st.altair_chart(box_plot, use_container_width=True)

            with col4:
                st.markdown("#### Branch-wise Package")
                st.bar_chart(filtered_df.groupby('Branch')['Package'].mean())
        else:
            st.warning("Missing required columns. Please upload valid placement data.")
