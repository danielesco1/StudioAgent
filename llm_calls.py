from server.config import *
import re


def classify_input(message):
    response = client.chat.completions.create(
        model=completion_model,
        messages=[
            {
                "role": "system",
                "content": """
                You are classifying user queries about building facade data. Classify the input into one of these 6 categories:

                filter_units - User wants to FIND/SHOW specific units (return unit IDs):
                - "Show me units with low SDA values"
                - "Find units on level 3"
                - "List units facing north"
                - "Which units have WWR greater than 0.5?"
                - "Show me units with poor daylight performance"
                - "Find all units in the south orientation"
                - "Display units connected to bedrooms"

                filter_panels - User wants to FIND/SHOW specific panels (return panel IDs):
                - "Show me panels facing south"
                - "Find panels with WWR > 0.4"
                - "List all bedroom panels"
                - "Which panels have high radiation exposure?"
                - "Show me east-facing panels with low SDA"
                - "Find panels connected to living rooms"
                - "Display panels with viewscore below 0.3"

                table_summary - User wants COUNTS/STATISTICS/SUMMARIES (return numeric summaries and overviews):
                - "How many panels are facing south?"
                - "What's the average WWR?"
                - "Count panels by orientation"
                - "What percentage of units have low SDA?"
                - "Provide a summary of my building"
                - "Give me an overview of the building data"
                - "Building insights and statistics"
                - "Summarize the building performance"
                - "Overall building analysis"
                - "How many units are on each level?"
                - "What's the total number of bedroom panels?"
                - "Average radiation levels by orientation"

                recommendations - General design guidance and best practices:
                - "What's the recommended WWR for Barcelona?"
                - "How to improve SDA values?"
                - "Best practices for south-facing panels"
                - "What orientation works best for residential units?"
                - "How to reduce radiation while maintaining daylight?"
                - "Strategies for improving viewscore"
                - "Guidelines for WWR in hot climates"

                component_recommendations - Specific component selection from library:
                - "Which panel components for high radiation areas?"
                - "What window type should I use for bedrooms?"
                - "Recommend components for panels that need shade"
                - "Best facade elements for south-facing panels?"
                - "Which components reduce radiation but maintain views?"
                - "Suggest window types for low SDA panels"
                - "What shading components work for east orientation?"

                refuse - Unrelated to building/facade data:
                - "What's the weather today?"
                - "How to bake cookies?"
                - "Current stock market prices"
                - "What time is it?"
                - "How to fix my car?"
                - "Best restaurants in Barcelona"
                - "Latest news headlines"

                Output ONLY the exact category name.
                """,
            },
            {
                "role": "user",
                "content": f"{message}",
            },
        ],
    )
    
    result = response.choices[0].message.content.strip()
    result = result.replace('*', '').replace('`', '').strip()
    return result


# Create a SQL query from user question
def generate_sql_query(dB_context: str, retrieved_descriptions: str, user_question: str) -> str:
    response = client.chat.completions.create(
        model=completion_model,
        messages=[
            {
                "role": "system",
                "content": f"""
                    You are an SQL assistant for a building panels database. Generate accurate SQL queries for any question about building panels.

                    ### DATABASE CONTEXT ###
                    {dB_context}
                    ### TABLE DESCRIPTIONS ###
                    {retrieved_descriptions}

                    ### QUERY PATTERNS ###
                    Count: SELECT COUNT(*) FROM building_panels WHERE...
                    List items: SELECT column FROM building_panels WHERE...
                    Unique values: SELECT DISTINCT column FROM building_panels WHERE...
                    Group/aggregate: SELECT column, COUNT(*) FROM building_panels GROUP BY column
                    Panel types: panel_id LIKE '%WINDOW%' (or %DOOR%, %WALL%, %FLOOR%, %ROOF%)
                    
                    # Instructions #
                     ## Reasoning Steps: ##
                     - Carefully analyze the users question.
                     - Cross-reference the question with the provided database schema and table descriptions.
                     - Think about which data a query to the database should fetch. Only data related to the question should be fetched.
                     - Pay special atenttion to the names of the tables and properties of the schema. Your query must use keywords that match perfectly.
                     - Create a valid and relevant SQL query, using only the table names and properties that are present in the schema.

                     ## Output Format: ##
                     - Output only the SQL query.
                     - Do not use formatting characters like '```sql' or other extra text.
                     - If the database doesnt have enough information to answer the question, simply output "No information".
                    """
            },
            {
                "role": "user",
                "content": user_question,
            },
        ],
    )
    return response.choices[0].message.content

