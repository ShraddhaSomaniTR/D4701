import streamlit as st
import pandas as pd
from openai_utils import init_openai, generate_sql_query
from database_utils import get_schema_info, execute_query

def main():
    st.title("Natural Language to SQL Query Converter")
    
    # Initialize OpenAI
    init_openai()
    
    # Get database schema
    schema_info = get_schema_info()
    
    # Display schema information in expandable section
    with st.expander("Database Schema"):
        st.text(schema_info)
    
    # Input for natural language query
    nl_query = st.text_area("Enter your question in natural language:", 
                           height=100,
                           placeholder="Example: Show me all customers from New York ordered by their total purchases")
    
    if st.button("Generate SQL"):
        if nl_query:
            with st.spinner("Generating SQL query..."):
                # Generate SQL query
                sql_query = generate_sql_query(nl_query, schema_info)
                
                # Display the generated SQL
                st.subheader("Generated SQL Query:")
                st.code(sql_query, language="sql")
                
                # Execute query button
                if st.button("Execute Query"):
                    try:
                        with st.spinner("Executing query..."):
                            results = execute_query(sql_query)
                            
                            # Display results as table
                            if results:
                                st.subheader("Query Results:")
                                df = pd.DataFrame(results)
                                st.dataframe(df)
                            else:
                                st.info("Query executed successfully but returned no results.")
                    except Exception as e:
                        st.error(f"Error executing query: {str(e)}")
        else:
            st.warning("Please enter a question first.")

if __name__ == "__main__":
    main()