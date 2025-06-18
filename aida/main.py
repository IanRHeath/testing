# main_script.py

import os
import snowflake.connector
from dotenv import load_dotenv
import json
import re # For parsing the jobId
import requests # For AIDA API calls
import time # For polling AIDA
import shutil # For cleaning up temporary files
import asyncio # For apex-next
from azure.identity import InteractiveBrowserCredential # For apex-next
import apex.results as arp # For apex-next

# --- Configuration and Setup ---

def setup_environment():
    """
    Loads credentials from a .env file into the environment.
    Now includes AIDA credentials.
    """
    print("[INFO] Setting up environment...")
    load_dotenv()
    # Add your AIDA username and password to your .env file
    if not os.getenv("SNOWFLAKE_USER") or not os.getenv("AIDA_USER") or not os.getenv("AIDA_PASSWORD"):
        raise EnvironmentError("CRITICAL: Ensure SNOWFLAKE_USER, AIDA_USER, and AIDA_PASSWORD are in .env file.")
    print("[SUCCESS] Environment configured.")

# --- Snowflake Logic (from Step 1, no changes) ---

def find_unprocessed_failures(execution_label: str) -> list:
    """
    Connects to Snowflake and finds all unprocessed failures for a given execution_label.
    """
    # This function remains exactly the same as in Step 1.
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
        sql_query = """
        SELECT TEST_RESULT_SEQ_ID, ADS_RESULT_LINK, QUEUE_ITEM_NAME, FAILURE_TYPE, FAILURE_DESCRIPTION, TARGET_PLATFORM AS BOARD
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

# --- NEW: Data Enrichment Module (Step 2) ---

def get_enrichment_data(failure_info: dict) -> dict:
    """
    Takes a single failure dictionary and enriches it with data from AIDA and apex-next.
    """
    print(f"\n--- Starting Enrichment for SEQ ID: {failure_info['TEST_RESULT_SEQ_ID']} ---")
    
    # Create a dictionary to hold all our new, rich context
    enriched_context = {"original_failure": failure_info}
    
    # 1. --- AIDA Analysis ---
    # This logic is adapted directly from your thread_with_aida.py script.
    print(f"[INFO] Starting AIDA analysis...")
    try:
        # Parse the Job ID from the ADS link
        pattern = r'/([0-9a-fA-F-]{36})/reports' #
        match = re.search(pattern, str(failure_info['ADS_RESULT_LINK']))
        if not match:
            raise ValueError("Could not parse Job ID from ADS_RESULT_LINK.")
        
        job_id = match.group(1)
        print(f"[INFO] Parsed AIDA Job ID: {job_id}")

        # Start a requests session and log in to AIDA
        session = requests.Session()
        certificate_path = "./certificates/tls-ca-bundle.crt" #
        
        login_data = { "username": os.getenv("AIDA_USER"), "password": os.getenv("AIDA_PASSWORD") } #
        login_response = session.post("https://aida.amd.com/api/auth/login", json=login_data, verify=certificate_path)
        login_response.raise_for_status() # Will raise an exception for non-200 status codes
        print("[SUCCESS] Logged in to AIDA.")

        # Start the debug run
        start_debug_data = {
            "queueType": "ads",
            "debugData": { "jobId": str(job_id), "useOfflineMethod": "true", "configOption": "16" }
        } #
        aida_response = session.post("https://aida.amd.com/api/debug/queueDebug", json=start_debug_data, verify=certificate_path)
        aida_response.raise_for_status()
        adId = aida_response.json().get('adId')
        enriched_context['aida_id'] = adId
        print(f"[INFO] AIDA debug run started with ID: {adId}")

        # Poll for completion
        summary_url = f"https://aida.amd.com/api/debug/{adId}" #
        while True:
            summary_response = session.get(summary_url, verify=certificate_path)
            summary_response.raise_for_status()
            # Navigating the JSON structure as seen in your scripts
            prompts = summary_response.json().get('debugData', {}).get('prompts', [])
            if prompts and prompts[0].get('status', '').lower() == "completed":
                enriched_context['aida_summary'] = prompts[0].get('outputlog')
                print("[SUCCESS] AIDA analysis completed.")
                break
            print("[INFO] Waiting for AIDA completion...")
            time.sleep(10) # Wait 10 seconds before polling again

    except Exception as e:
        print(f"[ERROR] AIDA analysis failed: {e}")
        enriched_context['aida_summary'] = f"AIDA analysis failed: {e}"

    # 2. --- Apex-Next File Analysis ---
    # This logic is adapted from your get_ticket_info.py script.
    print(f"\n[INFO] Starting apex-next file download...")
    seqid = failure_info['TEST_RESULT_SEQ_ID']
    target_dir = f"./temp_eras/{seqid}" # Use a temporary directory
    
    try:
        # Download ERA files for the specific sequence ID
        asyncio.run(arp.download_eras(
            seqids=[seqid],
            download_dir=target_dir,
            creds=InteractiveBrowserCredential(tenant_id='72f988bf-86f1-41af-91ab-2d7cd011db47'), # AMD Tenant ID
            storageinfo=arp.Pipeline.apex.prodinfo,
        )) #
        print(f"[SUCCESS] Downloaded apex-next files to {target_dir}")
        
        # Parse the testflow.log to find the die revision
        testflow_path = os.path.join(target_dir, "platform-test-results", "flat-storage", str(seqid), "testflow.log")
        if os.path.exists(testflow_path):
            with open(testflow_path, 'r') as file:
                for line in file:
                    if 'revision :' in line:
                        parts = line.split('revision :', 1)
                        enriched_context['die_revision'] = parts[1].split(',', 1)[0].strip() #
                        print(f"[SUCCESS] Found Die Revision: {enriched_context['die_revision']}")
                        break
        
        # We can add more file parsing here later if needed

    except Exception as e:
        print(f"[ERROR] Apex-next file processing failed: {e}")
        enriched_context['die_revision'] = f"File processing failed: {e}"
    finally:
        # Clean up the downloaded files
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
            print(f"[INFO] Cleaned up temporary directory: {target_dir}")

    # For now, we return the context we've gathered.
    # We will add the final Snowflake lookups in this function later if needed.
    return enriched_context


# --- Main Execution Block ---

if __name__ == "__main__":
    setup_environment()
    
    test_execution_label = "SYSVAL.INT.STXH.101BCDENDA-250417.FP11.0530.PPSV4694.EXP04_1001cRC2_Pre01_RevertPSP_RC62-NDA_CS7.05.16.143_TDR0_1500RB-S5_Test"

    failures_to_process = find_unprocessed_failures(test_execution_label)
    
    # In this step, we will only process the FIRST failure for simplicity.
    # In the final script, we will loop through all of them.
    if failures_to_process:
        first_failure = failures_to_process[0]
        
        # This is our new Step 2 function call
        final_context = get_enrichment_data(first_failure)
        
        print("\n\n--- FINAL ENRICHED CONTEXT ---")
        print(json.dumps(final_context, indent=2))
        print("------------------------------")
    else:
        print("\nNo unprocessed failures were found for the given execution label.")
