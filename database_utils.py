from sqlalchemy import create_engine, inspect, text
from typing import Dict, List, Set
import os
import re
from dotenv import load_dotenv
from table_column_matcher import get_relevant_tables_fuzz, get_relevant_columns_fuzz

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

# def get_relevant_tables(query_keywords: Set[str], all_tables: List[str]) -> List[str]:
#     """
#     Find tables that are likely relevant to the query based on keyword matching.
    
#     Args:
#         query_keywords (Set[str]): Keywords extracted from the query
#         all_tables (List[str]): All available table names
        
#     Returns:
#         List[str]: List of relevant table names
#     """
#     relevant_tables = []
    
#     for table in all_tables:
#         table_lower = table.lower()
        
#         # Direct match or partial match with table name
#         for keyword in query_keywords:
#             if (keyword in table_lower or 
#                 table_lower in keyword or
#                 any(part in keyword for part in table_lower.split('_')) or
#                 any(keyword in part for part in table_lower.split('_'))):
#                 relevant_tables.append(table)
#                 break
    
#     return relevant_tables

def get_relevant_tables(query_keywords: Set[str], all_tables: List[str]) -> List[str]:
    """
    Find tables that are likely relevant to the query based on keyword matching.
    """
    relevant_tables = []
    # First: Try exact table name matches
    for table in all_tables:
        table_lower = table.lower()
        if table_lower in query_keywords:
            relevant_tables.append(table)
    # If no exact matches, try column matches
    if not relevant_tables:
        try:
            engine = get_database_connection()
            inspector = inspect(engine)
            for table in all_tables:
                columns = inspector.get_columns(table)
                for col in columns:
                    if col['name'].lower() in query_keywords:
                        relevant_tables.append(table)
                        break  # Found a matching column, no need to check others
        except Exception as e:
            print(f"Error checking columns: {str(e)}")
    # If still no matches, then fallback to partial matches
    if not relevant_tables:
        for table in all_tables:
            table_lower = table.lower()
            for keyword in query_keywords:
                if (keyword in table_lower or 
                    any(part in keyword for part in table_lower.split('_'))):
                    relevant_tables.append(table)
                    break
    return list(set(relevant_tables))  # Remove duplicates

# def get_relevant_columns(query_keywords: Set[str], table_name: str, inspector) -> List[Dict]:
#     """
#     Get columns from a table that are likely relevant to the query.
    
#     Args:
#         query_keywords (Set[str]): Keywords from the query
#         table_name (str): Name of the table
#         inspector: SQLAlchemy inspector object
        
#     Returns:
#         List[Dict]: List of relevant column information
#     """
#     all_columns = inspector.get_columns(table_name)
#     relevant_columns = []
    

#     # Always include primary key and ID columns
#     for col in all_columns:
#         col_name_lower = col['name'].lower()
#         if ('id' in col_name_lower or 
#             col.get('primary_key', False) or
#             col_name_lower.endswith('_id')):
#             relevant_columns.append(col)
#             continue
            
#         # Check if column name matches any keyword
#         for keyword in query_keywords:
#             if (keyword in col_name_lower or 
#                 col_name_lower in keyword or
#                 any(part in keyword for part in col_name_lower.split('_')) or
#                 any(keyword in part for part in col_name_lower.split('_'))):
#                 relevant_columns.append(col)
#                 break
    
#     # If no relevant columns found, include first 5 columns
#     if not relevant_columns:
#         relevant_columns = all_columns[:5]
    
#     return relevant_columns

def get_relevant_columns(query_keywords: Set[str], table_name: str, inspector) -> List[Dict]:
    """
    Get columns from a table that are likely relevant to the query.
    Prioritizes exact matches, then partial matches, then id columns, then fallback.
    """
    all_columns = inspector.get_columns(table_name)
    relevant_columns = []
 
    # 1. Exact column name matches
    for col in all_columns:
        col_name_lower = col['name'].lower()
        if col_name_lower in query_keywords:
            relevant_columns.append(col)
 
    # 2. If no exact matches, try partial/fuzzy matches
    if not relevant_columns:
        for col in all_columns:
            col_name_lower = col['name'].lower()
            for keyword in query_keywords:
                if (keyword in col_name_lower or
                    col_name_lower in keyword or
                    any(part in keyword for part in col_name_lower.split('_')) or
                    any(keyword in part for part in col_name_lower.split('_'))):
                    relevant_columns.append(col)
                    break
 
    # 3. If still no matches, include primary key and ID columns
    if not relevant_columns:
        for col in all_columns:
            col_name_lower = col['name'].lower()
            if ('id' in col_name_lower or 
                col.get('primary_key', False) or
                col_name_lower.endswith('_id')):
                relevant_columns.append(col)
 
    # 4. Fallback: If still no relevant columns found, include first 5 columns
    if not relevant_columns:
        relevant_columns = all_columns[:5]
 
    return relevant_columns

