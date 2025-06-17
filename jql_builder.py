import json
import os
import re
from typing import Dict, Any
import openai
from jira import JIRA

from llm_config import get_azure_openai_client
from jira_utils import JiraBotError

# This part of the file is unchanged
RAW_AZURE_OPENAI_CLIENT = None
try:
    RAW_AZURE_OPENAI_CLIENT = get_azure_openai_client()
except Exception as e:
    print(f"CRITICAL ERROR: Could not initialize raw Azure OpenAI client at startup for JQL builder: {e}")

# All maps (program_map, system_map, etc.) are unchanged. They are omitted here for brevity.
program_map = {
    "STX": "Strix1 [PRG-000384]",
    "STXH": "Strix Halo [PRG-000391]",
    "GNR": "Granite Ridge [PRG-000279]",
    "KRK": "Krackan1 [PRG-000388]",
    "KRK2E": "Krackan2e [PRG-000376]",
    "SHP": "Shimada Peak HEDT [PRG-000326]",
    "FRG": "Fire Range [PRG-000394]",
}
system_map = {
    "STX": [
        "System-Strix1 FP8 APU",
        "System-Strix1 FP7 APU",
        "System-Strix1 FP11 APU"
    ],
    "STXH": [
        "System-Strix Halo Reference Board",
        "System-Strix Halo Customer A Platform"
    ]
}
VALID_SILICON_REVISIONS = {
    "A0", "A0A", "A0B", "A0C", "A0D", "A1", "A1B", "A1C", "A1D", "A1E",
    "A2", "B0", "B0A", "B0B", "B0C", "B0D", "B1", "B1B", "B1C", "B1E",
    "B1F", "B1G", "B2", "B2D", "B3", "B3E", "C0", "C1", "C1A", "C1B",
    "C1C", "C1D", "DP"
}
VALID_TRIAGE_CATEGORIES = {"APU", "APU/CPU-FW", "CPU", "GPU"}
triage_assignment_map = {
    "APU": [ "Client- Platform Debug - HW", "Diags-GPU" ],
    "APU/CPU-FW": [
        "Firmware - Binary DXIO", "Firmware - Binary EC", "Firmware - Binary IMC", "Firmware - Binary PSP",
        "Firmware - Binary SMU", "Firmware - Binary XHC", "Firmware - BIOS Verification", "Firmware - IPE AGESA - ABL",
        "Firmware - IPE AGESA - CPU", "Firmware - IPE AGESA - CPU UCODE INTEGRATION", "Firmware - IPE AGESA - DF",
        "Firmware - IPE AGESA - GNB", "Firmware - IPE AGESA - IDS", "Firmware - IPE AGESA - MEM",
        "Firmware - IPE AGESA - Other", "Firmware - IPE AGESA - PROMONTORY", "Firmware - IPE AGESA - PSP",
        "Firmware - IPE AGESA - UEFI", "Firmware - IPE CBS - CPU", "Firmware - IPE CBS - FCH",
        "Firmware - IPE CBS - GNB", "Firmware - IPE CBS - MEM", "Firmware - IPE CBS - Other", "Firmware - IPE CPM"
    ],
    "CPU": [
        "3D Graphics", "AAA", "ABL", "ACP", "ACPI", "AGESA", "Analog IO", "APML", "Application Automation", "Atomics",
        "Austin EMC,/RFI", "Automation Infrastructure", "AVL", "BIOS", "BMC", "Board", "Clarification/Validation",
        "Clock Characterization", "Coherency", "Core", "CXL", "DDRSSB", "Debug", "DF", "DFD", "DFx", "Diags",
        "Diags Framework", "Diags Release", "Diags-GPU", "Display", "Documentation", "DPM", "Driver", "DTM/WHQL",
        "DXIO", "E32PHY", "ESID", "FCH", "FCH Driver", "Firmware", "FPGA", "Fusing", "Gaming", "GFX Driver",
        "GMI", "GMTP PHY - PCIE", "GPU Compute", "GTMP PHY - XGMI", "HotPlug", "HSP", "Hybrid Graphics", "i2c",
        "i3c", "IO Compliance", "IO Datapath", "IO System Test", "IPU", "ISP", "Linux", "Linux Driver",
        "Manufacturing", "MCTP", "Memory (MC/PHY)", "Memory tuning", "MMHUB", "Modern Standby", "MP2", "MTAG",
        "Multi-GPU/Crossfire", "Multimedia", "N/A(disabled)", "NBIO", "Network", "Non-GFX Driver", "ODM Debug",
        "ODM Info", "ODM Reset", "Operating System", "OSS", "PCIe", "PEO/HST/SLT", "Performance", "PHY-FW",
        "PMFW", "PMM", "Power", "Power Express (PX)", "PPA", "PSP", "RAID", "RAS", "Remote Management", "Resets",
        "RF Mux", "SOi2", "SATA", "SBIOS", "Scan", "SDCI", "SDXI", "Security", "Signal Integrity", "Silicon",
        "SLT", "SMU", "Socket Issues", "SPI/eSPI", "SSBDCI", "Stability", "System Hang", "SystemInteg",
        "Test Scripts", "Thermal/Mechanical", "Tools - HW", "Tools - SW", "UMC", "USB 2.0/3.0 ", "USB 3.2",
        "USB4", "USR",  "UX", "VBIOS", "VCN", "Vendor", "Virtualization", "VPE", "WAFL", "WHQL", "XGMI"
    ],
    "GPU": [
        "Board Engineering", "Diags", "Diags-GPU", "Exercisers", "External IO", "IFWI", "INTERNAL IO", "MTAG",
        "Perf", "Platform", "SW/MLSE" , "Sys Int", "Sys Mgmt Ras/Security",
        "Sys Mgmt Ras/Security - Benson Tsang", "Sys Mgmt Virt/IOMMU/DFD/Scan/Fuse/Reset/", "Workloads"
    ]
}
VALID_SEVERITY_LEVELS = {"Critical", "High", "Medium", "Low"}
priority_map = {
    "P1": "P1 (Gating)",
    "P2": "P2 (Must Solve)",
    "P3": "P3 (Solution Desired)",
    "P4": "P4 (No Impact/Notify)"
}

