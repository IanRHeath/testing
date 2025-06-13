import json
import os
from typing import Dict, Any, Optional
import openai
from jira import JIRA

from llm_config import get_azure_openai_client
from jira_utils import JiraBotError

RAW_AZURE_OPENAI_CLIENT = None
try:
    RAW_AZURE_OPENAI_CLIENT = get_azure_openai_client()
except Exception as e:
    print(f"CRITICAL ERROR: Could not initialize raw Azure OpenAI client at startup for JQL builder: {e}")

# ... (program_map, system_map, and other maps remain the same) ...
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

project_map = {
    "PLAT": "PLAT",
    "SWDEV": "SWDEV",
    "FWDEV": "FWDEV"
}

def extract_keywords_from_text(text_to_analyze: str) -> str:
    """Uses the LLM to extract key technical terms from a block of text."""
    if RAW_AZURE_OPENAI_CLIENT is None:
        raise JiraBotError("Raw Azure OpenAI client not initialized. Cannot extract keywords.")
        
    system_prompt = """
    You are an expert in analyzing Jira tickets to find core issues. From the following ticket text, extract the 3 most important and specific technical keywords that describe the core problem. Focus on nouns, verbs, and technical terms (like 'crash', 'UI button', 'memory leak', 'API', 'authentication'). 
    
    Combine the keywords into a single, space-separated string.
    
    Example:
    Text: "The login button is broken on the main branch. When a user clicks it, the screen goes white and the application crashes with a memory allocation error in the new authentication module."
    Result: "login button crash"
    
    Output only the keywords and nothing else.
    """
    
    messages_to_send = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": text_to_analyze}
    ]

    try:
        resp = RAW_AZURE_OPENAI_CLIENT.chat.completions.create(
            model=os.getenv("LLM_CHAT_DEPLOYMENT_NAME"),
            messages=messages_to_send,
            max_tokens=50,
        )
        keywords = resp.choices[0].message.content.strip()
        return keywords
    except Exception as e:
        raise JiraBotError(f"Error during keyword extraction from text: {e}")


def extract_params(prompt_text: str) -> Dict[str, Any]:
    if RAW_AZURE_OPENAI_CLIENT is None:
        raise JiraBotError("Raw Azure OpenAI client not initialized. Cannot extract parameters.")

    system_prompt = """
    You are an expert in extracting JIRA query parameters from natural language prompts.
    Your goal is to create a JSON object based on the user's request.

    Extractable fields are: intent, priority, program, project, maxResults, order, keywords, createdDate, updatedDate, assignee, iod_silicon_rev, ccd_silicon_rev.

    Available programs: {programs_list}
    Available priorities: {priorities_list}
    Available projects: {projects_list}

    **Extraction Rules:**
    - If the user's query contains text to search for, extract the essential words into the "keywords" field.
    - For 'stale' tickets, infer the 'intent' as 'stale'. The system will handle the complex JQL for this.
    - For queries about unassigned tickets (e.g., "no owner", "unassigned"), set the 'assignee' field to the special value "EMPTY".
    - For date-related queries, populate 'createdDate' or 'updatedDate'. Convert natural language dates into JQL's relative date format.
        - "today" -> "startOfDay()"
        - "yesterday" -> "startOfDay(-1)"
        - "this week" -> "startOfWeek()"
        - "this month" -> "startOfMonth()"
        - "this year" -> "startOfYear()"
        - "last 7 days" -> "-7d"
    - If a parameter is not explicitly mentioned, you MUST omit it from the JSON.
    - ONLY include a "project" field if the user explicitly names a project in their request.

    Example 1 (Assignee Search): "show me unassigned tickets"
    {{
        "intent":"list",
        "assignee":"EMPTY"
    }}

    Example 2 (Complex Search): "show me p2 tickets for STXH assigned to John Doe"
    {{
        "intent":"list",
        "priority":"P2",
        "program":"STXH",
        "assignee":"John Doe"
    }}

    Example 3 (Stale Ticket Search): "find stale tickets"
    {{
        "intent":"stale"
    }}
    """

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
        resp = RAW_AZURE_OPENAI_CLIENT.chat.completions.create(
            model=os.getenv("LLM_CHAT_DEPLOYMENT_NAME"),
            messages=messages_to_send,
            max_tokens=256,
        )
        content = resp.choices[0].message.content.strip()
        print(f"LLM extracted parameters: {content}")
        params = json.loads(content)
        return params
    except json.JSONDecodeError as e:
        raise JiraBotError(f"LLM output was not valid JSON: {content}. Error: {e}")
    except openai.APIStatusError as e:
        raise JiraBotError(f"LLM API Error during parameter extraction: Status Code: {e.status_code}, Response: {e.response.text}")
    except Exception as e:
        raise JiraBotError(f"Error during parameter extraction: {e}")

