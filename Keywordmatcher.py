import json
from flashtext import KeywordProcessor
from multiprocessing import Pool


# Load keywords from a JSON document
def load_keywords(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)
    

def initialize_keyword_processor(keywords_dict):
    keyword_processor = KeywordProcessor(case_sensitive=False)
    
    # Add each keyword mapping to the processor
    for user_term, schema_term in keywords_dict.items():
        keyword_processor.add_keyword(user_term, schema_term)
    
    return keyword_processor

