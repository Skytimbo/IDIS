import streamlit as st

st.set_page_config(layout="centered")
st.title("Simple Search Input Test")

# Use a simple text input widget
search_term = st.text_input("Enter search term here:")

# A button to trigger an action
if st.button("Submit"):
    st.success(f"You submitted: '{search_term}'")
    st.info("If you can see your text above, this pattern works.")

st.write(f"(Current value in variable: '{search_term}')")