# --- MODIFIED SECTION 1: project_map ---
project_map = {
    "PLAT": "PLAT", # Corrected this mapping from "PLATFORM" to "PLAT"
    "SWDEV": "SWDEV",
    "FWDEV": "FWDEV"
}

def extract_keywords_from_text(text_to_analyze: str) -> str:
    """Uses the LLM to extract key technical terms from a block of text."""
    # This function is unchanged
    if RAW_AZURE_OPENAI_CLIENT is None:
        raise JiraBotError("Raw Azure OpenAI client not initialized. Cannot extract keywords.")
    system_prompt = """
    You are an expert in analyzing Jira tickets to find core issues. From the following ticket text, extract the 3 most important and specific technical keywords that describe the core problem. Focus on nouns, verbs, and technical terms (like 'crash', 'UI button', 'memory leak', 'API', 'authentication'). 
    Combine the keywords into a single, space-separated string.
    """
    messages_to_send = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": text_to_analyze}
    ]
    try:
        resp = RAW_AZURE_OPENAI_CLIENT.chat.completions.create(model=os.getenv("LLM_CHAT_DEPLOYMENT_NAME"), messages=messages_to_send, max_tokens=50)
        keywords = resp.choices[0].message.content.strip()
        return keywords
    except Exception as e:
        raise JiraBotError(f"Error during keyword extraction from text: {e}")

