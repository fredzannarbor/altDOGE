from dotenv import load_dotenv
import streamlit as st
from src.database import Database
from src.authmanager import AuthManager

load_dotenv()

def main():
    st.set_page_config(page_title="AltDOGE", layout="wide")
    db = Database("xtuff_collections.db")
    auth_manager = AuthManager(db)
    
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    
    if not st.session_state.user_id:
        st.title("AltDOGE - Login")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
            if submitted:
                user_id = auth_manager.authenticate(username, password)
                if user_id:
                    st.session_state.user_id = user_id
                    st.success("Logged in successfully!")
                    st.rerun()
                else:
                    st.error("Invalid credentials")
    else:
        st.title("AltDOGE - Regulatory Reform Platform")
        st.write("Use the sidebar to navigate.")

if __name__ == "__main__":
    main()
