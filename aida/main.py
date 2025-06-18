# main_script.py (Complete data gathering and enrichment engine)

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

# --- Configuration and Setup ---
def setup_environment():
    """
    Loads credentials from a .env file into the environment.
    """
    print("[INFO] Setting up environment...")
    load_dotenv()
    if not os.getenv("SNOWFLAKE_USER") or not os.getenv("AIDA_USER") or not os.getenv("AIDA_PASSWORD"):
        raise EnvironmentError("CRITICAL: Ensure SNOWFLAKE_USER, AIDA_USER, and AIDA_PASSWORD are in .env file.")
    print("[SUCCESS] Environment configured.")


# --- Snowflake Logic ---
def find_unprocessed_failures(execution_label: str) -> list:
    """
    Connects to Snowflake and finds all unprocessed failures for a given execution_label.
    """
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
        
        # This query now includes SCRUTINIZER_URL as requested.
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


# --- Data Enrichment Module ---
def get_enrichment_data(failure_info: dict) -> dict:
    """
    Takes a single failure dictionary and enriches it with data from ALL sources:
    AIDA, apex-next, and additional Snowflake tables.
    """
    print(f"\n--- Starting Enrichment for SEQ ID: {failure_info['TEST_RESULT_SEQ_ID']} ---")
    
    enriched_context = {"original_failure": failure_info}
    seqid = failure_info['TEST_RESULT_SEQ_ID']
    
    # === STAGE 1: AIDA Analysis ===
    # Logic from your thread_with_aida.py
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
        
        enriched_context['aida_id'] = adId
        print(f"[INFO] AIDA debug run started with ID: {adId}")

        summary_url = f"https://aida.amd.com/api/debug/{adId}"
        while True:
            summary_response = session.get(summary_url, verify=certificate_path)
            summary_response.raise_for_status()
            prompts = summary_response.json().get('debugData', {}).get('prompts', [])
            if prompts and prompts[0].get('status', '').lower() == "completed":
                enriched_context['aida_summary'] = prompts[0].get('outputlog')
                print("[SUCCESS] AIDA analysis completed.")
                break
            print("[INFO] Waiting for AIDA completion...")
            time.sleep(10)

    except Exception as e:
        print(f"[ERROR] AIDA analysis failed: {e}")
        enriched_context['aida_summary'] = f"AIDA analysis failed: {e}"

    # === STAGE 2: Apex-Next File Analysis ===
    # Logic from your get_ticket_info.py
    print(f"\n[INFO] Starting apex-next file download...")
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

    # === STAGE 3: Final Snowflake Details ===
    # Logic from your get_ticket_info.py
    print(f"\n[INFO] Starting final Snowflake detail lookup for SEQ ID: {seqid}...")
    snowflake_user = os.getenv("SNOWFLAKE_USER")
    conn = None
    try:
        conn = snowflake.connector.connect(
            user=snowflake_user, account='amd02.east-us-2.azure', warehouse='APEX_WH',
            database='APEX_TEST_RESULTS', schema='V2', authenticator='externalbrowser'
        )
        sql_query = "SELECT * FROM VSYSTEM_CONFIG WHERE TEST_RESULT_SEQ_ID = %s"
        cursor = conn.cursor()
        cursor.execute(sql_query, (str(seqid),))
        row = cursor.fetchone()
        if row:
            columns = [d[0] for d in cursor.description]
            system_config = dict(zip(columns, row))
            enriched_context['system_details'] = {
                "PROGRAM": system_config.get("CPU_PROGRAM"), "PROGRAM_SHORT": system_config.get("CPU_PROGRAM_SHORT"),
                "OS": system_config.get("OS"), "SYSTEM_SOCKET": system_config.get("CPU_SOCKET"),
                "BIOS": system_config.get("BIOS"), "BIOS_DATE": str(system_config.get("BIOS_DATE"))
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


# --- Main Execution Block ---
if __name__ == "__main__":
    setup_environment()
    
    test_execution_label = "SYSVAL.INT.STXH.101BCDENDA-250417.FP11.0530.PPSV4694.EXP04_1001cRC2_Pre01_RevertPSP_RC62-NDA_CS7.05.16.143_TDR0_1500RB-S5_Test"

    failures_to_process = find_unprocessed_failures(test_execution_label)
    
    # For now, we only process the FIRST failure for simplicity.
    if failures_to_process:
        first_failure = failures_to_process[0]
        final_context = get_enrichment_data(first_failure)
        
        print("\n\n--- FINAL ENRICHED CONTEXT ---")
        print(json.dumps(final_context, indent=2))
        print("------------------------------")
    else:
        print("\nNo unprocessed failures were found for the given execution label.")
