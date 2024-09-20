from langchain_community.llms import Ollama
from langchain_community.embeddings import OllamaEmbeddings
from langchain_experimental.text_splitter import SemanticChunker
from langchain.text_splitter import RecursiveCharacterTextSplitter, CharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import FlashrankRerank
import shutil

from dotenv import load_dotenv
load_dotenv() # Load environment variables from the .env file (if present)
from tqdm import tqdm

import logging
import os
os.environ['ANONYMIZED_TELEMETRY'] = 'False'

logger = logging.getLogger(__name__)


class OllamaLLM:
    def __init__(self,
                 proposal_document=None,
                 chromadb_path: str = None,
                 model_name: str = 'llama3:70b',
                 base_url: str = 'http://localhost:11434',
                 embeddings_model_name: str = 'mxbai-embed-large',
                 chunker: str = 'semantic',
                 chunk_size: int = 1000,
                 chunk_overlap: int = 200,
                 add_start_index: bool = True,
                 n_results: int = 5,
                 build_vectorstore = True):
        self.proposal_document = proposal_document
        self.model_name = model_name
        self.base_url = base_url
        self.model = Ollama(model=self.model_name, base_url=self.base_url)
        self.embedding_model = OllamaEmbeddings(model=embeddings_model_name)
        if chunker == 'semantic':
            self.text_splitter = SemanticChunker(self.embedding_model)
        elif chunker == 'recursive':
            self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap,
                                                                add_start_index=add_start_index)
        elif chunker == 'character':
            self.text_splitter = CharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap, separator='\n')
        else:
            raise f"{chunker} is not supported."
        self.chromadb_path = chromadb_path
        if build_vectorstore:
            self.vectorstore = self._build_vectorstore(chromadb_path)
            self.n_results = n_results
            self.retriever = self.vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": n_results})
            self.compression_retriever=self._build_reranker()

    def _build_vectorstore(self, persist_directory):
        if not self.proposal_document:
            raise ValueError("Proposal document is required to build the vectorstore.")

        logger.debug('Building vectorDB')
        documents = self.text_splitter.create_documents([self.proposal_document])
        embedding = self.embedding_model
        if os.path.exists(persist_directory):
            shutil.rmtree(persist_directory)
        # NOTE: Bug in chromadb==0.5.0 makes this not save
        db = Chroma.from_documents(documents, embedding, persist_directory=persist_directory)
        return db

    def _build_reranker(self):
        compressor = FlashrankRerank()
        compression_retriever = ContextualCompressionRetriever(
            base_compressor=compressor, base_retriever=self.retriever
        )
        return compression_retriever