def extract_params(prompt_text: str) -> Dict[str, Any]:
    if RAW_AZURE_OPENAI_CLIENT is None:
        raise JiraBotError("Raw Azure OpenAI client not initialized. Cannot extract parameters.")

    # --- MODIFIED SECTION 2: System Prompt ---
    system_prompt = """
    You are an expert in extracting JIRA query parameters from natural language prompts.
    Your goal is to create a JSON object based on the user's request.

    Extractable fields are: intent, priority, program, project, maxResults, order, keywords, created_after, created_before, updated_after, updated_before, assignee, reporter.
    The "maxResults" field is MANDATORY.

    Available programs: {programs_list}
    Available priorities: {priorities_list}
    Available projects: {projects_list}

    **Extraction Rules:**
    - If a project is mentioned, extract it. Otherwise, OMIT the project field.
    - ALWAYS include "maxResults", defaulting to 20. For "a ticket", use 1.
    - USER-BASED QUERIES:
      - For "assigned to me" or "reported by me", use "currentUser()".
      - For specific names like "assigned to Ian Heath", you MUST reformat it to "Last, First" format. Example: "Heath, Ian".
    - TIME-BASED QUERIES: Convert phrases like "yesterday" to JQL format ("-1d").
    
    Example 1 (Assigned to me): "show me tickets assigned to me"
    {{
      "intent": "list",
      "assignee": "currentUser()",
      "maxResults": 20
    }}

    Example 2 (Reported by specific user): "find bugs reported by 'Ian Heath'"
    {{
      "intent": "list",
      "keywords": "bug",
      "reporter": "Heath, Ian",
      "maxResults": 20
    }}
    """
    # --- END MODIFIED SECTION 2 ---
    
    formatted_system_prompt = system_prompt.format(
        programs_list=", ".join(program_map.keys()),
        priorities_list=", ".join(priority_map.keys()),
        projects_list=", ".join(project_map.keys())
    )

    messages_to_send = [
        {"role": "system", "content": formatted_system_prompt},
        {"role": "user", "content": prompt_text}
    ]

    print("\n--- LLM Request Details (for extract_params) ---")
    print(f"Model: {os.getenv('LLM_CHAT_DEPLOYMENT_NAME')}")
    print("Messages:")
    for msg in messages_to_send:
        print(f"  Role: {msg['role']}, Content: {msg['content']}")
    print("----------------------------------------------\n")

    try:
        resp = RAW_AZURE_OPENAI_CLIENT.chat.completions.create(model=os.getenv("LLM_CHAT_DEPLOYMENT_NAME"), messages=messages_to_send, max_tokens=256)
        content = resp.choices[0].message.content.strip()
        print(f"LLM extracted parameters: {content}")
        if content.startswith("```json"):
            content = content[7:-3].strip()
        params = json.loads(content)
        return params
    except json.JSONDecodeError as e:
        raise JiraBotError(f"LLM output was not valid JSON: {content}. Error: {e}")
    except openai.APIStatusError as e:
        raise JiraBotError(f"LLM API Error during parameter extraction: Status Code: {e.status_code}, Response: {e.response.text}")
    except Exception as e:
        raise JiraBotError(f"Error during parameter extraction: {e}")


def is_valid_jql_date_format(date_str: str) -> bool:
    """Checks if a string matches Jira's absolute (YYYY-MM-DD) or relative (-1w, -2d, -3M) date formats."""
    # This function is unchanged
    if not isinstance(date_str, str):
        return False
    absolute_format = r'^\d{4}-\d{2}-\d{2}$'
    relative_format = r'^-([1-9]\d*)[dwM]$'
    if re.match(absolute_format, date_str) or re.match(relative_format, date_str):
        return True
    return False

# --- NEW HELPER FUNCTION ---
def _format_name_for_jql(name: str) -> str:
    """
    Ensures a name is in 'Last, First' format for JQL.
    If the name is 'currentUser()', it's returned as is.
    If it appears to be 'First Last', it's reversed.
    Otherwise, it's assumed to be correct.
    """
    if name == "currentUser()" or "," in name:
        return name # Already correct or a special value
    
    parts = name.split()
    if len(parts) == 2:
        # Simple reversal for "First Last" format
        return f"{parts[1]}, {parts[0]}"
    
    # If format is unusual (single name, multiple middle names), return as is
    return name

