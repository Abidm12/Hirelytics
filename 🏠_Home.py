import streamlit as st
# --- Custom CSS for Sidebar Navigation ---
st.markdown(
    """
    <style>
    /* Style the sidebar page navigation */
    section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] ul li a {
        font-size: 18px !important;   /* Increase font size */
        font-weight: 600 !important;  /* Bold text */
        color: #2c3e50 !important;    /* Custom text color */
    }

    /* Hover effect */
    section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] ul li a:hover {
        color: #1abc9c !important;    /* Change color on hover */
    }

    /* Active page highlight */
    section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] ul li a[data-testid="stSidebarNavLinkActive"] {
        color: #e74c3c !important;    /* Active page color */
        font-weight: 700 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- App Content ---

st.markdown("""# 🏫 Hirelytics """)

st.markdown("""---""")
st.markdown("""
Welcome to the **Hirelytics** — Turning placement insights into career guidance.  

### 👨‍🎓 For Students
- 🎯 Placement prediction using historical data  
- 📝 Resume analysis with improvement suggestions  
- 📄 Resume builder to create professional resumes  

### 🏢 For Colleges
- 📊 Placement dashboards and insights  
- 📈 Trend analysis for data-driven decisions  

Empowering students to prepare better and helping colleges make informed choices.  
""")

