import os
import json
from dotenv import load_dotenv
from websockets.sync.client import connect

load_dotenv()

# Constants
WORKFLOW_ID = "8556ba87-acf8-4049-98a3-fc62a300656c"  # Workflow ID for Open AI GPT4
ESSO_TOKEN = os.getenv("ESSO_TOKEN", "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IlJERTBPVEF3UVVVMk16Z3hPRUpGTkVSRk5qUkRNakkzUVVFek1qZEZOVEJCUkRVMlJrTTRSZyJ9.eyJodHRwczovL3RyLmNvbS9mZWRlcmF0ZWRfdXNlcl9pZCI6IjYxMjYxNzAiLCJodHRwczovL3RyLmNvbS9mZWRlcmF0ZWRfcHJvdmlkZXJfaWQiOiJUUlNTTyIsImh0dHBzOi8vdHIuY29tL2xpbmtlZF9kYXRhIjpbeyJzdWIiOiJvaWRjfHNzby1hdXRofFRSU1NPfDYxMjYxNzAifV0sImh0dHBzOi8vdHIuY29tL2V1aWQiOiJmNmI3NzIxYy0wMTdjLTRlN2MtYmI2ZC05NGJlMzMzZWU2M2QiLCJodHRwczovL3RyLmNvbS9hc3NldElEIjoiYTIwODE5OSIsImlzcyI6Imh0dHBzOi8vYXV0aC50aG9tc29ucmV1dGVycy5jb20vIiwic3ViIjoiYXV0aDB8NjVhOTNhZDY2ZjlmYTI4ZDIxNmFjYzI4IiwiYXVkIjpbIjQ5ZDcwYTU4LTk1MDktNDhhMi1hZTEyLTRmNmUwMGNlYjI3MCIsImh0dHBzOi8vbWFpbi5jaWFtLnRob21zb25yZXV0ZXJzLmNvbS91c2VyaW5mbyJdLCJpYXQiOjE3NTE5NTU3MzQsImV4cCI6MTc1MjA0MjEzNCwic2NvcGUiOiJvcGVuaWQgcHJvZmlsZSBlbWFpbCIsImF6cCI6InRnVVZad1hBcVpXV0J5dXM5UVNQaTF5TnlvTjJsZmxJIn0.XYXJnOY-PNhGFnGWqfqOT-Cx-BVXJ0funp3kxU3pLPBeF4kiIs9dCLCK-guDetvIKOrlrE7p29iyRYsyQDZA9dYRz7qNS-NZbIDH2ZQA0MBV-DEZIJow6UhrulsnCoZOzIGQ5zwn3rPBGeIXy0AeXXtm-GH-N76v2X-sRz9FaFNKujJlbzWtIaOJ20cPLU17uBzspUGJT_mCkrCuklj8igHnG8yhyQX2sOMxJweTnkGv5veD3ZObWuInwQqszpihiIXKN5MhyoXT_q8xmxkdSuVKoav8U8G569TjV39hYaQoSqTmpF-tEN2c4qUf1Vt2wrykpvbj9rnOIneBZMNFMA")
URL = f"wss://wymocw0zke.execute-api.us-east-1.amazonaws.com/prod/?Authorization={ESSO_TOKEN}"

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
    
    ws = connect(URL)
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

def init_openai():
    """Check if ESSO_TOKEN environment variable is set."""
    if not ESSO_TOKEN or ESSO_TOKEN == "<TOKEN_WITHOUT_BEARER_KEYWORD>":
        raise ValueError("ESSO_TOKEN environment variable not set")

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