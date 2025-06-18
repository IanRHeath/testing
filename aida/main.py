# main_script.py

import os
import snowflake.connector
from dotenv import load_dotenv
import json

# --- Configuration and Setup ---

def setup_environment():
    """
    Loads credentials from a .env file into the environment.
    This is a best practice for security, keeping secrets out of the code.
    """
    print("[INFO] Setting up environment...")
    load_dotenv()
    # We only need the Snowflake user for this step.
    # We add a check to ensure the script doesn't run without credentials.
    if not os.getenv("SNOWFLAKE_USER"):
        raise EnvironmentError("CRITICAL: SNOWFLAKE_USER not found in .env file.")
    print("[SUCCESS] Environment configured.")

# --- Core Snowflake Logic ---

def find_unprocessed_failures(execution_label: str) -> list:
    """
    Connects to Snowflake and finds all unprocessed failures for a given execution_label.

    This function is the entry point for our entire workflow.

    Args:
        execution_label: The specific execution label to query for failures.

    Returns:
        A list of dictionaries, where each dictionary represents a failure to be processed.
    """
    print(f"\n[INFO] Connecting to Snowflake to find failures for label: '{execution_label}'")
    
    # We get the user from the environment variables loaded earlier.
    snowflake_user = os.getenv("SNOWFLAKE_USER")
    
    # This connection block is taken directly from your provided scripts.
    # It uses the recommended 'try...finally' pattern to ensure the connection is always closed.
    conn = None # Initialize conn to None to prevent error if connection fails
    try:
        # The connection parameters are consolidated from your scripts.
        # It uses the SSO 'externalbrowser' authenticator you've been using.
        conn = snowflake.connector.connect(
            user=snowflake_user,
            account='amd02.east-us-2.azure', #
            warehouse='APEX_WH', #
            database='APEX_TEST_RESULTS', #
            schema='V2', #
            authenticator='externalbrowser' #
        )
        print("[SUCCESS] Connected to Snowflake.")
        
        # This is the SQL query at the heart of this step.
        # It's designed to find the exact items that need to be processed.
        sql_query = """
        SELECT
            TEST_RESULT_SEQ_ID,
            ADS_RESULT_LINK,
            QUEUE_ITEM_NAME,
            FAILURE_TYPE,
            FAILURE_DESCRIPTION,
            TARGET_PLATFORM AS BOARD -- Renaming for clarity based on test.txt
        FROM
            VEXECUTION_RESULT
        WHERE
            EXECUTION_LABEL = %s
            AND RESULT != 'Pass'
            AND ADS_RESULT_LINK IS NOT NULL
        """
        
        cursor = conn.cursor()
        print(f"[INFO] Executing query...")
        cursor.execute(sql_query, (execution_label,))
        
        # This technique fetches all rows and converts them into a more usable
        # list of dictionaries. This is cleaner than accessing by index.
        column_names = [desc[0] for desc in cursor.description]
        failures = [dict(zip(column_names, row)) for row in cursor.fetchall()]
        
        print(f"[SUCCESS] Found {len(failures)} failures to process.")
        return failures

    except Exception as e:
        print(f"[ERROR] An error occurred with Snowflake: {e}")
        return [] # Return an empty list on failure
    finally:
        # This ensures the connection is closed whether the query succeeds or fails.
        if conn:
            print("[INFO] Closing Snowflake connection.")
            conn.close()

# --- Main Execution Block ---

if __name__ == "__main__":
    # This block runs when you execute the script directly.
    # It's our primary way to test the functionality of this step.
    
    # 1. Set up the environment
    setup_environment()
    
    # 2. Define our test input
    # We use a known execution label for development, which you can get from snowflake-tool.py
    test_execution_label = "SYSVAL.INT.STXH.101BCDENDA-250417.FP11.0530.PPSV4694.EXP04_1001cRC2_Pre01_RevertPSP_RC62-NDA_CS7.05.16.143_TDR0_1500RB-S5_Test" #

    # 3. Call our main function
    failures_to_process = find_unprocessed_failures(test_execution_label)
    
    # 4. Print the results in a clean, readable format
    if failures_to_process:
        print("\n--- RESULTS ---")
        # Using json.dumps with indentation makes the output easy to read.
        # This is the data that will be passed to the next steps of our process.
        print(json.dumps(failures_to_process, indent=2))
        print("---------------")
    else:
        print("\nNo unprocessed failures were found for the given execution label.")
