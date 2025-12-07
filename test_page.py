import streamlit as st

st.sidebar.title("Test")
page = st.sidebar.radio("Go to:", ["A","B"])
st.write("page is:", page)

if page == "A":
    st.write("A page")
elif page == "B":
    st.write("B page")
