from utils.helpers import read_file_to_dataframe
import itertools

class CARE:
    def __init__(self, infile=None):
        self.infile_data = read_file_to_dataframe(infile)
        self.AGENT_LIST = self._get_unique_items(column='Relevant Agents')
        #self.TAG_LIST = self._get_unique_items(column='Tags')

    def _get_unique_items(self, column=None):
        return set(
            list(itertools.chain(*[x.replace(', ', ',').split(',') for x in self.infile_data[column].tolist()])))

    def get_list(self, role=None, item='Question'):
        return self.infile_data[item][self.infile_data['Relevant Agents'].str.contains(role)].tolist()

