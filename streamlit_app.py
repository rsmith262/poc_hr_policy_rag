import streamlit as st
from RAG_question_answer import handle_query  # make sure this is imported from your existing code

# Streamlit page config
st.set_page_config(page_title="HR Policy Chatbot", page_icon="💬")

# App title
st.title("💼 HR Policy Chatbot")
st.markdown("Ask a question based on company policy documents.")

# Session state to hold chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User input
if prompt := st.chat_input("Ask a question about HR policies..."):
    # Display user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get model response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = handle_query(prompt)
            st.markdown(response)

    # Save assistant response
    st.session_state.messages.append({"role": "assistant", "content": response})
