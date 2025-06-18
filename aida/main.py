# main_script.py (with completed Step 2 logic)

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


# --- Data Enrichment Module (UPDATED) ---

def get_enrichment_data(failure_info: dict) -> dict:
    print(f"\n--- Starting Enrichment for SEQ ID: {failure_info['TEST_RESULT_SEQ_ID']} ---")
    
    enriched_context = {"original_failure": failure_info}
    
    # --- AIDA Analysis ---
    print(f"[INFO] Starting AIDA analysis...")
    try:
        pattern = r'/([0-9a-fA-F-]{36})/reports'
        match = re.search(pattern, str(failure_info['ADS_RESULT_LINK']))
        if not match: raise ValueError("Could not parse Job ID from ADS_RESULT_LINK.")
        job_id = match.group(1)

        session = requests.Session()
        certificate_path = "./certificates/tls-ca-bundle.crt"
        
        login_data = { "username": os.getenv("AIDA_USER"), "password": os.getenv("AIDA_PASSWORD") }
        login_response = session.post("https://aida.amd.com/api/auth/login", json=login_data, verify=certificate_path)
        login_response.raise_for_status()
        
        start_debug_data = {"queueType": "ads", "debugData": { "jobId": str(job_id), "useOfflineMethod": "true", "configOption": "16" }}
        aida_response = session.post("https://aida.amd.com/api/debug/queueDebug", json=start_debug_data, verify=certificate_path)
        aida_response.raise_for_status()
        adId = aida_response.json().get('adId')
        
        enriched_context['aida_id'] = adId # Storing the AIDA ID
        print(f"[INFO] AIDA debug run started with ID: {adId}")

        summary_url = f"https://aida.amd.com/api/debug/{adId}"
        while True:
            summary_response = session.get(summary_url, verify=certificate_path)
            summary_response.raise_for_status()
            prompts = summary_response.json().get('debugData', {}).get('prompts', [])
            if prompts and prompts[0].get('status', '').lower() == "completed":
                # *** NEW: Storing the AIDA summary in our context dictionary ***
                enriched_context['aida_summary'] = prompts[0].get('outputlog')
                print("[SUCCESS] AIDA analysis completed.")
                break
            print("[INFO] Waiting for AIDA completion...")
            time.sleep(10)

    except Exception as e:
        print(f"[ERROR] AIDA analysis failed: {e}")
        enriched_context['aida_summary'] = f"AIDA analysis failed: {e}"

    # --- Apex-Next File Analysis ---
    print(f"\n[INFO] Starting apex-next file download...")
    seqid = failure_info['TEST_RESULT_SEQ_ID']
    target_dir = f"./temp_eras/{seqid}"
    
    try:
        pipeline = arp.Pipeline.apex
        tenant_id = ac._AMD_TENANT_ID
        storageinfo = pipeline.prodinfo
        creds = InteractiveBrowserCredential(tenant_id=tenant_id)
        
        asyncio.run(arp.download_eras(
            seqids=[seqid], download_dir=target_dir, creds=creds, storageinfo=storageinfo
        ))
        print(f"[SUCCESS] Downloaded apex-next files to {target_dir}")
        
        # *** NEW: Parsing the file and storing the result in our context dictionary ***
        # This logic is from your get_ticket_info.py script
        testflow_path = os.path.join(target_dir, "platform-test-results", "flat-storage", str(seqid), "testflow.log")
        if os.path.exists(testflow_path):
            with open(testflow_path, 'r') as file:
                for line in file:
                    if 'revision :' in line:
                        enriched_context['die_revision'] = line.split('revision :', 1)[1].split(',', 1)[0].strip()
                        print(f"[SUCCESS] Found Die Revision: {enriched_context['die_revision']}")
                        break
        else:
            enriched_context['die_revision'] = "testflow.log not found"

    except Exception as e:
        print(f"[ERROR] Apex-next file processing failed: {e}")
        enriched_context['die_revision'] = f"File processing failed: {e}"
    finally:
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
            print(f"[INFO] Cleaned up temporary directory: {target_dir}")

    return enriched_context


# --- Main Execution Block (no changes) ---
if __name__ == "__main__":
    # ...
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
