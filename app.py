import streamlit as st
import pandas as pd
from openai_utils import generate_sql_query
from database_utils import get_schema_info, get_filtered_schema_info, execute_query

def main():
    st.title("Natural Language to SQL Query Converter")
    
    # Schema filtering options
    use_smart_filtering = st.sidebar.checkbox("🧠 Smart Schema Filtering", value=True, 
                                             help="Filter schema based on your query to reduce message size")
    
    # Input for natural language query
    nl_query = st.text_area("Enter your question in natural language:", 
                           height=100,
                           placeholder="Example: Show me all customers from New York ordered by their total purchases")
    
    # Get schema information based on filtering option
    if nl_query and use_smart_filtering:
        schema_info = get_filtered_schema_info(nl_query)
        schema_type = "Filtered (Smart)"
    else:
        schema_info = get_schema_info()
        schema_type = "Full Schema"
    
    # Debug information
    with st.expander("🐛 Debug Info", expanded=False):
        st.write(f"**Schema Type:** {schema_type}")
        st.write(f"**Schema Length:** {len(schema_info)} characters")
        st.write(f"**Schema Size:** {len(schema_info.encode('utf-8'))} bytes")
        
        if nl_query and use_smart_filtering:
            from database_utils import extract_keywords_from_query
            keywords = extract_keywords_from_query(nl_query)
            st.write(f"**Extracted Keywords:** {', '.join(keywords) if keywords else 'None'}")
        
        st.text_area("Schema Content:", value=schema_info, height=150, disabled=True)
        
        # WebSocket size check
        if len(schema_info.encode('utf-8')) > 25000:
            st.error("⚠️ Schema might be too large for WebSocket!")
        else:
            st.success("✅ Schema size looks good for WebSocket")

    # Display schema information in expandable section
    with st.expander("🗄️ Database Schema"):
        st.text(schema_info)
    
    if st.button("🔮 Generate SQL", type="primary"):
        if nl_query:
            # Show message size info
            total_message_size = len(nl_query) + len(schema_info)
            st.info(f"📊 Total message size: {total_message_size} characters")
            
            if total_message_size > 25000:
                st.warning("⚠️ Large message detected - enable Smart Schema Filtering")
            
            with st.spinner("Generating SQL query..."):
                try:
                    # Generate SQL query with filtered schema
                    sql_query = generate_sql_query(nl_query, schema_info)
                    
                    # Display the generated SQL
                    st.subheader("📝 Generated SQL Query:")
                    st.code(sql_query, language="sql")
                    
                    # Execute query button
                    if st.button("▶️ Execute Query", type="secondary"):
                        try:
                            with st.spinner("Executing query..."):
                                results = execute_query(sql_query)
                                
                                # Display results as table
                                if results:
                                    st.subheader("📊 Query Results:")
                                    df = pd.DataFrame(results)
                                    st.dataframe(df, use_container_width=True)
                                    st.info(f"✅ Query returned **{len(results)}** rows")
                                else:
                                    st.info("✅ Query executed successfully but returned no results.")
                        except Exception as e:
                            st.error(f"❌ Error executing query: {str(e)}")
                            
                except Exception as e:
                    error_msg = str(e)
                    st.error(f"❌ Error generating SQL query: {error_msg}")
                    
                    if "message too big" in error_msg.lower():
                        st.info("💡 Try enabling Smart Schema Filtering to reduce message size")
        else:
            st.warning("⚠️ Please enter a question first.")

if __name__ == "__main__":
    main()