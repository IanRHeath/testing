# main_script.py

import os
import snowflake.connector
from dotenv import load_dotenv
import json
import re
import requests
import time
import shutil
import asyncio

# --- Imports from your snippet ---
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

# --- Data Enrichment Module ---

def get_enrichment_data(failure_info: dict) -> dict:
    """
    Takes a single failure dictionary and enriches it with data from AIDA and apex-next.
    """
    print(f"\n--- Starting Enrichment for SEQ ID: {failure_info['TEST_RESULT_SEQ_ID']} ---")
    
    enriched_context = {"original_failure": failure_info}
    
    # --- AIDA Analysis (no changes) ---
    print(f"[INFO] Starting AIDA analysis...")
    # ... AIDA logic remains the same ...
    # (This section is collapsed for brevity but is unchanged from the previous version)


    # --- Apex-Next File Analysis (IMPLEMENTATION FROM YOUR SNIPPET) ---
    print(f"\n[INFO] Starting apex-next file download using your provided snippet's logic...")
    
    # I've adapted your snippet to work within our function.
    # Instead of a hardcoded seqid, it uses the one passed into this function.
    
    try:
        pipeline = arp.Pipeline.apex
        tenant_id = ac._AMD_TENANT_ID
        seqid = [failure_info['TEST_RESULT_SEQ_ID']] # Using the dynamic seqid from the failure
        target_dir = "./eras/" + str(seqid[0]) # Using the same directory structure

        # pipeline.devinfo # This was commented out in your snippet
        storageinfo = pipeline.prodinfo
        creds = InteractiveBrowserCredential(
                tenant_id=tenant_id,
                )
        
        print(f"[INFO] Calling arp.download_eras for SEQ ID: {seqid[0]}...")
        asyncio.run(arp.download_eras(
            seqids=seqid,
            download_dir=target_dir,
            creds=creds,
            storageinfo=storageinfo,
            ))
        print(f"[SUCCESS] Download call for apex-next files completed.")
        
        # We can add file parsing here if the download succeeds

    except Exception as e:
        print(f"[ERROR] Apex-next file processing failed: {e}")
        enriched_context['apex_next_status'] = f"Processing failed: {e}"
    finally:
        # Clean up the downloaded files if the directory was created
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
            print(f"[INFO] Cleaned up temporary directory: {target_dir}")

    return enriched_context


# --- Main Execution Block ---

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
