import streamlit as st

st.set_page_config(layout="wide")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"role": "assistant", "content": {"answer": "Hello", "related": ["Question 1", "Question 2"]}}
    ]

for i, entry in enumerate(st.session_state.chat_history):
    content = entry["content"]
    if isinstance(content, dict) and content.get("related"):
        with st.container(border=True):
            st.markdown("Related questions:")
            for j, r in enumerate(content["related"]):
                if st.button(r, key=f"related_{i}_{j}", use_container_width=True):
                    st.session_state["my_chat_input"] = r
                    st.rerun()

user_input = st.chat_input("Type something...", key="my_chat_input")

if user_input:
    st.write(f"User submitted: {user_input}")
