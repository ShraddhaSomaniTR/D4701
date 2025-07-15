import streamlit as st
import pandas as pd
import re
from openai_utils import generate_sql_query
from database_utils import get_schema_info, get_filtered_schema_info, execute_query

def clean_sql_query(sql_query: str) -> str:
    """
    Clean SQL query by removing markdown code fences and extra whitespace.
    
    Args:
        sql_query (str): Raw SQL query from AI
        
    Returns:
        str: Cleaned SQL query
    """
    # Remove markdown code fences (```sql and ```)
    cleaned = re.sub(r'```sql\s*', '', sql_query)
    cleaned = re.sub(r'```\s*$', '', cleaned)
    
    # Remove any remaining backticks
    cleaned = cleaned.replace('`', '')
    
    # Strip whitespace
    cleaned = cleaned.strip()
    
    return cleaned

def generate_sql_tool():
    """Tool 1: Generate SQL Query functionality"""
    st.title("🔮 Generate SQL Query")
    
    # Smart schema filtering is now always enabled (removed from UI)
    use_smart_filtering = True
    
    # Input for natural language query
    nl_query = st.text_area("Enter your question in natural language:", 
                           height=100,
                           placeholder="Example: Show me all customers from New York ordered by their total purchases")
    
    # Store generated SQL in session state
    if 'generated_sql' not in st.session_state:
        st.session_state.generated_sql = None

    # Generate SQL Button
    if st.button("🔮 Generate SQL", type="primary"):
        if nl_query:
            # Get schema information with smart filtering always enabled
            schema_info = get_filtered_schema_info(nl_query)
            schema_type = "Smart Filtered"
            
            # Display schema information in expandable section
            with st.expander("🗄️ Database Schema"):
                st.text(schema_info)
            total_message_size = len(nl_query) + len(schema_info)
            st.info(f"📊 Total message size: {total_message_size} characters")
            if total_message_size > 25000:
                st.warning("⚠️ Large message detected - consider optimizing the query")
            with st.spinner("Generating SQL query..."):
                try:
                    # Generate SQL query with filtered schema
                    raw_sql_query = generate_sql_query(nl_query, schema_info)
                    # Clean the SQL query to remove markdown formatting
                    cleaned_sql_query = clean_sql_query(raw_sql_query)
                    st.session_state.generated_sql = cleaned_sql_query  # Store cleaned SQL in session state
                    # Display the generated SQL
                    st.subheader("📝 Generated SQL Query:")
                    st.code(cleaned_sql_query, language="sql")
                except Exception as e:
                    error_msg = str(e)
                    st.error(f"❌ Error generating SQL query: {error_msg}")
                    if "message too big" in error_msg.lower():
                        st.info("💡 The system automatically filters the schema to reduce message size")
        else:
            st.warning("⚠️ Please enter a question first.")
 
    # Execute Query Button (moved outside the Generate SQL button block)
    if st.session_state.generated_sql is not None:
        if st.button("▶️ Execute Query", type="secondary"):
            try:
                with st.spinner("Executing query..."):
                    results = execute_query(st.session_state.generated_sql)
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

