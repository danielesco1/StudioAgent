import json
import os
import re
from llama_parse import LlamaParse
from config import *
from tqdm import tqdm
import time
from chunking_strategies import load_pdf_text,chunk_for_rag_bullets

# Parser setup - moved to top
parser = LlamaParse(
    api_key=LLAMAPARSE_API_KEY, 
    result_type="markdown",
    num_workers=4,
    verbose=True,
    language="en",
)

def get_embedding(text, model=embedding_model, max_retries=3):
    for attempt in range(max_retries):
        try:
            return local_client.embeddings.create(input=[text.replace("\n", " ")], model=model).data[0].embedding
        except Exception as e:
            if attempt < max_retries - 1: time.sleep(2 ** attempt)
            else: raise e

def process_pdfs_and_create_embeddings(directory="knowledge_pool"):
    for filename in os.listdir(directory):
        if not filename.endswith(".pdf"): continue
        
        try:
            print(f"Processing {filename}...")
            
            
            # Parse PDF and extract text
            # with open(os.path.join(directory, filename), "rb") as f:
            #     docs = parser.load_data(f, extra_info={"file_name": os.path.join(directory, filename)})
            
            pdf_path = os.path.join(directory, filename)
            
            full_text = load_pdf_text(pdf_path)
            print(full_text[:500])
            base_name = os.path.splitext(filename)[0]
            with open(os.path.join(directory, f"{base_name}.txt"), 'w', encoding='utf-8', errors='replace') as f:
                f.write(full_text)
            # extract text :contentReference[oaicite:0]{index=0}
            chunks = chunk_for_rag_bullets(full_text)

            # example: print or send to your embedding pipeline
            for i, chunk in enumerate(chunks, 1):
                print(f"=== Chunk {i} ===\n{chunk}\n")
            
            # full_text = "\n".join(doc.text for doc in docs if doc.text.strip())
            # if not full_text: continue
            
            # # Save text file
            # base_name = os.path.splitext(filename)[0]
            # with open(os.path.join(directory, f"{base_name}.txt"), 'w', encoding='utf-8', errors='replace') as f:
            #     f.write(full_text)
            
            # Create chunks and embeddings
            # chunks = chunk_for_rag(full_text)
            # chunks = chunk_for_rag_bullets(full_text)
            print(f"Created {len(chunks)} chunks from {filename}")
            
            embeddings = []
            for chunk in tqdm(chunks, desc=f"Embedding {filename}"):
                clean_chunk = re.sub(r'\n+', ' ', chunk).strip()
                embeddings.append({'content': clean_chunk, 'vector': get_embedding(clean_chunk)})
            
            # Save embeddings
            with open(os.path.join(directory, f"{base_name}.json"), 'w', encoding='utf-8') as f:
                json.dump(embeddings, f, indent=2, ensure_ascii=False)
            
            print(f"Finished {filename} - {len(embeddings)} embeddings created")
            
        except Exception as e:
            print(f"Error processing {filename}: {e}")

if __name__ == "__main__":
    process_pdfs_and_create_embeddings()