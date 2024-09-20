import pandas as pd
from utils.helpers import read_text
import logging
from tests.synthetic_instructions import instructions as test_instructions

logger = logging.getLogger(__name__)
class Agent:

    def __init__(self, role=None, vectordb=None, llm=None, embeddings=None, questions=None, trls=None, n_results=3, retriever = None, codes = None):
        self.agent_role = role
        self.llm = llm
        self.vectordb = vectordb
        self.retriever = retriever
        self.embeddings = embeddings
        self.instructions = self._get_instructions(role)
        self.questions = questions
        self.trls = trls
        self.n_results = n_results
        self.codes = codes

    def _get_instructions(self, role):
        fname_to_find = f'agents/{role.replace(" ","_").lower()}.txt'
        logger.debug(f'Loading {fname_to_find}')
        try:
            return read_text(fname_to_find, multiline=False)
        except:
            raise FileNotFoundError(f"Did not find {fname_to_find}")

    def _rag_query(self, query: str):
        logger.debug(f'Running re-ranked rag on {query}')
        results = self.retriever.invoke(query)
        return set([i.page_content for i in results])


    def _make_prompt(self, context, question):
        # Clean up formatting
        inst = self.instructions.replace("'", "").replace('"', "").replace("\n", " ")
        ques = question.replace("'", "").replace('"', "").replace("\n", " ")
        prompt = f"""
        Begin your analysis by categorizing the
        question as 'Answered,' 'Not Answered,' or 'Not Applicable' based solely on the context provided and your scientific
        perspective.  If the questions are implicitly or tangentially answered, then consider them 'Answered'. The important
        thing to consider is whether the proposal has considered these questions, rather than explicitly answering them in
        excruciating detail. Note: Do not include any apologies in your responses, but do state your reasoning for your decision.
        Answer in a brief sentence.
        '{inst}' 
            QUESTION: '{ques}'
            PASSAGE: '{context}'
            ANSWER:
            """
        return prompt

    def get_answer(self, question: str):
        contexts = self._rag_query(question)
        full_context = " ".join(contexts)
        prompt = self._make_prompt(full_context, question)
        response = self.llm.invoke(prompt)
        return response.replace('\n',' '), contexts

    def get_binary_answer(self, Q, A):
        prompt = f"""You are a binary response agent. Your responsibility it to assess whether the question asked was answered or not.
        You will respond with only YES, NO, or UNKNOWN. If the answer says the question was answered, then you should also say it is answered.
        
        
        For example:
        Q: Does the ML DevOps team need to create automated scripts for generating datasets using random number generators?
        A: The team should focus on creating automated scripts for generating datasets using random number generators. The answer reflects the intention of the question
        Your response: YES
                
        Q: How should drift detection processes be set up to catch data/model shifts?	
        A: "I categorize this question as **Answered**. The passage provides sufficient information to infer that drift detection processes are set up to catch data/model shifts. These statements imply that the team has implemented measures to detect potential data or model shifts, which is the core concern of drift detection."
        Your response: YES
        
        Q: Has a formal patient risk and safety review been completed?	
        A: Answered
        Your response: YES
        
        Q: Is containerization recommended to ensure consistency during model deployment?
        A: Containerization is not mentioned in the text. Rationale: If the answer suggests that no data was found, then the question was not answered 
        Your response: NO
                
        Q: Is it necessary for the ML DevOps team to implement real-time performance monitoring for the models in production?
        A: Performance monitoring is the process by which results are gauged. Rationale: The answer is not responding to the question
        Your response: UNKNOWN
        
        Q: Is the budget sufficient to accomplish the project aims?	
        A: I categorize this question as ""Answered"". My reasoning is that the passage explicitly mentions the budget allocated for the project, stating ""An appropriate budget to achieve these aims is considered to be $500,000, covering development, deployment, and ongoing support."" This directly addresses the question of whether the budget is sufficient to accomplish the project's aims."
        Your response: YES
        
        Q: How will model performance be compared to a baseline and what aceptance criteria will be used?  	
        A: "I categorize this question as ""Not Answered"". The passage provides information on various aspects of the project, such as model versioning, user feedback capture, infrastructure, auditing, pipeline optimization, best practices, compute resources presentation, and change management. However, it does not explicitly address how model performance will be compared to a baseline or what acceptance criteria will be used. While the passage mentions ""performance monitoring"" and ""auditing processes"", it does not provide specific details on how the model's performance will be evaluated or compared to a baseline. Additionally, there is no mention of acceptance criteria for the model's performance. Therefore, I conclude that this question has not been answered in the provided passage."
        Your response: YES
        
         Q: '{Q}'
         A: '{A}'
         Your Response: 
        """
        return self.llm.invoke(prompt)

    def answer_questions(self):
        col_names = ['TRL', 'Agent', 'Q', 'A', 'Binary', 'Context']
        if self.codes:
            col_names.extend('Code')
        df = pd.DataFrame(columns=col_names)
        for i, q in enumerate(self.questions):
            logger.info(f'Answering question {i+1} of {len(self.questions)}.')
            response, context = self.get_answer(q)
            bin_ans = self.get_binary_answer(q, response)
            result = [self.trls[i], self.agent_role, q, response, bin_ans, '|'.join([x for x in context])]
            if self.codes:
                result.append(self.codes[i])
            df = pd.concat([pd.DataFrame([result], columns=col_names), df])
        return df

class TextGenerator:
    def __init__(self, llm=None):
        """

        Args:
            llm:
        """
        self.llm = llm
        self.instructions = test_instructions

    def generate_text(self, questions):
        # Clean up formatting
        inst = self.instructions.replace("'", "").replace('"', "").replace("\n", " ")
        ques = '  '.join([questions.replace("'", "")]).replace('"', "").replace("\n", " ")
        prompt = f"""'{inst}'
            Given: '{ques}'
            Answer:
            """
        return self.llm.model.invoke(prompt)

class TextSummarizer:
    def __init__(self, llm=None):
        """

        Args:
            llm:
        """
        self.llm = llm

    def generate_text(self, verbose_text):
        prompt = f"""Combine the following information into a single, concise paragraph, eliminating redundant information.
        Ensure that the final result is coherent and retains all unique information. Output only the paragraph.'
        '{verbose_text}'
        """
        return self.llm.model.invoke(prompt)