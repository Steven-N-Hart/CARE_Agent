import re
from collections import defaultdict
import argparse
import logging
import sys
from time import time
import os
import re
from utils.llms import OllamaLLM
from utils.agent_builder import TextSummarizer


def get_args() -> argparse.Namespace:
    description = """
    CARE AI Lifecycle Assessor Text Summarizer    
    """
    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description=description)
    parser.add_argument('-c', '--input_file', default='synthetics/clinical_informatics_sme.txt', help="Input file to deduplicate")
    parser.add_argument('-o', '--output_file', default='synthetics/clinical_informatics_sme_dedup.txt', help="Where to save results")


    parser.add_argument('-v', '--verbosity', dest='verbosity',
                        choices=['DEBUG', 'INFO', 'WARNING', 'CRITICAL'], default='INFO')

    return parser.parse_args()



if __name__ == '__main__':
    args = get_args()
    logging.basicConfig(level=getattr(logging, args.verbosity),
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        handlers=[logging.StreamHandler()])


    o = open(args.output_file, 'w')
    with open(args.input_file, 'r') as f:
        answers = f.readlines()

    # Regular expression to extract the code
    code_pattern = re.compile(r"\|\d+\.\d+\.\d+\.\d+\|")

    # Dictionary to group answers and their codes by their prefix up to the last digit
    grouped_answers = defaultdict(lambda: {"texts": [], "codes": set()})

    for answer in answers:
        match = code_pattern.search(answer)
        if match:
            code = match.group()
            prefix = code[:7]  # Get the prefix up to the last dot (e.g., "|5.1.5.")
            grouped_answers[prefix]["texts"].append(answer)
            grouped_answers[prefix]["codes"].add(code)

    # Function to remove codes from text
    def remove_codes(text):
        return code_pattern.sub('', text).strip()

    # Combine entries with the same prefix and keep track of merged codes
    combined_answers = []
    merged_codes = []

    for prefix, data in grouped_answers.items():
        combined_text = " ".join(data["texts"])
        combined_text_no_codes = remove_codes(combined_text)
        combined_answers.append(combined_text_no_codes)
        merged_codes.append(''.join(list(data["codes"])))

    model = OllamaLLM(build=False)
    ts = TextSummarizer(llm=model)
    total_time = time()
    i = 1
    for code, verbose_text in zip(merged_codes, combined_answers):
        logging.info(f'Condensing question {i} of {len(combined_answers)}')
        answer = ts.generate_text(verbose_text)
        answer_line = code + ' ' + answer + ' ' + code + '\n'
        o.write(answer_line)
        i+=1

    o.close()