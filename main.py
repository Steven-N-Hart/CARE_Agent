import argparse
import logging
import sys
import pandas as pd
from time import time

from utils.helpers import load_directory_or_file
from utils.care import CARE
from utils.llms import OllamaLLM
from utils.agent_builder import Agent
from utils.reports import print_results

def get_args() -> argparse.Namespace:
    description = """
    CARE AI Lifecycle Assessor    
    """
    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description=description)
    parser.add_argument('-p', '--proposal_file_or_dir', default='tests/example_proposal.txt', help="Proposal file or directory.")
    parser.add_argument('-c', '--care_file', default='resources/AgentQuestions.xlsm', help="CARE Checklist file.")
    parser.add_argument('-d', '--dbfilepath', default='./db', help="Where to save chromaDB")
    parser.add_argument('-o', '--out_file', default='report', help="Prefix for reports")
    parser.add_argument('-C', '--chunker', default='character', choices=['semantic', 'recursive', 'character'],
                        help="Chunking style")
    parser.add_argument('-u', '--base_url', default='http://localhost:11434',
                        help="URL of your LLM")

    parser.add_argument('-V', '--vector_store', action='store_true', help="Whether to build a vectordb", default=True)
    parser.add_argument('-m', '--model_name', default='llama3:70b', help="LLM Model to use")
    parser.add_argument('-n', '--n_results', default=5, help="Number of results to pull from vector store")
    parser.add_argument('-s', '--chunk_size', default=1000, help="Vector store chunk size.")
    parser.add_argument('-O', '--chunk_overlap', default=500, help="Vector store chunk size overlap.")

    parser.add_argument('-v', '--verbosity', dest='verbosity',
                        choices=['DEBUG', 'INFO', 'WARNING', 'CRITICAL'], default='INFO')

    return parser.parse_args()



if __name__ == '__main__':
    args = get_args()
    logging.basicConfig(level=getattr(logging, args.verbosity),
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        handlers=[logging.StreamHandler()])

    # Read the proposal
    proposal = load_directory_or_file(args.proposal_file_or_dir)

    # Instantiate the CARE checklist
    care_data = CARE(infile=args.care_file)

    # Instantiate an OLLAMA-based LLM, embedding model, and ChromaDB
    model = OllamaLLM(model_name=args.model_name, proposal_document=proposal, chromadb_path=args.dbfilepath,
                      chunker=args.chunker, n_results=args.n_results,
                      build_vectorstore = args.vector_store,
                      base_url = args.base_url,
                      chunk_size=args.chunk_size, chunk_overlap=args.chunk_overlap)


    results_table = pd.DataFrame(columns=['Agent', 'Q', 'A', 'Binary', 'Context', 'TRL'])
    total_time = time()
    for agent in care_data.AGENT_LIST:
        logging.info(f'Creating {agent} agent.')
        agent_time = time()
        questions = care_data.get_list(role=agent)
        trls = care_data.get_list(role=agent, item='TRL')
        current_agent = Agent(role=agent,
                              llm=model.model,
                              embeddings=model.embedding_model,
                              vectordb=model.vectorstore,
                              questions=questions,
                              trls=trls,
                              retriever=model.compression_retriever)
        answer_df = current_agent.answer_questions()
        results_table = pd.concat([results_table, answer_df])
        logging.info(f'{agent} completed in {(time()-agent_time) / 60: .2f} min.')
    logging.info(f'All agents completed in {(time() - total_time) / 60: .2f} min.')

    results_table.to_excel(args.out_file + '.' + args.model_name.replace(':','-') + ".xlsx")
    print_results(report_name=args.out_file, model_name=args.model_name)

