import streamlit as st
# from file_index import retriever
from together import Together
from pathlib import Path
import os
import requests
import json


st.set_page_config(page_title="Torch is Lit", page_icon="🔥", layout="wide")
st.title("Torch is Lit 🔥❤️‍🔥")

def clear_chat_history():
    st.session_state.messages_rag = [
        {"role": "assistant", "content": "How may I assist you today?"}
    ]
    st.session_state.messages_code = [
        {"role": "assistant", "content": "How may I assist your code today?"}
    ]

@st.cache_data
def together_chat(messages):
    client = Together(api_key=os.environ["TOGETHER_API_KEY"])
    response = client.chat.completions.create(
        model="Phind/Phind-CodeLlama-34B-v2", messages=messages
    )
    return response.choices[0].message.content

def rag_prepare(st_files):
    if st_files:
        for file in st_files:
            with open(os.path.join('data', file.name), "wb") as f:
                f.write(file.read())

        for root, dirs, files in os.walk("data"):
            for file in files:
                url = "https://api.vectara.io/v1/upload/"
                params = {
                    "c": os.environ["VECTARA_CUSTOMER_ID"],
                    "o": os.environ["VECTARA_CORPUS_ID"],
                }
                payload = {}
                files = [
                    (
                        "file",
                        ("file", open(os.path.join(root, file), "rb"), "application/octet-stream"),
                    )
                ]
                headers = {
                    "Content-Type": "multipart/form-data",
                    "Accept": "application/json",
                    "x-api-key": os.environ["VECTARA_API_KEY"],
                }

                res = requests.request("POST", url, headers=headers, data=payload, files=files, params=params)
                print(res.json())
        # for filename in os.listdir("data"):
        #     file_path = os.path.join("data", filename)
        #     if os.path.isfile(file_path) or os.path.islink(file_path):
        #         os.unlink(file_path)


@st.cache_data
def rag_summarize(prompt):
    url = "https://api.vectara.io/v1/query"

    payload = json.dumps(
        {
            "query": [
                {
                    "query": prompt,
                    "start": 0,
                    "numResults": 10,
                    "contextConfig": {
                        "sentences_before": 3,
                        "sentences_after": 3,
                        "start_tag": "<b>",
                        "end_tag": "</b>",
                    },
                    "rerankingConfig": {
                        "rerankerId": 272725718,
                        "mmrConfig": {"diversityBias": 0.2},
                    },
                    "corpusKey": [
                        {
                            "customerId": os.environ["VECTARA_CUSTOMER_ID"],
                            "corpus_id": os.environ["VECTARA_CORPUS_ID"],
                            "semantics": 0,
                            "metadataFilter": "",
                            "dim": [],
                        }
                    ],
                    "summary": [
                        {
                            "summarizerPromptName": "vectara-summary-ext-v1.3.0",
                            "max_summarized_results": 1,
                            "response_lang": "en",
                        }
                    ],
                    "factualConsistencyScore": "true",
                }
            ]
        }
    )
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "x-api-key": os.environ["VECTARA_API_KEY"],
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    if response.status_code != 200:
        return {"summary": [{"text": "I'm sorry, I couldn't find the answer to your question."}], "response": []}
    return response.json()['responseSet'][0]


with st.sidebar:
    if VECTARA_CUSTOMER_ID := st.text_input(
        "Vectara Customer ID", key="vectara_customer_id"
    ):
        if VECTARA_CUSTOMER_ID != "":
            os.environ["VECTARA_CUSTOMER_ID"] = VECTARA_CUSTOMER_ID
        else:
            os.environ["VECTARA_CUSTOMER_ID"] = st.secrets["VECTARA_CUSTOMER_ID"]
    if VECTARA_API_KEY := st.text_input("Vectara API Key", key="vectara_api_key"):
        if VECTARA_API_KEY != "":
            os.environ["VECTARA_API_KEY"] = VECTARA_API_KEY
        else:
            os.environ["VECTARA_API_KEY"] = st.secrets["VECTARA_API_KEY"]
    if VECTARA_CORPUS_ID := st.text_input("Vectara Index ID", key="vectara_corpus_id"):
        if VECTARA_CORPUS_ID != "":
            os.environ["VECTARA_CORPUS_ID"] = VECTARA_CORPUS_ID
        else:
            os.environ["VECTARA_CORPUS_ID"] = st.secrets["VECTARA_CORPUS_ID"]
    if LLAMA_PARSE_API_KEY := st.text_input(
        "Llama Parse API Key", key="llama_parse_api_key"
    ):
        if LLAMA_PARSE_API_KEY != "":
            os.environ["LLAMA_PARSE_API_KEY"] = LLAMA_PARSE_API_KEY
        else:
            os.environ["LLAMA_PARSE_API_KEY"] = st.secrets["LLAMA_PARSE_API_KEY"]
    if TOGETHER_API_KEY := st.text_input("Together API Key", key="together_api_key"):
        if TOGETHER_API_KEY != "":
            os.environ["TOGETHER_API_KEY"] = TOGETHER_API_KEY
        else:
            os.environ["TOGETHER_API_KEY"] = st.secrets["TOGETHER_API_KEY"]
    if file := st.file_uploader("Upload RAG Corpus", accept_multiple_files=True):
        with st.spinner("Preparing RAG Corpus..."):
            rag_prepare(file)
            st.success("RAG Corpus uploaded successfully!")

    st.button("Clear Chat History ♻️🗑️", on_click=clear_chat_history)





tab1, tab2 = st.tabs(["Lit Torch 🔥❤️‍🔥", "Lit Code 🧑‍💻⚡"])
with tab1:
    st.header("Lit Torch 🔥❤️‍🔥")

    with st.expander("About this app"):
        st.write("""
        This app is a simple chat interface to interact with the docs in RAG application.

        """)

    if "messages_rag" not in st.session_state:
        st.session_state.messages_rag = [
            {"role": "assistant", "content": "How may I assist you today?"}
        ]

    if prompt := st.chat_input("Type a message here..."):
        st.session_state.messages_rag.append({"role": "user", "content": prompt})
        with st.spinner("Thinking... 🧠"):
            response = rag_summarize(prompt)['summary'][0]['text']
            # response = prompt
        st.session_state.messages_rag.append({"role": "assistant", "content": response})

    for message in st.session_state.messages_rag[::-1]:
        if message["role"] == "assistant":
            st.chat_message("assistant", avatar="🔥").markdown(message["content"])
        else:
            st.chat_message(message["role"], avatar="😋").markdown(message["content"])


with tab2:
    st.header("Lit Code 🧑‍💻⚡")

    with st.expander("About this app"):
        st.write("""
        Coding bot

        """)

    if "messages_code" not in st.session_state:
        st.session_state.messages_code = [
            {"role": "assistant", "content": "How may I assist your code today?"}
        ]

    if prompt := st.chat_input("Code Here..."):
        st.session_state.messages_code.append({"role": "user", "content": prompt})
        with st.spinner("Thinking... 🧠"):
            response = together_chat(st.session_state.messages_code)
            # response = prompt
        st.session_state.messages_code.append(
            {"role": "assistant", "content": response}
        )

    for message in st.session_state.messages_code[::-1]:
        if message["role"] == "assistant":
            st.chat_message(message["role"], avatar="⚡").markdown(message["content"])
        else:
            st.chat_message(message["role"], avatar="😋").markdown(message["content"])
