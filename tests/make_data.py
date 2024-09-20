import argparse
import logging
import sys
from time import time
import os
import re
from collections import defaultdict

from utils.care import CARE
from utils.llms import OllamaLLM
from utils.agent_builder import TextGenerator

def get_args() -> argparse.Namespace:
    description = """
    CARE AI Lifecycle Assessor Test Generator    
    """
    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description=description)
    parser.add_argument('-c', '--care_file', default='resources/AgentQuestions.xlsm', help="CARE Checklist file.")
    parser.add_argument('-o', '--out_dir', default='synthetics', help="Where to save results")
    parser.add_argument('-i', '--id', default='TRL.Track.Step.Item', help="Name of unique Identifier column in CARE file")
    parser.add_argument('-t', '--truth_file_prefix', default='truth', help="Name of truth_file prefix")

    parser.add_argument('-v', '--verbosity', dest='verbosity',
                        choices=['DEBUG', 'INFO', 'WARNING', 'CRITICAL'], default='INFO')

    return parser.parse_args()

def get_prefix(code):
    return '.'.join(code.split('.')[:-1])

if __name__ == '__main__':
    args = get_args()
    logging.basicConfig(level=getattr(logging, args.verbosity),
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        handlers=[logging.StreamHandler()])

    os.makedirs(args.out_dir, exist_ok=True)
    # Instantiate the CARE checklist
    care_data = CARE(infile=args.care_file)

    # Verify the unique code value is present
    assert args.id in care_data.infile_data.columns, f"{args.id} not found in CARE file"

    # Instantiate an OLLAMA-based LLM
    model = OllamaLLM(build=False)
    tg = TextGenerator(llm=model)
    total_time = time()
    p = open(f'{args.truth_file_prefix}.tsv', 'w')
    for agent in care_data.AGENT_LIST:
        logging.info(f'Creating {agent} agent.')
        questions = care_data.get_list(role=agent)
        code_id = care_data.get_list(role=agent, item=args.id)
        o = open(args.out_dir + f'/{agent.replace(" ","_").lower()}.txt', 'w')

        # Group similar questions
        # Dictionary to group questions by their code prefix up to the last dot
        grouped_data = defaultdict(lambda: {"questions": [], "codes": set()})
        for question, code in zip(questions, code_id):
            prefix = get_prefix(code)
            grouped_data[prefix]["questions"].append(question)
            grouped_data[prefix]["codes"].add(code)

        i=1
        for prefix, grouped in grouped_data.items():
            logging.info(f'Answering question {i} of {len(grouped_data)}')
            question_batch = ' '.join(grouped['questions'])
            code_batch = '|'.join(grouped['codes'])
            answer = tg.generate_text(question_batch)
            answer = answer.replace('\n', ' ')
            # Remove "Here is a" until ":"
            answer = re.sub(r'Here is a[^:]*:', '', answer)
            answer_line = code_batch + '| ' + answer + ' |' + code_batch + '|\n'
            o.write(answer_line)
            # Agent | Code | Q | A
            truth = '\t'.join([f'{agent.replace(" ","_").lower()}', code_batch, question_batch,  answer])
            p.write(truth + '\n')
            i+=1

        o.close()
        logging.info(f'Finished {agent} agent.')
    p.close()
    logging.info(f'Total time: {time() - total_time:0.2f} seconds')
