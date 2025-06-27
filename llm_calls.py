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
                Generate SQL queries for building/panel data using exact schema names.

                ### DATABASE ###
                {dB_context}
                {retrieved_descriptions}

                ### QUERY EXAMPLES ###
                "How many panels face south?" → SELECT COUNT(*) FROM building_sql WHERE panel_orientation = 'South'
                "Average WWR by orientation" → SELECT panel_orientation, AVG(WWR) FROM building_sql GROUP BY panel_orientation
                "Building summary" → SELECT COUNT(*), AVG(sda), AVG(WWR), AVG(radiation) FROM building_sql
                "Show panels with low SDA" → SELECT unit_id, panel_name FROM building_sql WHERE sda < 30
                "Panels in bedrooms" → SELECT unit_id, panel_name FROM building_sql WHERE connected_room LIKE '%bedroom%'
                "Units with poor daylight" → SELECT DISTINCT unit_id FROM building_sql WHERE sda < 30
                "Components used most" → SELECT component, COUNT(*) FROM building_sql GROUP BY component ORDER BY COUNT(*) DESC
                "WWR for low SDA units" → SELECT unit_id, WWR FROM building_sql WHERE sda < 30

                ### RULES ###
                - Panel queries: always return unit_id, panel_name
                - Use LIKE '%pattern%' for text matching
                - Thresholds: Low SDA < 30, High SDA > 50, High radiation > 1.0
                - Output only SQL, no formatting or explanations
                """
            },
            {
                "role": "user", 
                "content": user_question,
            },
        ],
    )
    
    # Clean formatting
    sql = response.choices[0].message.content.strip()
    sql = sql.replace('```sql', '').replace('```', '')
    
    # Take only the first line that looks like SQL
    lines = sql.split('\n')
    for line in lines:
        line = line.strip()
        if line.upper().startswith('SELECT'):
            return line.rstrip(';') + ';'
    
    return sql.split('\n')[0].strip()

# Create a natural language response out of the SQL query and result
def build_answer(sql_query: str, sql_result: str, user_question: str) -> str:
    response = client.chat.completions.create(
        model=completion_model,
        messages=[
            {
                "role": "system",
                "content": """
                Extract structured data from SQL results for indexing purposes.

                **Panel queries (unit_id, panel_name):**
                SQL Result: [(187, '3B_WINDOW9'), (173, '3B_WINDOW8')] → Return: [(187, '3B_WINDOW9'), (173, '3B_WINDOW8')]

                **Unit queries:**
                SQL Result: [('187',), ('291',), ('385',)] → Return: [187, 291, 385]

                **Count queries:**
                SQL Result: [(15,)] → Return: 15

                **Empty results:**
                SQL Result: [] → Return: []

                Always return raw data structure, no descriptive text.
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