def get_all_columns(table_name: str, inspector) -> List[Dict]:
    all_columns = inspector.get_columns(table_name)
    return all_columns

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
        relevant_tables = get_relevant_tables_fuzz(query_keywords, all_tables)
        
        schema_info = []
        # If no relevant tables found, use first 5 tables
        if not relevant_tables:
            
            relevant_tables = all_tables[:5]
            # Get relevant columns for this table
            for table_name in relevant_tables:
                relevant_columns = get_relevant_columns(query_keywords, table_name, inspector)

                column_info = [f"{col['name']}({col['type'].__class__.__name__[:3]})" 
                          for col in relevant_columns]
            
                schema_info.append(f"{table_name}: {', '.join(column_info)}")
        
        else:
            # For relevant tables, get ALL columns
            for table_name in relevant_tables:
            # Get relevant columns for this table
                relevant_columns = get_all_columns(table_name, inspector)
            
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

# Add these functions to your existing database_utils.py file

def get_stored_procedures() -> List[str]:
    """
    Get list of all stored procedures in the database.
    
    Returns:
        List[str]: List of stored procedure names
    """
    try:
        engine = get_database_connection()
        query = """
        SELECT 
            ROUTINE_NAME as procedure_name
        FROM INFORMATION_SCHEMA.ROUTINES
        WHERE ROUTINE_TYPE = 'PROCEDURE'
            AND ROUTINE_SCHEMA = 'dbo'
        ORDER BY ROUTINE_NAME
        """
        with engine.connect() as connection:
            result = connection.execute(text(query))
            procedures = [row.procedure_name for row in result.fetchall()]
        return procedures
    except Exception as e:
        raise Exception(f"Error fetching stored procedures: {str(e)}")

def get_stored_procedure_definition(procedure_name: str) -> str:
    """
    Get the definition of a specific stored procedure.
    
    Args:
        procedure_name (str): Name of the stored procedure
        
    Returns:
        str: Stored procedure definition
    """
    try:
        engine = get_database_connection()
        query = """
        SELECT 
            ROUTINE_DEFINITION as definition
        FROM INFORMATION_SCHEMA.ROUTINES
        WHERE ROUTINE_NAME = :procedure_name
            AND ROUTINE_TYPE = 'PROCEDURE'
            AND ROUTINE_SCHEMA = 'dbo'
        """
        with engine.connect() as connection:
            result = connection.execute(text(query), {"procedure_name": procedure_name})
            row = result.fetchone()
            if row:
                return row.definition
            else:
                raise Exception(f"Stored procedure '{procedure_name}' not found")
    except Exception as e:
        raise Exception(f"Error fetching stored procedure definition: {str(e)}")

def get_stored_procedure_parameters(procedure_name: str) -> List[Dict]:
    """
    Get parameters of a stored procedure.
    
    Args:
        procedure_name (str): Name of the stored procedure
        
    Returns:
        List[Dict]: List of parameter information
    """
    try:
        engine = get_database_connection()
        query = """
        SELECT 
            PARAMETER_NAME as name,
            DATA_TYPE as data_type,
            CHARACTER_MAXIMUM_LENGTH as max_length,
            PARAMETER_MODE as mode
        FROM INFORMATION_SCHEMA.PARAMETERS
        WHERE SPECIFIC_NAME = :procedure_name
            AND SPECIFIC_SCHEMA = 'dbo'
        ORDER BY ORDINAL_POSITION
        """
        with engine.connect() as connection:
            result = connection.execute(text(query), {"procedure_name": procedure_name})
            return [dict(row._mapping) for row in result.fetchall()]
    except Exception as e:
        raise Exception(f"Error fetching stored procedure parameters: {str(e)}")

def analyze_stored_procedure_performance(procedure_name: str) -> Dict:
    """
    Analyze stored procedure performance metrics.
    Falls back to basic info if performance views are not accessible.
    
    Args:
        procedure_name (str): Name of the stored procedure
        
    Returns:
        Dict: Performance metrics or basic procedure info
    """
    try:
        engine = get_database_connection()
        
        # First try to access performance stats
        perf_query = """
        SELECT 
            p.name as procedure_name,
            ps.execution_count,
            ps.total_elapsed_time,
            CASE 
                WHEN ps.execution_count > 0 
                THEN ps.total_elapsed_time / ps.execution_count 
                ELSE 0 
            END as avg_elapsed_time,
            ps.total_logical_reads,
            CASE 
                WHEN ps.execution_count > 0 
                THEN ps.total_logical_reads / ps.execution_count 
                ELSE 0 
            END as avg_logical_reads,
            ps.total_logical_writes,
            CASE 
                WHEN ps.execution_count > 0 
                THEN ps.total_logical_writes / ps.execution_count 
                ELSE 0 
            END as avg_logical_writes,
            ps.cached_time,
            ps.last_execution_time,
            ps.total_physical_reads,
            CASE 
                WHEN ps.execution_count > 0 
                THEN ps.total_physical_reads / ps.execution_count 
                ELSE 0 
            END as avg_physical_reads,
            ps.min_elapsed_time,
            ps.max_elapsed_time,
            ps.total_worker_time,
            CASE 
                WHEN ps.execution_count > 0 
                THEN ps.total_worker_time / ps.execution_count 
                ELSE 0 
            END as avg_worker_time
        FROM sys.procedures p
        LEFT JOIN sys.dm_exec_procedure_stats ps ON p.object_id = ps.object_id
        WHERE p.name = :procedure_name
            AND p.schema_id = SCHEMA_ID('dbo')
        """
        
        with engine.connect() as connection:
            result = connection.execute(text(perf_query), {"procedure_name": procedure_name})
            row = result.fetchone()
            if row:
                return dict(row._mapping)
            else:
                return {"message": f"No performance data found for '{procedure_name}'"}
                
    except Exception as e:
        # If performance stats are not accessible, fall back to basic procedure info
        if "permission" in str(e).lower() or "denied" in str(e).lower():
            return get_basic_procedure_info(procedure_name)
        else:
            raise Exception(f"Error analyzing stored procedure performance: {str(e)}")

