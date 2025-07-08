import openai
import os
from dotenv import load_dotenv

load_dotenv()

def init_openai():
    """Initialize OpenAI with API key from environment variables."""
    openai.api_key = os.getenv('OPENAI_API_KEY')

def generate_sql_query(prompt: str, schema_info: str) -> str:
    """
    Generate SQL query from natural language prompt using OpenAI.
    
    Args:
        prompt (str): Natural language query
        schema_info (str): Database schema information
        
    Returns:
        str: Generated SQL query
    """
    try:
        system_prompt = f"""You are a SQL expert. Given the following database schema:
        {schema_info}
        
        Convert the following natural language query to SQL.
        Return ONLY the SQL query without any explanations."""

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating SQL query: {str(e)}"