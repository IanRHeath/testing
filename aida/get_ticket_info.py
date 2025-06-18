import requests
import os
import json
import getpass
import snowflake.connector
from azure.identity import InteractiveBrowserCredential
import apex.results as arp
import apex.clients as ac
import asyncio

# NOT CURRENTLY UPDATED: refer to thread_with_aida.py

# Enter execution label: 6.12.25.scan.test
# Enter your AIDA debug ID: 98756551-ae22-4fa0-ba54-cb3c4337b719

# TODO
# fail rate

# README
# need "/certificates/tls-ca-bundle.crt" in cwd
# need snowflake and apex-next datalake permissions

def findColIndex(col_name, columns):
    if col_name not in columns:
        raise ValueError(f"column '{col_name}' not found")
    return columns.index(col_name)

def extract_die_revision(testflow_path):
    with open(testflow_path, 'r') as file:
        for line in file:
            if 'revision :' in line:
                parts = line.split('revision :', 1)
                revision_part = parts[1].split(',', 1)[0].strip()
                return revision_part
    return None

# get verification path
current_directory = os.getcwd()
relative_path = os.path.join(current_directory)
certificate_path = relative_path + "/certificates/tls-ca-bundle.crt"

# start session
session = requests.Session()

# Prompt for user credentials
# username = input("Enter your AMD username: ")
# password = getpass.getpass("Enter your AMD password: ")
# exec_label = input("Enter execution label: ") # restart
# AIDA_debug_ID = input("Enter your AIDA debug ID: ") # 4ce71db8-dbb2-4995-a603-4aa8832e39b2
username = 
password = 
exec_label = "SYSVAL.INT.STXH.101BCDENDA-250417.FP11.0530.PPSV4694.EXP04_1001cRC2_Pre01_RevertPSP_RC62-NDA_CS7.05.16.143_TDR0_1500RB-S5_Test"
AIDA_debug_ID = "9acd7f78-ed87-4c4d-a843-ad9bd743d316"
print("\n")

conn = snowflake.connector.connect(
    user=username,
    account='amd02.east-us-2.azure',
    warehouse='APEX_WH',
    database='APEX_TEST_RESULTS',
    schema='V2',
    authenticator='externalbrowser'  # SSO login
)

try:
    print("\nConnecting to Snowflake\n")
    cur = conn.cursor()
    cur.execute("SELECT CURRENT_USER(), CURRENT_ACCOUNT(), CURRENT_ROLE()")
    print(cur.fetchone())

    # VSYSTEM_CONFIG VIEW
    print("\nQuerying VSYSTEM_CONFIG")
    sql_query = "SELECT * FROM VSYSTEM_CONFIG WHERE EXECUTION_LABEL = %s"
    cur.execute(sql_query, (exec_label))
    # sql_query = "SELECT * FROM VSYSTEM_CONFIG WHERE TEST_RESULT_SEQ_ID = 131401770"
    # cur.execute(sql_query)
    row = cur.fetchone()
    print(row)
    columns = [d[0] for d in cur.description]

    for col_name, value in zip(columns, row):
        print(f"{col_name}: {value}")

    bios = row[findColIndex("BIOS", columns)]
    bios_date = row[findColIndex("BIOS_DATE", columns)]
    program = row[findColIndex("CPU_PROGRAM", columns)]
    program_short = row[findColIndex("CPU_PROGRAM_SHORT", columns)]
    os_name = row[findColIndex("OS", columns)]
    system = row[findColIndex("CPU_SOCKET", columns)]

    # VEXECUTION_RESULT VIEW
    print("\nQuerying VEXECUTION_RESULT")
    sql_query = "SELECT * FROM VEXECUTION_RESULT WHERE EXECUTION_LABEL = %s"
    cur.execute(sql_query, (exec_label))
    # sql_query = "SELECT * FROM VEXECUTION_RESULT WHERE TEST_RESULT_SEQ_ID = 131401770"
    # cur.execute(sql_query)
    row = cur.fetchone()
    print(row)
    columns = [d[0] for d in cur.description]

    for col_name, value in zip(columns, row):
        print(f"{col_name}: {value}")

    ads_type = row[findColIndex("ADS_USAGE", columns)]
    if (ads_type == "None"):
        print("No ADS")
        exit()
    description = row[findColIndex("FAILURE_DESCRIPTION", columns)] # usually none
    scrut_url = row[findColIndex("SCRUTINIZER_URL", columns)]
    ads_link = row[findColIndex("ADS_RESULT_LINK", columns)]
    board = row[findColIndex("TARGET_PLATFORM", columns)]
    seqid = row[findColIndex("TEST_RESULT_SEQ_ID", columns)]
    test_queue = row[findColIndex("QUEUE_NAME", columns)]
    fail_type = row[findColIndex("FAILURE_TYPE", columns)]
    result = row[findColIndex("RESULT", columns)]
    result_type = row[findColIndex("RESULT_TYPE", columns)]
    exit_code = row[findColIndex("EXIT_CODE", columns)]

    