def get_basic_procedure_info(procedure_name: str) -> Dict:
    """
    Get basic stored procedure information when performance stats are not available.
    
    Args:
        procedure_name (str): Name of the stored procedure
        
    Returns:
        Dict: Basic procedure information
    """
    try:
        engine = get_database_connection()
        query = """
        SELECT 
            p.name as procedure_name,
            p.create_date,
            p.modify_date,
            p.object_id,
            CASE 
                WHEN p.is_ms_shipped = 1 THEN 'System'
                ELSE 'User'
            END as procedure_type,
            'Performance data not available (insufficient permissions)' as performance_note
        FROM sys.procedures p
        WHERE p.name = :procedure_name
            AND p.schema_id = SCHEMA_ID('dbo')
        """
        
        with engine.connect() as connection:
            result = connection.execute(text(query), {"procedure_name": procedure_name})
            row = result.fetchone()
            if row:
                return dict(row._mapping)
            else:
                return {"message": f"Stored procedure '{procedure_name}' not found"}
                
    except Exception as e:
        raise Exception(f"Error getting basic procedure info: {str(e)}")

def get_stored_procedures_with_performance() -> List[Dict]:
    """
    Get list of stored procedures with basic performance metrics.
    Falls back to basic info if performance views are not accessible.
    
    Returns:
        List[Dict]: List of stored procedures with performance data or basic info
    """
    try:
        engine = get_database_connection()
        
        # First try to get performance data
        perf_query = """
        SELECT 
            p.name as procedure_name,
            p.create_date,
            p.modify_date,
            ISNULL(ps.execution_count, 0) as execution_count,
            ISNULL(ps.total_elapsed_time, 0) as total_elapsed_time,
            CASE 
                WHEN ps.execution_count > 0 
                THEN ps.total_elapsed_time / ps.execution_count 
                ELSE 0 
            END as avg_elapsed_time,
            ISNULL(ps.last_execution_time, p.create_date) as last_execution_time,
            'Performance data available' as data_source
        FROM sys.procedures p
        LEFT JOIN sys.dm_exec_procedure_stats ps ON p.object_id = ps.object_id
        WHERE p.schema_id = SCHEMA_ID('dbo')
        ORDER BY ps.execution_count DESC, p.name
        """
        
        with engine.connect() as connection:
            result = connection.execute(text(perf_query))
            return [dict(row._mapping) for row in result.fetchall()]
            
    except Exception as e:
        # If performance stats are not accessible, fall back to basic procedure list
        if "permission" in str(e).lower() or "denied" in str(e).lower():
            return get_basic_procedures_list()
        else:
            raise Exception(f"Error fetching stored procedures with performance: {str(e)}")

def get_basic_procedures_list() -> List[Dict]:
    """
    Get basic list of stored procedures when performance stats are not available.
    
    Returns:
        List[Dict]: List of stored procedures with basic info
    """
    try:
        engine = get_database_connection()
        query = """
        SELECT 
            p.name as procedure_name,
            p.create_date,
            p.modify_date,
            p.object_id,
            CASE 
                WHEN p.is_ms_shipped = 1 THEN 'System'
                ELSE 'User'
            END as procedure_type,
            'Performance data not available (insufficient permissions)' as data_source
        FROM sys.procedures p
        WHERE p.schema_id = SCHEMA_ID('dbo')
        ORDER BY p.name
        """
        
        with engine.connect() as connection:
            result = connection.execute(text(query))
            return [dict(row._mapping) for row in result.fetchall()]
            
    except Exception as e:
        raise Exception(f"Error fetching basic procedures list: {str(e)}")

def check_performance_permissions() -> bool:
    """
    Check if the current user has permissions to view performance data.
    
    Returns:
        bool: True if permissions are available, False otherwise
    """
    try:
        engine = get_database_connection()
        test_query = """
        SELECT TOP 1 execution_count 
        FROM sys.dm_exec_procedure_stats
        """
        
        with engine.connect() as connection:
            result = connection.execute(text(test_query))
            result.fetchone()  # Try to fetch one row
            return True
            
    except Exception as e:
        if "permission" in str(e).lower() or "denied" in str(e).lower():
            return False
        else:
            # Some other error occurred
            raise Exception(f"Error checking permissions: {str(e)}")