# Create a natural language response out of the SQL query and result
def build_answer(sql_query: str, sql_result: str, user_question: str) -> str:
    response = client.chat.completions.create(
        model=completion_model,
        messages=[
            {
                "role": "system",
                "content": """
                Interpret SQL query results and provide natural language answers. Extract actual data.

                Examples:
                - SQL Result: [('187',), ('291',), ('385',)] → Answer: "[187, 291, 385]"
                - SQL Result: [(15,)] → Answer: "15 panels"
                - SQL Result: [] → Answer: "No results found"
                - SQL Result: [('187', 'bedroom', 'North')] → Answer: "Found: Unit 187 has a North-facing panel in bedroom"
                - SQL Result: [(187, '3B_WINDOW9'), (173, '3B_WINDOW8'), (173, '3B_WINDOW13')] → Answer: "[(187, '3B_WINDOW9'), (173, '3B_WINDOW8'), (173, '3B_WINDOW13')]"
                
                """
            },
            {
                "role": "user",
                "content": f"""
                User question: {user_question}
                SQL Query: {sql_query}
                SQL Result: {sql_result}
                Return the formatted answer according. do not add anything else.
                
                """,
            },
        ],
    )
    return response.choices[0].message.content

# Fix an SQL query that has failed
def fix_sql_query(dB_context: str, user_question: str, atempted_queries: str, exceptions: str) -> str:

    attemptted_entries = []
    for query, exception in zip(atempted_queries, exceptions):
        attemptted_entries.append(f"#Previously attempted query#:{query}. #SQL Exception error#:{exception}")

    queries_exceptions_content = "\n".join(attemptted_entries)

    response = client.chat.completions.create(
        model=completion_model,
        messages=[
            {
                "role": "system",
                "content":
                       f"""
                You are an SQL database expert tasked with correcting a SQL query. A previous attempt to run a query
                did not yield the correct results, either due to errors in execution or because the result returned was empty
                or unexpected. Your role is to analyze the error based on the provided database schema and the details of
                the failed execution, and then provide a corrected version of the SQL query.
                The new query should provide an answer to the question! Dont create queries that do not relate to the question!
                Pay special atenttion to the names of the table and properties. Your query must use keywords that match perfectly.

                # Context Information #
                - The database contains one table, each corresponding to a different panel feature. 
                - Each table row represents an individual instance of a panel feature of that type.
                ## Database Schema: ## {dB_context}

                # Instructions #
                1. Write down in steps why the sql queries might be failling and what could be changed to avoid it. Answer this questions:
                    I. Is the table being fetched the most apropriate to the user question, or could there be another table that might be more suitable?
                    II. Could there be another property in the schema of database for that table that could provide the right answer?
                2. Given your reasoning, write a new query taking into account the various # Failed queries and exceptions # tried before.
                2. Never output the exact same query. You should try something new given the schema of the database.
                3. Your output should come in this format: #Reasoning#: your reasoning. #NEW QUERY#: the new query.
                
                Do not use formatting characters, write only the query string.
                No other text after the query. Do not invent table names or properties. Use only the ones shown to you in the schema.
                """,
            },
            {
                "role": "user",
                "content": f""" 
                #User question#
                {user_question}
                #Failed queries and exceptions#
                {queries_exceptions_content}
                """,
            },
        ],
    )
    
    response_content = response.choices[0].message.content
    #print(response_content)
    match = re.search(r'#NEW QUERY#:(.*)', response_content)
    if match:
        return match.group(1).strip()
    else:
        return None