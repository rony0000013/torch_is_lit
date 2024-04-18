
from llama_index.core import SimpleDirectoryReader
from llama_index.indices.managed.vectara import VectaraIndex
from llama_parse import LlamaParse
from pathlib import Path
import toml
import os




if __name__ == '__main__':
    config = toml.load('./.streamlit/secrets.toml')
    os.environ["VECTARA_CUSTOMER_ID"] = config['VECTARA_CUSTOMER_ID']
    os.environ["VECTARA_CORPUS_ID"] = config['VECTARA_CORPUS_ID']
    os.environ["VECTARA_API_KEY"] = config['VECTARA_API_KEY']

    parser = LlamaParse(
        api_key=config['LLAMA_PARSE_API_KEY'],
        result_type="markdown",
    )
    
    reader = SimpleDirectoryReader(input_dir=os.path.join(os.getcwd(), Path('data')), file_extractor={".pdf": parser}, recursive=True)
    documents = reader.load_data(num_workers=12)
    index = VectaraIndex.from_documents(documents, show_progress=True)
    retriever = index.as_retriever(similarity_top_k=7)



