import streamlit as st

st.title("Main App Area")

# Sidebar content
st.sidebar.title("Navigation")
if st.sidebar.button("Home"):
    st.write("Clicked Home in sidebar")
if st.sidebar.button("Admin"):
    st.write("Clicked Admin in sidebar")
