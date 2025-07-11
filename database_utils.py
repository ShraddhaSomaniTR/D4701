from sqlalchemy import create_engine, inspect, text
from typing import Dict, List, Set
import os
import re
from dotenv import load_dotenv

load_dotenv()

def get_database_connection():
    """Create database connection using a hardcoded SQL Server connection string."""
    # SQLAlchemy connection string for SQL Server using pyodbc
    connection_string = (
        "mssql+pyodbc://dev-app-db:8mLfkU9Q7ALuTVke@w2-dev-db01.cd701adc0fa4.database.windows.net:1433/SPDEV2007"
        "?driver=ODBC+Driver+17+for+SQL+Server"
    )
    return create_engine(connection_string)

def extract_keywords_from_query(query: str) -> Set[str]:
    """
    Extract potential table and column keywords from the natural language query.
    
    Args:
        query (str): Natural language query
        
    Returns:
        Set[str]: Set of keywords that might match table or column names
    """
    # Convert to lowercase for matching
    query_lower = query.lower()
    
    # Remove common SQL words and articles
    stop_words = {
        'select', 'from', 'where', 'and', 'or', 'not', 'in', 'on', 'by', 'for',
        'with', 'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'can', 'show', 'me', 'all', 'get', 'find',
        'list', 'display', 'give', 'tell', 'what', 'which', 'who', 'when',
        'where', 'how', 'why', 'their', 'my', 'your', 'his', 'her', 'its',
        'our', 'this', 'that', 'these', 'those'
    }
    
    # Extract words (alphanumeric sequences)
    words = re.findall(r'\b[a-zA-Z][a-zA-Z0-9_]*\b', query_lower)
    
    # Filter out stop words and short words
    keywords = {word for word in words if word not in stop_words and len(word) > 2}
    
    return keywords

def get_relevant_tables(query_keywords: Set[str], all_tables: List[str]) -> List[str]:
    """
    Find tables that are likely relevant to the query based on keyword matching.
    
    Args:
        query_keywords (Set[str]): Keywords extracted from the query
        all_tables (List[str]): All available table names
        
    Returns:
        List[str]: List of relevant table names
    """
    relevant_tables = []
    
    for table in all_tables:
        table_lower = table.lower()
        
        # Direct match or partial match with table name
        for keyword in query_keywords:
            if (keyword in table_lower or 
                table_lower in keyword or
                any(part in keyword for part in table_lower.split('_')) or
                any(keyword in part for part in table_lower.split('_'))):
                relevant_tables.append(table)
                break
    
    return relevant_tables

def get_relevant_columns(query_keywords: Set[str], table_name: str, inspector) -> List[Dict]:
    """
    Get columns from a table that are likely relevant to the query.
    
    Args:
        query_keywords (Set[str]): Keywords from the query
        table_name (str): Name of the table
        inspector: SQLAlchemy inspector object
        
    Returns:
        List[Dict]: List of relevant column information
    """
    all_columns = inspector.get_columns(table_name)
    relevant_columns = []
    
    # Always include primary key and ID columns
    for col in all_columns:
        col_name_lower = col['name'].lower()
        if ('id' in col_name_lower or 
            col.get('primary_key', False) or
            col_name_lower.endswith('_id')):
            relevant_columns.append(col)
            continue
            
        # Check if column name matches any keyword
        for keyword in query_keywords:
            if (keyword in col_name_lower or 
                col_name_lower in keyword or
                any(part in keyword for part in col_name_lower.split('_')) or
                any(keyword in part for part in col_name_lower.split('_'))):
                relevant_columns.append(col)
                break
    
    # If no relevant columns found, include first 5 columns
    if not relevant_columns:
        relevant_columns = all_columns[:5]
    
    return relevant_columns

def get_filtered_schema_info(query: str) -> str:
    """
    Get database schema information filtered based on the input query.
    Only includes tables and columns that are likely relevant to the query.
    
    Args:
        query (str): Natural language query to filter schema for
        
    Returns:
        str: Filtered schema information
    """
    try:
        engine = get_database_connection()
        inspector = inspect(engine)
        
        # Extract keywords from the query
        query_keywords = extract_keywords_from_query(query)
        
        # Get all table names
        all_tables = inspector.get_table_names()
        
        # Find relevant tables
        relevant_tables = get_relevant_tables(query_keywords, all_tables)
        
        # If no relevant tables found, use first 5 tables
        if not relevant_tables:
            relevant_tables = all_tables[:5]
        
        # Limit to maximum 5 tables to control size
        relevant_tables = relevant_tables[:5]
        
        schema_info = []
        for table_name in relevant_tables:
            # Get relevant columns for this table
            relevant_columns = get_relevant_columns(query_keywords, table_name, inspector)
            
            # Limit columns to maximum 10 to control size
            relevant_columns = relevant_columns[:10]
            
            column_info = [f"{col['name']}({col['type'].__class__.__name__[:3]})" 
                          for col in relevant_columns]
            
            schema_info.append(f"{table_name}: {', '.join(column_info)}")
        
        result = " | ".join(schema_info)
        
        # Add debug info about filtering
        filtered_info = f"[Found {len(relevant_tables)} relevant tables from {len(all_tables)} total]"
        
        return f"{result} {filtered_info}"
        
    except Exception as e:
        return f"Error fetching filtered schema: {str(e)}"

def get_schema_info() -> str:
    """
    Optimized: Get schema info for all 'BASE TABLE' tables in 'dbo' schema,
    excluding those starting with 'BK_' or 'RF_'.
    """
    try:
        engine = get_database_connection()
        query = """
        SELECT
            t.name AS table_name,
            c.name AS column_name,
            ty.name AS data_type
        FROM sys.tables t
        INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
        INNER JOIN sys.columns c ON t.object_id = c.object_id
        INNER JOIN sys.types ty ON c.user_type_id = ty.user_type_id
        WHERE
            s.name = 'dbo'
            AND t.name NOT LIKE 'BK\_%' ESCAPE '\\'
            AND t.name NOT LIKE 'RF\_%' ESCAPE '\\'
        ORDER BY t.name, c.column_id
        """
        with engine.connect() as connection:
            result = connection.execute(text(query))
            rows = result.fetchall()
 
        # Organize results by table
        from collections import defaultdict
        table_columns = defaultdict(list)
        for row in rows:
            table_columns[row.table_name].append(f"{row.column_name} ({row.data_type})")
 
        schema_info = []
        for table_name, columns in table_columns.items():
            schema_info.append(f"Table: dbo.{table_name}")
            schema_info.append("Columns: " + ", ".join(columns))
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
            # Use text() to properly handle the SQL query for newer SQLAlchemy versions
            result = connection.execute(text(query))
            
            # Handle different types of queries
            if result.returns_rows:
                return list(result.mappings().all())
            else:
                # For INSERT, UPDATE, DELETE queries
                return [{"rows_affected": result.rowcount}]
                
    except Exception as e:
        raise Exception(f"Error executing query: {str(e)}")