def build_jql(params: Dict[str, Any], exclude_key: Optional[str] = None) -> str:
    """
    Constructs a JQL query string based on extracted parameters.
    Can optionally exclude a specific issue key from the results.
    """
    jql_parts = []
    order_clause = ""

    raw_proj = params.get("project", "").strip().upper()
    if raw_proj:
        if raw_proj in project_map:
            jql_parts.append(f"project = '{project_map[raw_proj]}'")
        else:
            raise JiraBotError(f"Invalid project '{raw_proj}'. Must be one of {list(project_map.keys())}.")

    raw_prio = params.get("priority", "").strip()
    if raw_prio:
        if raw_prio.upper() in priority_map:
            jql_parts.append(f"priority = \"{priority_map[raw_prio.upper()]}\"")
        elif raw_prio in priority_map.values():
            jql_parts.append(f"priority = \"{raw_prio}\"")
        else:
            raise JiraBotError(f"Invalid priority '{raw_prio}'. Must be one of {list(priority_map.keys())}.")

    raw_prog = params.get("program", "").strip().upper()
    if raw_prog:
        if raw_prog in program_map:
            jql_parts.append(f"program = '{program_map[raw_prog]}'")
        elif raw_prog in program_map.values():
            jql_parts.append(f"program = '{raw_prog}'")
        else:
            raise JiraBotError(f"Invalid program '{raw_prog}'. Must be one of {list(program_map.keys())}.")
    
    assignee = params.get("assignee")
    if assignee:
        if assignee.upper() == "EMPTY":
            jql_parts.append("assignee is EMPTY")
        else:
            # Use the name exactly as provided. This relies on the user
            # providing a correct Jira username or full display name.
            jql_parts.append(f'assignee = "{assignee}"')

    created_date = params.get("createdDate")
    if created_date:
        if "()" in created_date:
            jql_parts.append(f'created >= {created_date}')
        else:
            jql_parts.append(f'created >= "{created_date}"')

    updated_date = params.get("updatedDate")
    if updated_date:
        if "()" in updated_date:
            jql_parts.append(f'updated >= {updated_date}')
        else:
            jql_parts.append(f'updated >= "{updated_date}"')

    if params.get("intent") == "stale":
        stale_conditions = [
            'updated < "-30d"',
            '(assignee is EMPTY AND created < "-7d")',
            '(status in ("In Progress", "In Development", "Development") AND NOT status CHANGED AFTER -60d)',
            '(status in ("In Review", "In QA") AND NOT status CHANGED AFTER -7d)',
            '(status in ("Blocked", "Waiting for Customer") AND NOT status CHANGED AFTER -15d)'
        ]
        
        open_statuses = [
            "Open", "To Do", "In Progress", "Reopened", "Blocked", 
            "In Development", "Development", "In Review", "In QA", "Waiting for Customer"
        ]
        
        jql_parts.append(f"status in ({', '.join([f'\"{s}\"' for s in open_statuses])}) AND ({' OR '.join(stale_conditions)})")

    keywords = params.get("keywords")
    if keywords:
        keyword_list = []
        if isinstance(keywords, str):
            keyword_list = keywords.split(' ')
        elif isinstance(keywords, list):
            keyword_list = keywords

        keyword_parts = []
        for kw_raw in keyword_list:
            kw = str(kw_raw).strip().replace('"', '\\"')
            if kw:
                keyword_parts.append(f'text ~ "{kw}"')
        if keyword_parts:
            jql_parts.append(f"({' AND '.join(keyword_parts)})")

    # Add the exclusion clause if a key is provided
    if exclude_key:
        jql_parts.append(f'key != "{exclude_key}"')

    order_direction = params.get("order", "").strip().upper()
    if order_direction in ["ASC", "DESC"]:
        order_clause = f" ORDER BY created {order_direction}"
    
    elif params.get("maxResults") and not order_clause:
        order_clause = " ORDER BY created DESC"


    if not jql_parts:
        raise JiraBotError("Your query is too broad. Please specify a project, keywords, or other criteria to begin a search.")
    
    jql = " AND ".join(jql_parts)

    if order_clause:
        jql += order_clause

    print(f"Built JQL: {jql}")

    return jql