# --- MODIFIED SECTION 3: build_jql ---
def build_jql(params: Dict[str, Any], exclude_key: str = None) -> str:
    """Constructs a JQL query string based on extracted parameters."""
    jql_parts = []
    order_clause = ""

    # Project (Now uses the corrected map)
    if raw_proj := params.get("project", "").strip().upper():
        if raw_proj in project_map:
            jql_parts.append(f"project = '{project_map[raw_proj]}'")
        else:
            raise JiraBotError(f"Invalid project '{raw_proj}'. Must be one of {list(project_map.keys())}.")
    
    if exclude_key:
        jql_parts.append(f"issueKey != '{exclude_key}'")

    if raw_prio := params.get("priority", "").strip():
        if raw_prio.upper() in priority_map:
            jql_parts.append(f"priority = \"{priority_map[raw_prio.upper()]}\"")
        elif raw_prio in priority_map.values():
            jql_parts.append(f"priority = \"{raw_prio}\"")
        else:
            raise JiraBotError(f"Invalid priority '{raw_prio}'. Must be one of {list(priority_map.keys())}.")

    if raw_prog := params.get("program", "").strip().upper():
        if raw_prog in program_map:
            jql_parts.append(f"program = '{program_map[raw_prog]}'")
        elif raw_prog in program_map.values():
            jql_parts.append(f"program = '{raw_prog}'")
        else:
            raise JiraBotError(f"Invalid program '{raw_prog}'. Must be one of {list(program_map.keys())}.")

    if params.get("intent") == "stale":
        jql_parts.append("status in (\"Open\", \"To Do\", \"In Progress\", \"Reopened\", \"Blocked\") AND updated < \"-30d\"")
        
    # User logic now uses the formatter
    if assignee := params.get("assignee"):
        formatted_name = _format_name_for_jql(assignee)
        if formatted_name == "currentUser()":
            jql_parts.append(f"assignee = {formatted_name}")
        else:
            jql_parts.append(f"assignee = \"{formatted_name}\"")

    if reporter := params.get("reporter"):
        formatted_name = _format_name_for_jql(reporter)
        if formatted_name == "currentUser()":
            jql_parts.append(f"reporter = {formatted_name}")
        else:
            jql_parts.append(f"reporter = \"{formatted_name}\"")

    if keywords := params.get("keywords"):
        keyword_parts = []
        for kw_raw in keywords.replace(',', ' ').split():
            kw = kw_raw.strip()
            if kw:
                keyword_parts.append(f"summary ~ \"{kw}\" OR description ~ \"{kw}\"")
        if keyword_parts:
            jql_parts.append(f"({' OR '.join(keyword_parts)})")

    date_fields = { "created_after": "created >=", "created_before": "created <=", "updated_after": "updated >=", "updated_before": "updated <=" }
    for field, operator in date_fields.items():
        if date_value := params.get(field):
            if is_valid_jql_date_format(date_value):
                jql_parts.append(f"{operator} '{date_value}'")
            else:
                raise JiraBotError(f"The date format '{date_value}' for '{field}' is not valid. Please use a format like YYYY-MM-DD or a relative date like -7d or -2w.")
    
    order_direction = params.get("order", "").strip().upper()
    if order_direction in ["ASC", "DESC"]:
        order_clause = f" ORDER BY created {order_direction}"
    elif params.get("maxResults") and not order_clause:
        order_clause = " ORDER BY created DESC"

    if not jql_parts:
        raise JiraBotError("Your query is too broad. Please specify at least one search criteria (e.g., keywords, a program, or a project).")
    
    jql = " AND ".join(jql_parts)

    if order_clause:
        jql += order_clause

    print(f"Built JQL: {jql}")
    return jql
# --- END MODIFIED SECTION 3 ---
