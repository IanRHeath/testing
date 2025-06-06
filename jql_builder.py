# jql_builder.py
import json
from typing import Dict, Any
import openai
from jira import JIRA # Just for type hinting

# Assuming local imports
from llm_config import get_azure_openai_client
from jira_utils import JiraBotError # For error handling in JQL building

# Global client for parameter extraction (initialized once)
RAW_AZURE_OPENAI_CLIENT = None
try:
    RAW_AZURE_OPENAI_CLIENT = get_azure_openai_client()
except Exception as e:
    print(f"CRITICAL ERROR: Could not initialize raw Azure OpenAI client at startup for JQL builder: {e}")
    # This will prevent the JQL builder from working, handled gracefully below.


# --- Your provided mappings ---
program_map = {
    "STX": "Strix1 [PRG-000384]",
    "STXH": "Strix Halo [PRG-000391]",
    "GNR": "Granite Ridge [PRG-000279]",
    "KRK": "Krackan1 [PRG-000388]",
    "KRK2E": "Krackan2e [PRG-000376]",
    "SHP": "Shimada Peak HEDT [PRG-000326]",
    "FRG": "Fire Range [PRG-000394]",
}

priority_map = {
    "P1": "P1 (Gating)",
    "P2": "P2 (Must Solve)",
    "P3": "P3 (Solution Desired)",
    "P4": "P4 (No Impact/Notify)"
}

project_map = {
    "PLAT": "PLATFORM" # Assuming PLAT maps to the full "PLATFORM" project key
}

def extract_params(prompt_text: str) -> Dict[str, Any]:
    """
    Uses LLM to extract JQL parameters from a natural language prompt.
    """
    if RAW_AZURE_OPENAI_CLIENT is None:
        raise JiraBotError("Raw Azure OpenAI client not initialized. Cannot extract parameters.")

    system_prompt = """
    You are an expert in extracting JIRA query parameters from natural language prompts.
    Extract the intent (e.g., "list", "count", "find"), priority, program, project,
    maximum number of results (maxResults), and order (ASC/DESC) as a JSON object only.
    Infer keywords for summary/description search for 'duplicate' or 'similar' intent.

    Available programs: {programs_list}
    Available priorities: {priorities_list}
    Available projects: {projects_list}

    Example of expected JSON output:
    {{
        "intent":"list",
        "priority":"P2",
        "program":"STXH",
        "project":"PLAT",
        "maxResults":5,
        "order":"ASC",
        "keywords": "login failure, timeout"
    }}

    If a parameter is not explicitly mentioned, omit it from the JSON.
    For 'stale' tickets, infer 'status in (\"Open\", \"To Do\", \"In Progress\", \"Reopened\", \"Blocked\") AND updated < \"-30d\"'
    For 'duplicate' tickets, extract relevant keywords from the user's prompt (e.g., "login errors" -> "login error").
    """
    
    # Dynamically inject available mappings into the system prompt
    formatted_system_prompt = system_prompt.format(
        programs_list=", ".join(program_map.keys()),
        priorities_list=", ".join(priority_map.keys()),
        projects_list=", ".join(project_map.keys())
    )

    try:
        resp = RAW_AZURE_OPENAI_CLIENT.chat.completions.create(
            model=os.getenv("LLM_CHAT_DEPLOYMENT_NAME"), # Use the deployment name for the model
            messages=[
                {"role": "system", "content": formatted_system_prompt},
                {"role": "user", "content": prompt_text}
            ],
            max_tokens=256, # Increased token limit for potentially more complex JSON
            temperature=0.0 # Keep low for structured output
        )
        content = resp.choices[0].message.content.strip()
        print(f"LLM extracted parameters: {content}")
        # Robustly try to parse JSON
        params = json.loads(content)
        return params
    except json.JSONDecodeError as e:
        raise JiraBotError(f"LLM output was not valid JSON: {content}. Error: {e}")
    except Exception as e:
        raise JiraBotError(f"Error during parameter extraction: {e}")

def build_jql(params: Dict[str, Any]) -> str:
    """
    Constructs a JQL query string based on extracted parameters.
    """
    jql_parts = []

    # Handle project
    raw_proj = params.get("project", "").strip().upper()
    if raw_proj:
        if raw_proj in project_map:
            jql_parts.append(f"project = '{project_map[raw_proj]}'")
        else:
            raise JiraBotError(f"Invalid project '{raw_proj}'. Must be one of {list(project_map.keys())}.")
    else:
        # Default to "PLATFORM" if no project is specified, as per your instruction
        jql_parts.append("project = 'PLATFORM'")


    # Handle priority
    raw_prio = params.get("priority", "").strip()
    if raw_prio:
        if raw_prio.upper() in priority_map:
            jql_parts.append(f"priority = \"{priority_map[raw_prio.upper()]}\"")
        elif raw_prio in priority_map.values(): # Already in full format
            jql_parts.append(f"priority = \"{raw_prio}\"")
        else:
            raise JiraBotError(f"Invalid priority '{raw_prio}'. Must be one of {list(priority_map.keys())}.")

    # Handle program (assuming 'program' is a custom field in JIRA)
    # If 'program' is not a direct JIRA field or a custom field, this part needs adjustment.
    raw_prog = params.get("program", "").strip().upper()
    if raw_prog:
        if raw_prog in program_map:
            # Assuming program is a custom field in JIRA, and the JQL needs the full name.
            # You might need to change 'program' to 'cf[xxxx]' if it's a custom field ID.
            # For now, we'll assume 'program' is a JQL-queryable field name.
            jql_parts.append(f"program = '{program_map[raw_prog]}'")
        elif raw_prog in program_map.values():
            jql_parts.append(f"program = '{raw_prog}'")
        else:
            raise JiraBotError(f"Invalid program '{raw_prog}'. Must be one of {list(program_map.keys())}.")

    # Handle stale tickets (based on your definition)
    if params.get("intent") == "stale":
        jql_parts.append("status in (\"Open\", \"To Do\", \"In Progress\", \"Reopened\", \"Blocked\") AND updated < \"-30d\"")

    # Handle keywords for "duplicate" or general search
    keywords = params.get("keywords")
    if keywords:
        # Assuming keywords can apply to summary or description
        keyword_parts = []
        for kw in keywords.split(','):
            kw = kw.strip()
            if kw:
                keyword_parts.append(f"summary ~ \"{kw}\" OR description ~ \"{kw}\"")
        if keyword_parts:
            jql_parts.append(f"({' OR '.join(keyword_parts)})")

    # Handle order
    if params.get("order"):
        order_clause = f" ORDER BY created {params['order']}" # Assuming 'created' is the default field for ordering

    if not jql_parts:
        # Fallback to a broad query if no specific parameters were extracted
        return "project = 'PLATFORM'" # Or some other default

    jql = " AND ".join(jql_parts)

    if params.get("order"):
        jql += order_clause # Append order clause at the very end

    print(f"Built JQL: {jql}")
    return jql
