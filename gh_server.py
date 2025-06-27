from flask import Flask, request, jsonify
from server.config import *

import json, numpy as np, argparse
from openai import OpenAI

from llm_calls import *
from data_utils.create_vector_db import *

from sql_utils.run_sql_rag import *
from rag_utils.run_rag import *

app = Flask(__name__)

@app.route('/llm_call', methods=['POST'])
def llm_call():
    data = request.get_json()
    input_string = data.get('input', '')
    db_path = data.get('db_path', '')
    table_descriptions_path = data.get('table_descriptions_path', '')
    knowledge_pool_path = data.get('knowledge_pool_path', '')
    mode = "local"
    show_context = True
    if table_descriptions_path:
        table_json = update_content_embeddings(table_descriptions_path)
        print("Embthankeddings added to table descriptions!")
    
    router_output = classify_input(input_string)
    print(f"Received input: {input_string}")
    print(f"Classified answer: {router_output}")
    
    json_values = []
    answer = ""
    if router_output == "filter_units": 
        #sql query for units returns unit index
        # answer = "The following units have low SDA values: [Unit 101, Unit 102, Unit 103]. These units are located on the ground floor and have a WWR greater than 0.4."
        # json_values = [{'question classification': f"{router_output}"},
        #                 {"unit_id": "101", "sda": 0.3, "wwr": 0.45, "orientation": "North"},
        #                {"unit_id": "102", "sda": 0.25, "wwr": 0.5, "orientation": "East"},
        #                {"unit_id": "103", "sda": 0.28, "wwr": 0.42, "orientation": "West"}]
        
        answer = run_sql_rag(input_string, db_path, table_descriptions_path=table_descriptions_path)
        json_values = [{'question classification': f"{router_output}"}]
        
    if router_output == "filter_panels":
        #sql query for panels , returns unit index and panel name
        # answer = "The following panels are connected to the units you requested: [Panel A, Panel B, Panel C]. These panels have a WWR greater than 0.4 and are facing north." 
        # json_values = [{'question classification': f"{router_output}"},
        #                 {"panel_id": "A", "unit_id": "101", "orientation": "North", "wwr": 0.45},
        #                {"panel_id": "B", "unit_id": "102", "orientation": "East", "wwr": 0.5},
        #                {"panel_id": "C", "unit_id": "103", "orientation": "West", "wwr": 0.42}]
        
        answer = run_sql_rag(input_string, db_path, table_descriptions_path=table_descriptions_path)
        json_values = [{'question classification': f"{router_output}"}]
    if router_output == "table_summary":
        # # sql query for summary statistics, returns text description with numbers/counts
        # answer = "There are 120 panels facing north with an average WWR of 0.35. The total number of units is 50, with 20 units on the ground floor."       
        # json_values = [{'question classification': f"{router_output}"},
        #                 {"orientation": "North", "count": 120, "average_wwr": 0.35},
        #                {"orientation": "East", "count": 80, "average_wwr": 0.4},
        #                {"orientation": "West", "count": 60, "average_wwr": 0.3},
        #                {"orientation": "South", "count": 40, "average_wwr": 0.25}]
        answer = run_sql_rag(input_string, db_path, table_descriptions_path=table_descriptions_path)
        json_values = [{'question classification': f"{router_output}"}]
    if router_output == "recommendations":
        #rag call on knowledge pool, returns actionable recommendations
        # answer = rag_call(input_string, db_path, mode, show_context)
        # answer = "Based on the current values, I recommend increasing the WWR to 0.4 for better performance in areas with low SDA and high radiation."
        # json_values = [{'question classification': f"{router_output}"},
        #                 {"recommendation": "Increase WWR to 0.4 for better performance in low SDA areas."},
        #                {"recommendation": "Use high-performance glazing for panels with high radiation."},
        #                {"recommendation": "Optimize panel orientation to maximize natural light."}]
        answer, best_vectors, context_results = run_rag(input_string, knowledge_pool_path, mode=mode, show_context=show_context)
        json_values = [{'question classification': f"{router_output}"},{'best_vectors': f"{best_vectors}"}, {'context_results': f"{context_results}"}]
        
    if router_output == "component_recommendations":
        #rag call on knowledge pool, returns specific component IDs and descriptions from available library
        #answer = rag_call(input_string, db_path, mode, show_context) 
        # answer = "Base on my knowledge, you should use the following components for your panels: [Component A, Component B]. These components are suitable for improving performance in areas with low SDA and high radiation."   
        # json_values = [{'question classification': f"{router_output}"},
        #             {"component_id": "A", "description": "High-performance glazing for low SDA areas."}]
        
        answer = run_sql_rag(input_string, db_path, table_descriptions_path=table_descriptions_path)
        json_values = [{'question classification': f"{router_output}"}]
        
        
    if router_output in "refuse":
        answer = "I'm sorry, I cannot assist with that request. Ask me about building performance, facade design, or panel components."
        json_values = [{'question classification': f"{router_output}"}]
    
    return jsonify({
        "response": answer,
        "json_values": json_values if json_values else [],
    })


if __name__ == '__main__':
    app.run(port=5000, debug=True)