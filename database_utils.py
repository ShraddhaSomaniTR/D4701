from sqlalchemy import create_engine, inspect
from typing import Dict, List
import os
from dotenv import load_dotenv

load_dotenv()

def get_database_connection():
    """Create database connection using environment variables."""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        raise ValueError("DATABASE_URL environment variable not set")
    return create_engine(db_url)

def get_schema_info() -> str:
    """
    Get database schema information including tables and their columns.
    
    Returns:
        str: Formatted schema information
    """
    try:
        engine = get_database_connection()
        inspector = inspect(engine)
        
        schema_info = []
        for table_name in inspector.get_table_names():
            columns = inspector.get_columns(table_name)
            column_info = [f"{col['name']} ({col['type'].__class__.__name__})" for col in columns]
            schema_info.append(f"Table: {table_name}")
            schema_info.append("Columns: " + ", ".join(column_info))
            schema_info.append("")
            
        return "\n".join(schema_info)
    except Exception as e:
        return f"Error fetching schema information: {str(e)}"

def execute_query(query: str) -> List[Dict]:
    """
    Execute SQL query and return results.
    
    Args:
        query (str): SQL query to execute
        
    Returns:
        List[Dict]: Query results as list of dictionaries
    """
    try:
        engine = get_database_connection()
        with engine.connect() as connection:
            result = connection.execute(query)
            return [dict(row) for row in result]
    except Exception as e:
        raise Exception(f"Error executing query: {str(e)}")