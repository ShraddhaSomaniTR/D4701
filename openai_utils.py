import os
import json
import re
import datetime
import jwt
from TokenGeneration import get_token_from_url  # Import the token generation function
from typing import Dict
from dotenv import load_dotenv
from websockets.sync.client import connect

load_dotenv()

# --- Load Configuration from config.json ---
with open("config.json", "r") as config_file:
    config = json.load(config_file)

# --- Token validation helper ---
def is_token_valid(token):
    try:
        # Decode JWT without verification to get exp
        payload = jwt.decode(token, options={"verify_signature": False, "verify_aud": False})
        exp = payload.get("exp")
        if exp is None:
            return False
        # Use timezone-aware datetime for UTC
        exp_dt = datetime.datetime.fromtimestamp(exp, datetime.timezone.utc)
        now_dt = datetime.datetime.now(datetime.timezone.utc)
        # Check if token is expired (with 30s buffer)
        return exp_dt > now_dt + datetime.timedelta(seconds=30)
    except Exception:
        return False

# --- Get or refresh token if expired ---
def get_or_refresh_token():
    token = config.get("TOKEN")
    if token and is_token_valid(token):
        return token
    portal_url = config["PORTAL_URL"]
    token = get_token_from_url(portal_url)
    # Save new token to config.json
    config["TOKEN"] = token
    with open("config.json", "w") as f:
        json.dump(config, f, indent=2)
    return token

# Constants
WORKFLOW_ID = config["WORKFLOW_ID"]  # Workflow ID for Open AI GPT4
TOKEN = get_or_refresh_token()
WEBSOCKET_URL = config["WEBSOCKET_URL"].replace("{TOKEN}", TOKEN)

def query_workflow(query: str, workflow_id: str = WORKFLOW_ID, is_persistence_allowed: str = "false"):
    """
    Send a query to the workflow through websocket connection.
    
    Args:
        query (str): The query to send
        workflow_id (str): The workflow ID
        is_persistence_allowed (str): Whether persistence is allowed
        
    Returns:
        tuple: (answer, cost_tracker)
    """
    msg = {
        "action": "SendMessage",
        "workflow_id": workflow_id,
        "query": query,
        "is_persistence_allowed": is_persistence_allowed
    }
    
    ws = connect(WEBSOCKET_URL)
    ws.send(json.dumps(msg))
    answer = str()
    cost_tracker = dict()
    eof = False
    
    while not eof:
        message = ws.recv()
        message = json.loads(message)
        for model, value in message.items():
            if "answer" in value:
                answer += value["answer"]
            elif "cost_track" in value:
                cost_tracker = value['cost_track']
                eof = True
    
    ws.close()
    return answer, cost_tracker


def generate_sql_query(prompt: str, schema_info: str) -> str:
    """
    Generate SQL query from natural language prompt using websocket API.
    
    Args:
        prompt (str): Natural language query
        schema_info (str): Database schema information
        
    Returns:
        str: Generated SQL query
    """
    try:
        # Construct the system prompt with schema information
        system_prompt = f"""You are a SQL expert. Given the following database schema:
        {schema_info}
        
        Convert the following natural language query to SQL.
        Return ONLY the SQL query without any explanations."""

        # Format the complete prompt
        full_prompt = f"{system_prompt}\n\nQuery: {prompt}"
        
        # Get response through websocket
        answer, _ = query_workflow(full_prompt)
        return answer.strip()
    except Exception as e:
        return f"Error generating SQL query: {str(e)}"

# Add these functions to your existing openai_utils.py file

def optimize_stored_procedure(procedure_definition: str, procedure_name: str) -> tuple:
    """
    Optimize stored procedure using AI.
    
    Args:
        procedure_definition (str): Current stored procedure definition
        procedure_name (str): Name of the procedure
        performance_data (Dict): Performance metrics
        schema_info (str): Database schema information
        
    Returns:
        tuple: (optimized_procedure, optimization_suggestions, system_prompt)
    """
    try:
        # Construct the system prompt for optimization
        system_prompt = f"""You are a SQL Server stored procedure optimization expert. 
        
       
        
      
        
        Analyze the following stored procedure and provide:
        1. An optimized version of the stored procedure
        2. Detailed optimization suggestions explaining what was changed and why
        3. Performance improvement recommendations
        
        Focus on:
        - Query optimization (indexes, joins, WHERE clauses)
        - Parameter usage and SQL injection prevention
        - Error handling improvements
        - Code readability and maintainability
        - Performance bottlenecks
        
        Stored Procedure Name: {procedure_name}
        
        Current Definition:
        {procedure_definition}
        
        Please provide the response in the following format:
        
        ## Optimized Stored Procedure:
        ```sql
        [optimized procedure code here]
        ```
        
        ## Optimization Suggestions:
        [detailed suggestions here]
        """
        
        # Get response through websocket
        answer, _ = query_workflow(system_prompt)
        
        # Parse the response to extract optimized procedure and suggestions
        parts = answer.split("## Optimization Suggestions:")
        optimized_part = parts[0].replace("## Optimized Stored Procedure:", "").strip()
        suggestions_part = parts[1].strip() if len(parts) > 1 else "No specific suggestions provided."
        
        # Clean the optimized procedure (remove markdown formatting)
        optimized_procedure = clean_sql_code(optimized_part)
        
        return optimized_procedure, suggestions_part, system_prompt
        
    except Exception as e:
        return f"Error optimizing stored procedure: {str(e)}", "", system_prompt

def analyze_stored_procedure_issues(procedure_definition: str, procedure_name: str) -> tuple:
    """
    Analyze stored procedure for potential issues and best practices.
    
    Args:
        procedure_definition (str): Stored procedure definition
        procedure_name (str): Name of the procedure
        
    Returns:
        tuple: (analysis_report, system_prompt)
    """
    try:
        system_prompt = f"""You are a SQL Server code review expert. 
        
        Analyze the following stored procedure for:
        1. Security vulnerabilities (SQL injection, permissions)
        2. Performance issues (missing indexes, inefficient queries)
        3. Best practices violations
        4. Code quality issues
        5. Error handling problems
        6. Maintainability concerns
        
        Provide a detailed analysis report with:
        - Issue severity (High/Medium/Low)
        - Specific recommendations
        - Code examples where applicable
        
        Stored Procedure Name: {procedure_name}
        
        Definition:
        {procedure_definition}
        """
        
        # Get response through websocket
        answer, _ = query_workflow(system_prompt)
        
        return answer, system_prompt
        
    except Exception as e:
        return f"Error analyzing stored procedure: {str(e)}", system_prompt

def clean_sql_code(sql_code: str) -> str:
    """
    Clean SQL code by removing markdown formatting.
    
    Args:
        sql_code (str): SQL code with potential markdown
        
    Returns:
        str: Cleaned SQL code
    """
    # Remove markdown code fences
    cleaned = re.sub(r'```sql\s*', '', sql_code)
    cleaned = re.sub(r'```\s*', '', cleaned)
    
    # Remove any remaining backticks
    cleaned = cleaned.replace('`', '')
    
    # Strip whitespace
    cleaned = cleaned.strip()
    
    return cleaned