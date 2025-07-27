import streamlit as st
from src.database import Database
from src.authmanager import AuthManager

def main():
    db = Database("xtuff_collections.db")
    auth_manager = AuthManager(db)
    
    if not st.session_state.get("user_id"):
        st.error("Please log in to access this page.")
        st.stop()
    
    st.title(f"AltDOGE - {st.session_state.page_title}")
    st.write("Page under construction.")

if __name__ == "__main__":
    main()
