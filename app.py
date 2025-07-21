import streamlit as st
import pandas as pd
import re
from flashtext import KeywordProcessor
from openai_utils import generate_sql_query
from database_utils import get_schema_info, get_filtered_schema_info, execute_query
from Keywordmatcher import load_keywords, initialize_keyword_processor
import json
import time

# Page configuration
st.set_page_config(
    page_title="SQL Genie",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling and accessibility
st.markdown("""
<style>
    .main-header {
        font-size: 10rem;
        color: #1e3a8a;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: bold;
    }
    
    .tool-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        margin: 1rem 0;
    }
    
    .metric-card {
        background: #f8fafc;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #3b82f6;
        margin: 0.5rem 0;
    }
    
    .success-message {
        background: #d1fae5;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #10b981;
        color: #065f46;
    }
    
    .warning-message {
        background: #fef3c7;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #f59e0b;
        color: #92400e;
    }
    
    .help-tooltip {
        background: #eff6ff;
        padding: 0.8rem;
        border-radius: 6px;
        border: 1px solid #bfdbfe;
        font-size: 0.9rem;
        margin: 0.5rem 0;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* Accessibility improvements */
    .stButton > button:focus {
        outline: 2px solid #3b82f6;
        outline-offset: 2px;
    }
    
    /* Keyboard shortcuts info */
    .keyboard-shortcuts {
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: rgba(0,0,0,0.8);
        color: white;
        padding: 10px;
        border-radius: 5px;
        font-size: 0.8rem;
        display: none;
    }
    
    /* Animation for success messages */
    @keyframes slideIn {
        from { opacity: 0; transform: translateY(-10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .success-message {
        animation: slideIn 0.3s ease-out;
    }
</style>
""", unsafe_allow_html=True)

def show_welcome_message():
    """Display welcome message and app overview"""
    st.markdown('<h1 class="main-header" style="margin-top: -80px ; font-size:70px">🤖 SQL Genie</h1>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 5, 1])
    with col2:
        st.markdown("""
        <div style="text-align: center; padding: 0.5rem; background: #f1f5f9; border-radius: 10px;">
            <h4>Welcome to your intelligent SQL companion!</h4>
            <p>Generate SQL queries from natural language and optimize stored procedures with AI assistance.</p>
        </div>
        """, unsafe_allow_html=True)

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

def show_help_section(tool_name):
    """Display contextual help for each tool"""
    help_content = {
        "SQL Generator": {
            "title": "🔮 SQL Query Generator Help",
            "content": """
            **How to use:**
            1. Type your question in plain English
            2. Use business-friendly terms (they'll be automatically translated)
            3. Click "Generate SQL" to get your query
            4. Review and execute the query
            
            **Example queries:**
            - "Show me all completed jobs from last month"
            - "Find all CCH binders with errors"
            - "List emails for pending engagements"
            
            **Tips:**
            - Be specific about date ranges and conditions
            - Use familiar business terms instead of technical column names
            """
        },
        "SP Optimizer": {
            "title": "⚡ Stored Procedure Optimizer Help",
            "content": """
            **Features:**
            - **Optimize:** Improve performance and code quality
            - **Performance Analysis:** View execution statistics
            - **Code Review:** Check for best practices and issues
            
            **What gets optimized:**
            - Query performance and indexing
            - Parameter usage and security
            - Error handling
            - Code readability
            """
        }
    }
    
    if tool_name in help_content:
        with st.expander("❓ Need Help?", expanded=False):
            help_info = help_content[tool_name]
            st.markdown(f"### {help_info['title']}")
            st.markdown(help_info['content'])

def show_feedback_section():
    """Display feedback collection section"""
    with st.expander("💬 Feedback & Suggestions", expanded=False):
        st.markdown("Help us improve the AI SQL Assistant!")
        
        col1, col2 = st.columns(2)
        
        with col1:
            rating = st.select_slider(
                "Rate your experience:",
                options=[1, 2, 3, 4, 5],
                value=5,
                format_func=lambda x: "⭐" * x
            )
        
        with col2:
            feature_request = st.selectbox(
                "What feature would you like to see?",
                [
                    "Select an option",
                    "More example queries",
                    "Query history",
                    "Saved queries",
                    "Better error messages",
                    "Query performance insights",
                    "Data visualization",
                    "Export options"
                ]
            )
        
        feedback_text = st.text_area(
            "Additional feedback:",
            placeholder="Tell us what you think or suggest improvements..."
        )
        
        if st.button("📤 Submit Feedback"):
            # In a real application, you would save this to a database or send via email
            st.success("Thank you for your feedback! We appreciate your input.")
            st.balloons()

def show_query_history():
    """Display query history functionality"""
    if 'query_history' not in st.session_state:
        st.session_state.query_history = []
    
    with st.expander("🕒 Query History", expanded=False):
        if st.session_state.query_history:
            st.markdown("**Recent Queries:**")
            for i, (timestamp, query, sql) in enumerate(reversed(st.session_state.query_history[-10:])):
                with st.container():
                    col1, col2, col3 = st.columns([2, 3, 1])
                    with col1:
                        st.text(timestamp.strftime("%H:%M:%S"))
                    with col2:
                        st.text(query[:50] + "..." if len(query) > 50 else query)
                    with col3:
                        if st.button("🔄", key=f"rerun_{i}", help="Rerun this query"):
                            st.session_state.query_input = query
                            st.rerun()
        else:
            st.info("No query history yet. Run some queries to see them here!")

def add_to_query_history(query, sql):
    """Add a query to the history"""
    if 'query_history' not in st.session_state:
        st.session_state.query_history = []
    
    import datetime
    st.session_state.query_history.append((datetime.datetime.now(), query, sql))
    
    # Keep only last 50 queries
    if len(st.session_state.query_history) > 50:
        st.session_state.query_history = st.session_state.query_history[-50:]

def show_app_status():
    """Show application status and statistics"""
    with st.expander("📊 App Status", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Session Queries", len(st.session_state.get('query_history', [])))
            st.metric("Active Features", "2")  # SQL Generator and SP Optimizer
        
        with col2:
            st.metric("Database Status", "🟢 Connected")
            st.metric("AI Service", "🟢 Online")
        
        # Show memory usage if available
        try:
            import psutil
            memory_percent = psutil.virtual_memory().percent
            st.progress(memory_percent / 100)
            st.caption(f"Memory Usage: {memory_percent:.1f}%")
        except:
            st.caption("Memory info not available")

def generate_sql_tool(keyword_processor, ui_config=None):
    """Tool 1: Generate SQL Query functionality with enhanced UI"""
    
    if ui_config is None:
        ui_config = load_ui_config()
    

    # st.title("🔮 Generate SQL Query")
    st.markdown('<h2 style="margin-top:-30px">🔮 Generate SQL Query</h2>', unsafe_allow_html=True)


    # User-friendly input section
    st.markdown('<p style="margin-left:10px"> 💬 What would you like to know? </p>', unsafe_allow_html=True)
    
    # Example queries for inspiration
    with st.expander("💡 Example Queries", expanded=False):
        examples = ui_config.get("example_queries", [
            "Show me all completed jobs from last month",
            "Find all CCH binders with errors",
            "List all pending engagements with their emails"
        ])
        
        max_examples = ui_config.get("ui_settings", {}).get("max_query_examples", 5)
        examples = examples[:max_examples]
        
        for i, example in enumerate(examples):
            if st.button(f"📝 {example}", key=f"example_{i}"):
                st.session_state.query_input = example
                st.rerun()
    

    query_placeholder = "Example: Show me all customers from New York ordered by their total purchases"
        
    raw_nl_query = st.text_area(
            "Enter your question in natural language:", 
            height=120,
            placeholder=query_placeholder,
            value=st.session_state.get('query_input',''),
            help="Describe what data you want to see in plain English. Use business terms - they'll be automatically translated to database terms.",
            key="query_text_area"
    )
       
        # with col2:
        #     st.markdown("<br>", unsafe_allow_html=True)  # Add some spacing to align with text area
        #     if st.button("🗑️", help="Clear the query input", key="clear_query"):
        #         st.session_state['query_text_area'] = ""
        #         # Clear the actual text area by rerunning
        #         # st.rerun()
    
    # Clear the session state after using it
    if 'query_input' in st.session_state:
        del st.session_state.query_input
    
    nl_query = keyword_processor.replace_keywords(raw_nl_query)
    
    # # Show keyword replacements if any were made
    # if raw_nl_query != nl_query and raw_nl_query:
    #     st.markdown("### 🔄 Business Terms Translated:")
    #     col1, col2 = st.columns(2)
    #     with col1:
    #         st.markdown("**Your Input:**")
    #         st.code(raw_nl_query, language="text")
    #     with col2:
    #         st.markdown("**Translated Query:**")
    #         st.code(nl_query, language="text")
    
    # Initialize session state for SQL and other states
    if 'generated_sql' not in st.session_state:
        st.session_state.generated_sql = None
    if 'query_results' not in st.session_state:
        st.session_state.query_results = None
    if 'modify_mode' not in st.session_state:
        st.session_state.modify_mode = False

    # Generate SQL Button with better styling
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        generate_button = st.button(
            "🔮 Generate SQL Query", 
            type="primary", 
            use_container_width=True,
            disabled=not nl_query.strip()
        )

    if generate_button:
        if nl_query:
            # Progress indicators
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # Step 1: Get schema
                status_text.text("🔍 Analyzing database schema...")
                progress_bar.progress(25)
                
                schema_info = get_filtered_schema_info(nl_query)
                
                # Step 2: Calculate message size
                status_text.text("📊 Optimizing query parameters...")
                progress_bar.progress(50)
                
                total_message_size = len(nl_query) + len(schema_info)
                
                # Step 3: Generate SQL
                status_text.text("🤖 Generating SQL with AI...")
                progress_bar.progress(75)
                
                raw_sql_query = generate_sql_query(nl_query, schema_info)
                cleaned_sql_query = clean_sql_query(raw_sql_query)
                st.session_state.generated_sql = cleaned_sql_query
                
                # Add to query history
                add_to_query_history(nl_query, cleaned_sql_query)
                
                # Step 4: Complete
                status_text.text("✅ SQL query generated successfully!")
                progress_bar.progress(100)
                time.sleep(0.5)
                
                # Clear progress indicators
                progress_bar.empty()
                status_text.empty()
                
                # Success message
                st.markdown("""
                <div class="success-message">
                    <strong>🎉 Success!</strong> Your SQL query has been generated and is ready to execute.
                </div>
                """, unsafe_allow_html=True)
                
            except Exception as e:
                progress_bar.empty()
                status_text.empty()
                error_msg = str(e)
                st.error(f"❌ Error generating SQL query: {error_msg}")
                if "message too big" in error_msg.lower():
                    st.info("💡 Try making your query more specific to reduce schema complexity")
        else:
            st.warning("⚠️ Please enter a question first.")
 
    # Display Generated SQL Section - This should ALWAYS show if SQL exists
    if st.session_state.generated_sql is not None:
        st.markdown("### 📝 Generated SQL Query:")
        # Remove the column layout and display SQL at full width
        st.code(st.session_state.generated_sql, language="sql")
    
    # Execute Query Section with enhanced UI
    if st.session_state.generated_sql is not None:
        st.markdown("---")
        st.markdown("### ▶️ Execute Your Query")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            execute_button = st.button("▶️ Execute Query", type="secondary", use_container_width=True)
        
        # with col2:
        #     if st.button("📊 Explain Query", use_container_width=True):
        #         with st.expander("📖 Query Explanation", expanded=True):
        #             st.info("This feature will explain what the SQL query does in plain English. (Feature coming soon!)")
        
        with col2:
            if st.button("🔄 Modify Query", use_container_width=True):
                st.session_state.modify_mode = True
                st.rerun()  # Refresh to show modify mode
        
        # Query modification mode
        if st.session_state.get('modify_mode', False):
            st.markdown("#### ✏️ Modify Your Query")
            modified_sql = st.text_area(
                "Edit your SQL query:",
                value=st.session_state.generated_sql,
                height=150,
                key="modified_sql"
            )
            
            col1, col2, col3 = st.columns([1,1,4.5])
            with col1:
                if st.button("💾 Save Changes"):
                    st.session_state.generated_sql = modified_sql
                    st.session_state.modify_mode = False
                    st.success("Query updated!")
                    st.rerun()
            with col2:
                if st.button("❌ Cancel"):
                    st.session_state.modify_mode = False
                    st.rerun()

        
        if execute_button:
            try:
                execution_start = time.time()
                
                with st.spinner("🚀 Executing query..."):
                    results = execute_query(st.session_state.generated_sql)
                
                execution_time = time.time() - execution_start
                
                # Display results with enhanced formatting
                if results:
                    st.markdown("### 📊 Query Results:")
                    
                    # Results metrics
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Rows Returned", len(results))
                    with col2:
                        st.metric("Execution Time", f"{execution_time:.2f}s")
                    with col3:
                        st.metric("Columns", len(results[0].keys()) if results else 0)
                    
                    # Results table
                    df = pd.DataFrame(results)
                    st.dataframe(
                        df, 
                        use_container_width=True,
                        height=400
                    )
                    
                    # # Download option
                    # csv = df.to_csv(index=False)
                    # st.download_button(
                    #     label="📥 Download as CSV",
                    #     data=csv,
                    #     file_name="query_results.csv",
                    #     mime="text/csv"
                    # )
                    
                    st.session_state.query_results = results
                else:
                    st.markdown("""
                    <div class="help-tooltip">
                        <strong>✅ Query executed successfully!</strong><br>
                        No rows were returned. This might mean:
                        <ul>
                            <li>Your filters didn't match any data</li>
                            <li>The table is empty</li>
                            <li>This was an UPDATE/INSERT/DELETE query</li>
                        </ul>
                    </div>
                    """, unsafe_allow_html=True)
                    
            except Exception as e:
                st.error(f"❌ Error executing query: {str(e)}")
                
                # Help with common errors
                error_str = str(e).lower()
                if "invalid column name" in error_str:
                    st.info("💡 **Tip:** The column name might not exist. Try rephrasing your question.")
                elif "syntax error" in error_str:
                    st.info("💡 **Tip:** There's a SQL syntax error. You can modify the query above.")
                elif "permission" in error_str:
                    st.info("💡 **Tip:** You might not have permission to access this data.")

def optimize_sp_tool():
    """Tool 2: Optimize SP functionality with enhanced UI"""
    

    # st.title("⚡ Optimize Stored Procedures")
    st.markdown('<h2 style="margin-top:-30px">⚡ Optimize Stored Procedures</h2>', unsafe_allow_html=True)
    
    # Import the new functions
    from database_utils import (get_stored_procedures, get_stored_procedure_definition, 
                               get_stored_procedure_parameters, analyze_stored_procedure_performance, get_stored_procedures, 
                               check_performance_permissions, get_stored_procedures_with_performance)
    from openai_utils import optimize_stored_procedure, analyze_stored_procedure_issues
    
    # Enhanced tab selection with descriptions
    tab1, tab2, tab3 = st.tabs([
        "🔧 Optimize Code", 
        "📊 Performance Analysis", 
        "🔍 Code Review"
    ])
    
    with tab1:
        st.markdown("### 🔧 Stored Procedure Optimization")
        st.markdown("Improve performance, security, and maintainability of your stored procedures.")
        
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
    
    with tab2:
        st.markdown("### 📊 Performance Analysis")
    
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
        st.markdown("### 🔍 Code Review & Best Practices")
        
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

# Load UI configuration
@st.cache_data
def load_ui_config():
    """Load UI configuration from file"""
    try:
        with open("ui_config.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        # Default configuration if file doesn't exist
        return {
            "ui_settings": {
                "theme": "light",
                "show_welcome_by_default": True,
                "enable_copy_feature": True,
                "show_debug_info": False,
                "max_query_examples": 5,
                "default_table_height": 400
            },
            "example_queries": [
                "Show me all completed jobs from last month",
                "Find all CCH binders with errors",
                "List all pending engagements with their emails"
            ],
            "help_tooltips": {}
        }

def main():
    # Load configurations
    ui_config = load_ui_config()
    ui_settings = ui_config.get("ui_settings", {})
    
    # Initialize session state
    if 'show_welcome' not in st.session_state:
        st.session_state.show_welcome = ui_settings.get("show_welcome_by_default", True)
    
    # Load configuration
    with open("userfriendly.json", "r") as config_file:
        config_data = json.load(config_file)
    
    keywords = config_data[0] if isinstance(config_data, list) and len(config_data) > 0 else {}
    keyword_processor = initialize_keyword_processor(keywords)
    
    # Enhanced sidebar
    with st.sidebar:
        st.markdown("## 🛠️ AI SQL Assistant")
        
        # Show welcome 
        st.session_state.show_welcome = True
        
        st.markdown("---")
        
        # Tool selection with enhanced styling
        st.markdown("### Choose Your Tool")
        
        # Tool descriptions
        tool_descriptions = {
            "Tool 1: Generate SQL Query": "🔮 SQL Generator",
            "Tool 2: Optimize SP": "⚡ SP Optimization"
        }
        
        selected_tool = st.radio(
            "Select a tool:",
            list(tool_descriptions.keys()),
            format_func=lambda x: tool_descriptions[x],
            index=0
        )
        
        # Add new interactive features
        st.markdown("---")
        show_query_history()

        st.markdown("---")
        show_app_status()
        
        st.markdown("---")
        show_feedback_section()
        
    
    # Main content area
    if st.session_state.show_welcome:
        show_welcome_message()
        st.markdown("---")
    
    # Display selected tool
    if selected_tool == "Tool 1: Generate SQL Query":
        generate_sql_tool(keyword_processor, ui_config)
    elif selected_tool == "Tool 2: Optimize SP":
        optimize_sp_tool()
    
    # Show feedback and query history sections
    st.markdown("---")
    show_app_status()

    st.markdown("---")
    show_feedback_section()
   

if __name__ == "__main__":
    main()