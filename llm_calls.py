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

                filter_units - User wants to filter/find units based on properties like:
                - Low/high SDA, WWR, radiation levels
                - Rooms connected, component types
                - Unit orientation, level, name
                - Return: unit IDs

                filter_panels - User wants to filter/find panels based on criteria like:
                - Room connection, panel orientation (North/South/East/West)
                - Low/high SDA, WWR, radiation, viewscore
                - Component descriptions
                - Return: unit IDs and panel IDs

                table_summary - User wants summary statistics or counts like:
                - "How many panels face north?"
                - "What's the average WWR?"
                - "Count of units by level"
                - General data insights/statistics
                - Return: text description with numbers/counts

                recommendations - User wants general improvement suggestions or design guidance like:
                - Performance improvement advice based on current values
                - Recommended WWR values for locations/climates
                - Design optimization strategies
                - Best practices for orientation
                - Return: actionable recommendations

                component_recommendations - User wants specific component/element suggestions like:
                - "Which panel components do you recommend for units that need shade?"
                - "What window type should I use for high radiation areas?"
                - "Suggest components for panels with low SDA"
                - Matching available components to performance criteria
                - Return: specific component IDs and descriptions from available library

                refuse - Query is unrelated to building/facade data

                # Examples #
                User: "Show me units with low SDA values"
                Output: filter_units

                User: "Find all north-facing panels with WWR > 0.4"
                Output: filter_panels

                User: "How many panels are connected to bedrooms?"
                Output: table_summary

                User: "What is the recommended WWR for Barcelona?"
                Output: recommendations

                User: "For units that need more shade which panel components do you recommend?"
                Output: component_recommendations

                User: "What window type should I use for high radiation panels?"
                Output: component_recommendations

                User: "What's the weather today?"
                Output: refuse

                IMPORTANT: Output ONLY the exact category name with no extra characters, asterisks, or formatting.
                """,
            },
            {
                "role": "user",
                "content": f"{message}",
            },
        ],
    )
    
    # Clean the response to remove any extra characters
    result = response.choices[0].message.content.strip()
    result = result.replace('*', '').replace('`', '').strip()
    return result