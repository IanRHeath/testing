# main_script.py (with completed Step 2 data gathering)

import os
import snowflake.connector
from dotenv import load_dotenv
import json
import re
import requests
import time
import shutil
import asyncio
from azure.identity import InteractiveBrowserCredential
import apex.results as arp
import apex.clients as ac

# --- Configuration and Setup (no changes) ---
def setup_environment():
    # ...
    print("[INFO] Setting up environment...")
    load_dotenv()
    if not os.getenv("SNOWFLAKE_USER") or not os.getenv("AIDA_USER") or not os.getenv("AIDA_PASSWORD"):
        raise EnvironmentError("CRITICAL: Ensure SNOWFLAKE_USER, AIDA_USER, and AIDA_PASSWORD are in .env file.")
    print("[SUCCESS] Environment configured.")


# --- Snowflake Logic (no changes) ---
def find_unprocessed_failures(execution_label: str) -> list:
    # ... (This function remains exactly the same)
    print(f"\n[INFO] Connecting to Snowflake to find failures for label: '{execution_label}'")
    snowflake_user = os.getenv("SNOWFLAKE_USER")
    conn = None
    try:
        conn = snowflake.connector.connect(
            user=snowflake_user,
            account='amd02.east-us-2.azure',
            warehouse='APEX_WH',
            database='APEX_TEST_RESULTS',
            schema='V2',
            authenticator='externalbrowser'
        )
        print("[SUCCESS] Connected to Snowflake.")
        # MODIFIED to include SCRUTINIZER_URL from VEXECUTION_RESULT
        sql_query = """
        SELECT TEST_RESULT_SEQ_ID, ADS_RESULT_LINK, QUEUE_ITEM_NAME, FAILURE_TYPE, FAILURE_DESCRIPTION, TARGET_PLATFORM AS BOARD, SCRUTINIZER_URL
        FROM VEXECUTION_RESULT
        WHERE EXECUTION_LABEL = %s AND RESULT != 'Pass' AND ADS_RESULT_LINK IS NOT NULL
        """
        cursor = conn.cursor()
        print(f"[INFO] Executing query...")
        cursor.execute(sql_query, (execution_label,))
        column_names = [desc[0] for desc in cursor.description]
        failures = [dict(zip(column_names, row)) for row in cursor.fetchall()]
        print(f"[SUCCESS] Found {len(failures)} failures to process.")
        return failures
    except Exception as e:
        print(f"[ERROR] An error occurred with Snowflake: {e}")
        return []
    finally:
        if conn:
            print("[INFO] Closing Snowflake connection.")
            conn.close()


# --- Data Enrichment Module (UPDATED) ---

def get_enrichment_data(failure_info: dict) -> dict:
    print(f"\n--- Starting Enrichment for SEQ ID: {failure_info['TEST_RESULT_SEQ_ID']} ---")
    
    enriched_context = {"original_failure": failure_info}
    seqid = failure_info['TEST_RESULT_SEQ_ID']
    
    # ... AIDA Analysis logic remains the same ...
    # ... Apex-Next File Analysis logic remains the same ...

    # *** NEW: Final Snowflake Details ***
    # This logic is from your get_ticket_info.py script
    print(f"\n[INFO] Starting final Snowflake detail lookup for SEQ ID: {seqid}...")
    snowflake_user = os.getenv("SNOWFLAKE_USER")
    conn = None
    try:
        conn = snowflake.connector.connect(
            user=snowflake_user,
            account='amd02.east-us-2.azure',
            warehouse='APEX_WH',
            database='APEX_TEST_RESULTS',
            schema='V2',
            authenticator='externalbrowser'
        )
        
        # Querying the VSYSTEM_CONFIG table for system details
        sql_query = "SELECT * FROM VSYSTEM_CONFIG WHERE TEST_RESULT_SEQ_ID = %s"
        cursor = conn.cursor()
        cursor.execute(sql_query, (str(seqid),)) # Note: seqid needs to be a string for parameter binding
        
        row = cursor.fetchone()
        if row:
            columns = [d[0] for d in cursor.description]
            system_config = dict(zip(columns, row))

            # Adding the specific details we need to our context dictionary
            enriched_context['system_details'] = {
                "PROGRAM": system_config.get("CPU_PROGRAM"),
                "PROGRAM_SHORT": system_config.get("CPU_PROGRAM_SHORT"),
                "OS": system_config.get("OS"),
                "SYSTEM_SOCKET": system_config.get("CPU_SOCKET"),
                "BIOS": system_config.get("BIOS"),
                "BIOS_DATE": str(system_config.get("BIOS_DATE")) # Convert date to string for JSON
            }
            print("[SUCCESS] Found system details in VSYSTEM_CONFIG.")
        else:
            print(f"[WARNING] No details found in VSYSTEM_CONFIG for SEQ ID: {seqid}")

    except Exception as e:
        print(f"[ERROR] Final Snowflake lookup failed: {e}")
        enriched_context['system_details'] = {"error": f"Failed to get details: {e}"}
    finally:
        if conn:
            conn.close()

    return enriched_context


# --- Main Execution Block (no changes) ---
if __name__ == "__main__":
    setup_environment()
    
    test_execution_label = "SYSVAL.INT.STXH.101BCDENDA-250417.FP11.0530.PPSV4694.EXP04_1001cRC2_Pre01_RevertPSP_RC62-NDA_CS7.05.16.143_TDR0_1500RB-S5_Test"

    failures_to_process = find_unprocessed_failures(test_execution_label)
    
    if failures_to_process:
        first_failure = failures_to_process[0]
        final_context = get_enrichment_data(first_failure)
        
        print("\n\n--- FINAL ENRICHED CONTEXT ---")
        print(json.dumps(final_context, indent=2))
        print("------------------------------")
    else:
        print("\nNo unprocessed failures were found for the given execution label.")
