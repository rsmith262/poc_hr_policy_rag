import streamlit as st
from RAG_question_answer import handle_query  # make sure this is imported from your existing code

# This provides the code for the app front end

# Streamlit page config
st.set_page_config(page_title="HR Policy Chatbot", page_icon="💬")

# Sidebar content
# This adds a sidebar with some info and instructions on using the app
with st.sidebar:
    st.title("📘 About This App")
    st.markdown(
        """
        This is a **proof of concept** HR Policy chatbot that uses RAG (Retrieval-Augmented Generation).

        Documents included in the knowledgebase

        - Annual Leave Policy
        - Flexible Working Policy
        - Maternity, Paternity and Parental Leave Policy
        - Remuneration Policy
        - Retirement Policy
        - Sabbatical Policy

        **Instructions:**
        - Ask a question about HR policies.
        - The model will retrieve the most relevant sections and generate a concise answer.
        - A link will be given to the relevant document and page number(s) the answer was generated from.
        - Chat history is preserved during your session.

        """
    )

# App title
st.title("💼 HR Policy Chatbot")
st.markdown("Ask a question based on policy documents.")

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
    # uses imported query logic from RAG_question_answer.py
    # see file for langchain and prompt logic
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = handle_query(prompt)
            st.markdown(response)

    # Save assistant response
    st.session_state.messages.append({"role": "assistant", "content": response})