def optimize_sp_tool():
    """Tool 2: Optimize SP functionality"""
    st.title("⚡ Optimize Stored Procedures")
    
    # Import the new functions
    from database_utils import (get_stored_procedures, get_stored_procedure_definition, 
                               get_stored_procedure_parameters, analyze_stored_procedure_performance, get_stored_procedures, 
                               check_performance_permissions, get_stored_procedures_with_performance)
    from openai_utils import optimize_stored_procedure, analyze_stored_procedure_issues
    
    # Tab selection for different optimization features
    tab1, tab2, tab3 = st.tabs(["🔧 Optimize SP", "📊 Analyze Performance", "🔍 Code Review"])
    
    with tab1:
        st.header("Stored Procedure Optimization")
        
        # Option to select existing SP or paste custom code
        input_method = st.radio("Select input method:", 
                               ["Select from Database", "Paste Custom Code"])
        
        if input_method == "Select from Database":
            try:
                # Get list of stored procedures
                procedures = get_stored_procedures()
                
                if procedures:
                    selected_procedure = st.selectbox("Select a stored procedure:", 
                                                    [""] + procedures)
                    
                    if selected_procedure:
                        # Get procedure definition
                        with st.spinner("Loading stored procedure..."):
                            procedure_def = get_stored_procedure_definition(selected_procedure)
                            parameters = get_stored_procedure_parameters(selected_procedure)
                        
                        # Display current procedure
                        st.subheader("📋 Current Stored Procedure")
                        st.code(procedure_def, language="sql")
                        
                        # Display parameters if any
                        if parameters:
                            st.subheader("📝 Parameters")
                            param_df = pd.DataFrame(parameters)
                            st.dataframe(param_df, use_container_width=True)
                        
                        # Optimization button
                        if st.button("🚀 Optimize Stored Procedure", type="primary"):
                            with st.spinner("Optimizing stored procedure..."):

                                optimized_proc, suggestions, system_prompt = optimize_stored_procedure(
                                    procedure_def, selected_procedure
                                )
                                # Display results
                                st.subheader("✨ Optimized Stored Procedure")
                                st.code(optimized_proc, language="sql")
                                
                                st.subheader("💡 Optimization Suggestions")
                                st.markdown(suggestions)
                                
                                # # Debug info
                                # with st.expander("🛠️ System Prompt (for debugging)"):
                                #     st.text(system_prompt)
                else:
                    st.warning("No stored procedures found in the database.")
                    
            except Exception as e:
                st.error(f"Error loading stored procedures: {str(e)}")
        
        else:  # Paste Custom Code
            st.subheader("📝 Paste Your Stored Procedure Code")
            custom_procedure = st.text_area("Stored Procedure Code:", 
                                          height=300,
                                          placeholder="CREATE PROCEDURE [dbo].[YourProcedureName]...")
            
            procedure_name = st.text_input("Procedure Name (optional):", 
                                         placeholder="MyStoredProcedure")
            
            if st.button("🚀 Optimize Custom Procedure", type="primary"):
                if custom_procedure:
                    with st.spinner("Optimizing stored procedure..."):
                        
                        optimized_proc, suggestions, system_prompt = optimize_stored_procedure(
                            custom_procedure, procedure_name or "CustomProcedure"
                        )
                        
                        # Display results
                        st.subheader("✨ Optimized Stored Procedure")
                        st.code(optimized_proc, language="sql")
                        
                        st.subheader("💡 Optimization Suggestions")
                        st.markdown(suggestions)
                        
                        # Debug info
                        with st.expander("🛠️ System Prompt (for debugging)"):
                            st.text(system_prompt)
                else:
                    st.warning("Please paste your stored procedure code.")
    
    # Update the performance analysis section in optimize_sp_tool():

    with tab2:
        st.header("📊 Performance Analysis")
    
    # Check permissions first
        try:
            has_perf_permissions = check_performance_permissions()
            if not has_perf_permissions:
                st.warning("⚠️ **Limited Performance Data Available**")
                st.info("Your database user doesn't have `VIEW SERVER PERFORMANCE STATE` permission. "
                       "Basic procedure information will be shown instead of detailed performance metrics.")
        except Exception as e:
            st.error(f"Error checking permissions: {str(e)}")
            has_perf_permissions = False
    
        try:
            # Option to view all procedures with performance or analyze specific one
            analysis_type = st.radio("Analysis Type:", 
                                   ["All Procedures Overview", "Detailed Analysis"])
        
            if analysis_type == "All Procedures Overview":
                with st.spinner("Loading stored procedures..."):
                    procedures_perf = get_stored_procedures_with_performance()
            
                if procedures_perf:
                    st.subheader("📈 Stored Procedures Overview")
                
                    # Convert to DataFrame for better display
                    df = pd.DataFrame(procedures_perf)
                
                    # Check if we have performance data or just basic info
                    if 'execution_count' in df.columns and df['execution_count'].sum() > 0:
                        # We have performance data
                        if 'avg_elapsed_time' in df.columns:
                            df['avg_elapsed_time_ms'] = (df['avg_elapsed_time'] / 1000).round(2)
                        if 'total_elapsed_time' in df.columns:
                            df['total_elapsed_time_ms'] = (df['total_elapsed_time'] / 1000).round(2)
                    
                        # Display the dataframe with performance columns
                        display_cols = ['procedure_name', 'execution_count', 'avg_elapsed_time_ms', 
                                       'total_elapsed_time_ms', 'last_execution_time']
                        available_cols = [col for col in display_cols if col in df.columns]
                        st.dataframe(df[available_cols], use_container_width=True)
                    
                        # Show top performers if we have performance data
                        if len(df) > 0 and 'execution_count' in df.columns:
                            st.subheader("🏆 Top Performers")
                        
                            col1, col2 = st.columns(2)
                        
                            with col1:
                                st.write("**Most Executed Procedures:**")
                                top_executed = df.nlargest(5, 'execution_count')[['procedure_name', 'execution_count']]
                                st.dataframe(top_executed, use_container_width=True)
                        
                            with col2:
                                if 'avg_elapsed_time_ms' in df.columns:
                                    st.write("**Slowest Average Execution:**")
                                    slowest = df.nlargest(5, 'avg_elapsed_time_ms')[['procedure_name', 'avg_elapsed_time_ms']]
                                    st.dataframe(slowest, use_container_width=True)
                                else:
                                    st.write("**Recently Modified:**")
                                    recent = df.nlargest(5, 'modify_date')[['procedure_name', 'modify_date']]
                                    st.dataframe(recent, use_container_width=True)
                    else:
                        # We only have basic info
                        basic_cols = ['procedure_name', 'create_date', 'modify_date', 'procedure_type']
                        available_cols = [col for col in basic_cols if col in df.columns]
                        st.dataframe(df[available_cols], use_container_width=True)
                    
                        st.info("💡 **Note:** Performance metrics are not available due to insufficient permissions. "
                               "Contact your database administrator to grant `VIEW SERVER PERFORMANCE STATE` permission for detailed metrics.")
                else:
                    st.warning("No stored procedures found.")
        
            else:  # Detailed Analysis
                procedures = get_stored_procedures()
            
                if procedures:
                    selected_procedure = st.selectbox("Select a stored procedure for detailed analysis:", 
                                                    [""] + procedures, key="perf_analysis")
                
                    if selected_procedure:
                        with st.spinner("Analyzing procedure..."):
                            performance_data = analyze_stored_procedure_performance(selected_procedure)
                    
                        if 'execution_count' in performance_data and performance_data.get('execution_count', 0) > 0:
                            # We have performance data
                            st.subheader("📈 Detailed Performance Metrics")
                        
                            # Create metrics columns
                            col1, col2, col3, col4 = st.columns(4)
                        
                            with col1:
                                st.metric("Execution Count", performance_data.get('execution_count', 0))
                            with col2:
                                st.metric("Total Elapsed Time (ms)", 
                                         f"{performance_data.get('total_elapsed_time', 0)/1000:.2f}")
                            with col3:
                                st.metric("Avg Elapsed Time (ms)", 
                                         f"{performance_data.get('avg_elapsed_time', 0)/1000:.2f}")
                            with col4:
                                st.metric("Total Logical Reads", performance_data.get('total_logical_reads', 0))
                        
                            # Additional metrics if available
                            if performance_data.get('avg_logical_reads', 0) > 0:
                                col5, col6, col7, col8 = st.columns(4)
                            
                                with col5:
                                    st.metric("Avg Logical Reads", performance_data.get('avg_logical_reads', 0))
                                with col6:
                                    st.metric("Total Logical Writes", performance_data.get('total_logical_writes', 0))
                                with col7:
                                    st.metric("Avg Logical Writes", performance_data.get('avg_logical_writes', 0))
                                with col8:
                                    st.metric("Last Execution", 
                                             str(performance_data.get('last_execution_time', 'N/A'))[:19])
                        
                            # Performance insights
                            st.subheader("🔍 Performance Insights")
                        
                            avg_elapsed = performance_data.get('avg_elapsed_time', 0)
                            avg_reads = performance_data.get('avg_logical_reads', 0)
                            execution_count = performance_data.get('execution_count', 0)
                        
                            insights = []
                        
                            if avg_elapsed > 1000000:  # > 1 second
                                insights.append("⚠️ **High average execution time** - Consider query optimization")
                        
                            if avg_reads > 10000:
                                insights.append("⚠️ **High logical reads** - Consider index optimization")
                        
                            if execution_count > 10000:
                                insights.append("ℹ️ **Frequently executed procedure** - Optimization could have significant impact")
                        
                            if not insights:
                                insights.append("✅ **Performance looks good** - No major issues detected")
                        
                            for insight in insights:
                                st.markdown(insight)
                    
                        else:
                            # Show basic info when performance data is not available
                            st.subheader("📋 Basic Procedure Information")
                        
                            if 'create_date' in performance_data:
                                col1, col2 = st.columns(2)
                            
                                with col1:
                                    st.metric("Created", str(performance_data.get('create_date', 'N/A'))[:19])
                                with col2:
                                    st.metric("Modified", str(performance_data.get('modify_date', 'N/A'))[:19])
                        
                            if 'performance_note' in performance_data:
                                st.info(f"💡 {performance_data['performance_note']}")
                            else:
                                st.info("No performance data available for this stored procedure. "
                                       "The procedure may not have been executed since the last server restart, "
                                       "or you may not have sufficient permissions to view performance statistics.")
                else:
                    st.warning("No stored procedures found in the database.")
                
        except Exception as e:
            st.error(f"Error in performance analysis: {str(e)}")
    
    with tab3:
        st.header("🔍 Code Review & Best Practices")
        
        # Similar to optimization tab but focused on code review
        input_method = st.radio("Select input method:", 
                               ["Select from Database", "Paste Custom Code"], key="code_review")
        
        if input_method == "Select from Database":
            try:
                procedures = get_stored_procedures()
                
                if procedures:
                    selected_procedure = st.selectbox("Select a stored procedure for review:", 
                                                    [""] + procedures, key="code_review_select")
                    
                    if selected_procedure:
                        with st.spinner("Loading stored procedure..."):
                            procedure_def = get_stored_procedure_definition(selected_procedure)
                        
                        st.subheader("📋 Current Stored Procedure")
                        st.code(procedure_def, language="sql")
                        
                        if st.button("🔍 Analyze Code", type="primary"):
                            with st.spinner("Analyzing code for issues..."):
                                analysis_report, system_prompt = analyze_stored_procedure_issues(
                                    procedure_def, selected_procedure
                                )
                                
                                st.subheader("📋 Code Analysis Report")
                                st.markdown(analysis_report)
                                
                                # Debug info
                                with st.expander("🛠️ System Prompt (for debugging)"):
                                    st.text(system_prompt)
                else:
                    st.warning("No stored procedures found in the database.")
                    
            except Exception as e:
                st.error(f"Error loading stored procedures: {str(e)}")
        
        else:  # Paste Custom Code
            st.subheader("📝 Paste Your Stored Procedure Code")
            custom_procedure = st.text_area("Stored Procedure Code:", 
                                          height=300,
                                          placeholder="CREATE PROCEDURE [dbo].[YourProcedureName]...",
                                          key="custom_code_review")
            
            procedure_name = st.text_input("Procedure Name (optional):", 
                                         placeholder="MyStoredProcedure",
                                         key="custom_name_review")
            
            if st.button("🔍 Analyze Custom Code", type="primary"):
                if custom_procedure:
                    with st.spinner("Analyzing code for issues..."):
                        analysis_report, system_prompt = analyze_stored_procedure_issues(
                            custom_procedure, procedure_name or "CustomProcedure"
                        )
                        
                        st.subheader("📋 Code Analysis Report")
                        st.markdown(analysis_report)
                        
                        # Debug info
                        with st.expander("🛠️ System Prompt (for debugging)"):
                            st.text(system_prompt)
                else:
                    st.warning("Please paste your stored procedure code.")

def main():
    # Sidebar for tool selection
    st.sidebar.title("🛠️ Tools")
    
    # Tool selection
    selected_tool = st.sidebar.radio(
        "Select a tool:",
        ["Tool 1: Generate SQL Query", "Tool 2: Optimize SP"],
        index=0
    )
    
    # Display selected tool
    if selected_tool == "Tool 1: Generate SQL Query":
        generate_sql_tool()
    elif selected_tool == "Tool 2: Optimize SP":
        optimize_sp_tool()

if __name__ == "__main__":
    main()