
from server.config import *
import json
import numpy as np
from rag_utils.rag_utils import *


def run_rag(input_string,knowledge_pool_path, mode="local", show_context=True):
    
 
    embeddings_json = knowledge_pool_path
    # --- User Input ---
    query = input_string
    
    # Get available documents
    index_lib = load_embeddings(embeddings_json)
    available_docs = list(set(v.get('source_file', 'unknown').replace('.json', '') for v in index_lib))
    doc_context = f"Available knowledge base: {', '.join(available_docs)}"
    
    answer, best_vectors, context_results = perform_search(query, index_lib, doc_context, num_results=5, mode=mode, show_context=show_context)
    
    return answer, best_vectors, context_results
    
