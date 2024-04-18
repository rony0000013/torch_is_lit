# Torch is Lit 🔥❤️‍🔥

Torch is Lit 🔥❤️‍🔥 is a powerful Retrieval Augmented Generation (RAG) application that leverages Large Language Models (LLMs) to provide an intelligent and comprehensive solution for developers and researchers working with PyTorch and coding tasks.

## Features

1. Lit Torch
    - A RAG application built with Vectara and LlamaIndex
    - Utilizes PyTorch documentation and examples as the corpus data
    - Allows users to ask natural language queries related to PyTorch
    - Retrieves relevant information from the corpus and generates responses using the LLM

2. Lit Code
    - A coding-tuned LLM hosted on Together.AI
    - Assists with programming tasks through natural language queries
    - Provides intelligent code suggestions, generation, and debugging support

## Installation

### Prerequisites - Python and Poetry

1. Clone the repository:

    ```bash
    git clone https://github.com/rony0000013/torch-is-lit.git
    ```

2. Install the dependencies:

    ```bash
    poetry install
    ```

3. Add stonks worker deployed link in `.streamlit/secrets.toml`

    ```bash
    VECTARA_CUSTOMER_ID=<YOUR_VECTARA_CUSTOMER_ID>
    VECTARA_CORPUS_ID=<YOUR_VECTARA_CORPUS_ID>
    VECTARA_API_KEY=<YOUR_VECTARA_API_KEY>
    LLAMA_PARSE_API_KEY=<YOUR_LLAMA_PARSE_API_KEY>
    TOGETHER_API_KEY=<YOUR_TOGETHER_API_KEY>
    ```

4. Run the app

    ```bash
    poetry run streamlit run ui.py
    ```

5. To Add data to courpus add files in data directory and run

    ```bash
    poetry run python file_index.py
    ```

## Usage

1. Lit Torch
    - Run the Lit Torch application and ask queries regarding pytorch docs
    - Ask natural language queries related to PyTorch, and the application will retrieve relevant information from the corpus and generate responses using the LLM.

2. Lit Code
    - Access the Lit Code interface in the streamlit app
    - Provide natural language queries related to programming tasks
    - Lit Code will generate intelligent code suggestions, assist with code generation, and help with debugging.

## License

This project is licensed under the Apache 2 License.

## Acknowledgments

- Vectara for providing the RAG toolkit
- LlamaIndex for the powerful index and query capabilities
- Together.AI for hosting the coding-tuned LLM
