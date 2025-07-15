from typing import Set, List, Dict
from sqlalchemy import inspect, create_engine
from rapidfuzz import process, fuzz


def get_database_connection():
    """Create database connection using a hardcoded SQL Server connection string."""
    # SQLAlchemy connection string for SQL Server using pyodbc
    connection_string = (
        "mssql+pyodbc://dev-app-db:8mLfkU9Q7ALuTVke@w2-dev-db01.cd701adc0fa4.database.windows.net:1433/SPDEV2007"
        "?driver=ODBC+Driver+17+for+SQL+Server"
    )
    return create_engine(connection_string)
 
def get_relevant_tables_fuzz(
    query_keywords: Set[str], 
    all_tables: List[str], 
    fuzzy_threshold: int = 80  # Adjust threshold as needed
) -> List[str]:
    """
    Find tables relevant to the query using exact, column, and fuzzy matching.
    """
    if not query_keywords or not all_tables:
        return []
 
    # Lowercase for case-insensitive matching
    query_keywords_lc = {kw.lower() for kw in query_keywords}
    table_lc_map = {table.lower(): table for table in all_tables}
    all_tables_lc = list(table_lc_map.keys())
    relevant_tables = set()
 
    # # 1. Exact table name matches
    # for kw in query_keywords_lc:
    #     if kw in table_lc_map:
    #         relevant_tables.add(table_lc_map[kw])
    # if relevant_tables:
    #     return list(relevant_tables)
 
    # # 2. Column name matches
    # try:
    #     engine = get_database_connection()
    #     inspector = inspect(engine)
    #     for table in all_tables:
    #         columns = inspector.get_columns(table)
    #         for col in columns:
    #             if col['name'].lower() in query_keywords_lc:
    #                 relevant_tables.add(table)
    #                 break
    #     if relevant_tables:
    #         return list(relevant_tables)
    # except Exception as e:
    #     print(f"Error checking columns: {str(e)}")
 
    # 3. Fuzzy table name matching
    for kw in query_keywords_lc:
        matches = process.extract(
            kw, 
            all_tables_lc, 
            scorer=fuzz.token_sort_ratio, 
            limit=10
        )
        for match, score, idx in matches:
            if score >= fuzzy_threshold:
                relevant_tables.add(table_lc_map[match])
    if relevant_tables:
        return list(relevant_tables)
 
    # 4. Fuzzy column name matching (optional, can be slow for many tables/columns)
    try:
        engine = get_database_connection()
        inspector = inspect(engine)
        for table in all_tables:
            columns = inspector.get_columns(table)
            col_names = [col['name'].lower() for col in columns]
            for kw in query_keywords_lc:
                matches = process.extract(
                    kw, 
                    col_names, 
                    scorer=fuzz.token_sort_ratio, 
                    limit=10
                )
                for match, score, idx in matches:
                    if score >= fuzzy_threshold:
                        relevant_tables.add(table)
                        break
        if relevant_tables:
            return list(relevant_tables)
    except Exception as e:
        print(f"Error in fuzzy column matching: {str(e)}")
 
    return list(relevant_tables)

def get_relevant_columns_fuzz(
    query_keywords: Set[str],
    table_name: str,
    inspector,
    fuzzy_threshold: int = 80,
    fallback_count: int = 5
) -> List[Dict]:
    """
    Get columns from a table that are likely relevant to the query.
    Prioritizes exact matches, then fuzzy matches, then id/primary key columns, then fallback.
    """
    if not query_keywords or not table_name or not inspector:
        return []
    all_columns = inspector.get_columns(table_name)
    if not all_columns:
        return []
 
    query_keywords_lc = {kw.lower() for kw in query_keywords}
    relevant_columns = []
 
    # # 1. Exact column name matches
    # for col in all_columns:
    #     col_name_lower = col['name'].lower()
    #     if col_name_lower in query_keywords_lc:
    #         relevant_columns.append(col)
    # if relevant_columns:
    #     return relevant_columns
 
    # 2. Fuzzy column name matches
    col_names_lc = [col['name'].lower() for col in all_columns]
    matched_indices = set()
    for kw in query_keywords_lc:
        matches = process.extract(
            kw,
            col_names_lc,
            scorer=fuzz.token_sort_ratio,
            limit=2
        )
        for match, score, idx in matches:
            if score >= fuzzy_threshold and idx not in matched_indices:
                relevant_columns.append(all_columns[idx])
                matched_indices.add(idx)
    if relevant_columns:
        return relevant_columns
 
    # 3. If still no matches, include primary key and ID columns
    for col in all_columns:
        col_name_lower = col['name'].lower()
        if (
            'id' in col_name_lower or 
            col.get('primary_key', False) or
            col_name_lower.endswith('_id')
        ):
            relevant_columns.append(col)
    if relevant_columns:
        return relevant_columns
 
    # 4. Fallback: If still no relevant columns found, include first N columns
    return all_columns[:fallback_count]