finally:
    print("\nClosing Snowflake connection")
    cur.close()
    conn.close()

# QUERY DATA LAKE FOR FILES 
pipeline = arp.Pipeline.apex
tenant_id = ac._AMD_TENANT_ID
target_dir = "./eras/" + str(seqid)

storageinfo = pipeline.prodinfo
creds = InteractiveBrowserCredential(
        tenant_id=tenant_id,
        )

print("\nQuerying apex-next\n")
asyncio.run(arp.download_eras(
    seqids=[seqid],
    download_dir=target_dir,
    creds=creds,
    storageinfo=storageinfo,
    )) 

# parse apex-next files
ERA_path = target_dir + "/platform-test-results/flat-storage/" + str(seqid)

testflow_path = ERA_path + "/testflow.log"
die_revision = extract_die_revision(testflow_path)

# test_summary_path = ERA_path + "/summary.json"
# with open(test_summary_path, 'r') as file:
#     summary_data = json.load(file)
# req_loops = summary_data['REQUESTED_LOOPS']
# comp_loops = summary_data['COMPLETED_LOOPS']
# fail_loops = summary_data['FAILED_LOOPS']
# fail_data = str(fail_loops) + "/" + str(comp_loops)
# if (comp_loops != req_loops):
#     fail_data += ", " + str(req_loops) + " requested"

result_path = ERA_path + "/result.json"
with open(result_path, 'r') as file:
    result_data = json.load(file)
req_loops = result_data['TestInfo']['Loops']
failing_loop = result_data['FailureInfo']['FailingLoop']
if result_data['TestInfo']['Status'] == "Pass":
    fail_data = "Pass"
else:
    fail_data = "failed at " + str(failing_loop) + "/" + str(req_loops)

sut_config_path = ERA_path + "/sut_config.json"
scan_path = ERA_path + "/device_scan.zip"
BSOD_path = ERA_path + "/crash_dump.dmp"
sleep_study_path = ERA_path + "/sleep_study.html"
amdz_path = ERA_path + "/amdz.txt"

# log in AIDA
print("\nConnecting to AIDA")
login_header = {'Content-Type': 'application/json'}
login_data = {
"username": username,
"password": password
}
login_response = session.post("https://aida.amd.com/api/auth/login", headers=login_header, json=login_data, verify=certificate_path)
if login_response.status_code != 200:
    print("login failed. exiting")
    exit()
print("\nlogin successful")

# get AIDA summary
print("\nQuerying AIDA summary")
AIDA_url = "https://aida.amd.com/api/debug/" + AIDA_debug_ID
AIDA_response =  session.get(AIDA_url, verify=certificate_path)
if AIDA_response.status_code != 200:
    print(f"get error {AIDA_response.status_code}")
    exit()
    
AIDA_data_json = AIDA_response.json().get('debugData').get('prompts')[0]
summary = AIDA_data_json.get('outputlog')
status = AIDA_data_json.get('status')

print("\nData collection successful\n")

print(f"seqid: {seqid}")

print(f"\nAIDA Status: {status}")

print("\n1. PLAT Ticket\n")
print("Project: PLAT")
print("\nIssue Type: Task\n")

print("\n2. Summary / Ticket Title")
print(f"\n[{program_short}][{board}] (JIRA bot generated) [FR: {fail_data}]\n") # TODO issue type and description
print(f"description: {description}")
print(f"fail type: {fail_type}")
print(f"result: {result}")
print(f"result type: {result_type}")
print(f"exit code: {exit_code}")

print("\n3. Ticket Information")
print(f"\nProgram: {program}")
print(f"\nSystem: {system}")
print(f"\nSilicon-Die Revision: {die_revision}")
print(f"\nBIOS Version: {bios}, {bios_date}")
print("\nFunctional Area: Clarification/Validation")
print("\nTriage Category: APU")
print("\nTriage Assignment: Client - Platform Debug - HW")
print("\nSeverity: medium\n")

print("\n4. Description\n")
print("AIDA Summary: ")
print(summary)
print("\nSUT Configuration: ")
print(f"file at: {sut_config_path}\n")

print("\n5. Steps to Reproduce\n")
print(f"APEX Queue: {test_queue}")
print(f"OS: {os_name}\n")

print("\n6. Other")
print(f"\nADS: {ads_link}")
print(f"\nScrutinizer URL: {scrut_url}\n")
if os.path.exists(amdz_path):
    print("\nAMDz: ")
    print(f"file at: {amdz_path}")
else:
    print("No AMDz file found")
if os.path.exists(scan_path):
    print("\nScan: ")
    print(f"file at: {scan_path}")
else:
    print("No scan file found")
if os.path.exists(BSOD_path):
    print("\nBSOD Dump: ")
    print(f"file at: {BSOD_path}")
else:
    print("No BSOD dump file found")
if os.path.exists(sleep_study_path):
    print("\nSleep Study: ")
    print(f"file at: {sleep_study_path}")
else:
    print("No sleep study file found")

# print("\n7. Labels")
