import json, numpy as np, argparse
from openai import OpenAI
from server.config import *

def get_embedding(text, model=embedding_model):
    return local_client.embeddings.create(input=[text.replace("\n", " ")], model=model).data[0].embedding

def similarity(v1, v2):
    return np.dot(v1, v2)

def load_embeddings(embeddings_json):
    with open(embeddings_json, 'r', encoding='utf8') as f:
        return json.load(f)

def get_best_vectors(question_vector, index_lib, num_results):
    scores = [{'content': v['content'], 'score': similarity(question_vector, v['vector']), 'source_file': v.get('source_file', 'unknown')} for v in index_lib]
    return sorted(scores, key=lambda x: x['score'], reverse=True)[:num_results]

def perform_search(query, index_lib, doc_context, num_results=5, mode="local", show_context=False):
    question_vector = get_embedding(query)
    best_vectors = get_best_vectors(question_vector, index_lib, num_results)
    
    context_parts = [doc_context]
    for v in best_vectors:
        source = v.get('source_file', 'unknown').replace('.json', '')
        context_parts.append(f"[Source: {source}]\n{v['content']}")
    context = "\n\n".join(context_parts)
    
    context_results = ""
    if show_context:
        print(f"\nRETRIEVED CONTEXT:")
        for i, v in enumerate(best_vectors, 1):
            print(f"[{i}] Source: {v.get('source_file', 'unknown')}")
            print(f"Content: {v['content']}\n")
            context_results += f"[{i}] Source: {v.get('source_file', 'unknown')}\nContent: {v['content']}\n\n"
    
    answer = rag_answer(query, context,mode)
    return answer, best_vectors, context_results

def rag_answer(question, context, mode="local"):
    client, completion_model, embedding_model = api_mode(mode)
    
    prompt = f"""Answer the question based on the provided information. 
    You are given extracted parts of a document and a question. Provide a direct answer.
    If you don't know the answer, just say "I do not know.". Don't make up an answer.
    PROVIDED INFORMATION: {context}. Provide a summary of the information provided."""
    
    completion = client.chat.completions.create(
        model=completion_model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": question}
        ],
        temperature=0.1,
    )
    return completion.choices[0].message.content

def extract_values(text, mode="local"): 
    """Provide helpful fallback when RAG fails"""
    client, completion_model, embedding_model = api_mode(mode)
    
    prompt = f"""{text}
        You are a parser that extracts the upper percentage values from a Window-to-Wall Ratio recommendation. Given text with entries like North: 30–40%, South: 40–50% (shaded), East/West: 35–45%, 
        output **only** a JSON object with lowercase keys north, south, east, and west whose values are the upper bounds as integers.  
            Example input:
            The recommended WWR …  
            - North: 30-40%  
            - South: 40-50% (shaded)  
            - East/West: 35-45% 
            Expected output:
            json
            {{'north':40,'south':50,'east':35,'west':45}}
        """

    response = client.chat.completions.create(
        model=completion_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )
    return response.choices[0].message.content