# Multi threaded data pulling from snowflake + AIDA debug runs for each failure

# Must have ./certificates/tls-ca-bundle.crt in cwd
# Must have snowflake access to APEX_TEST_RESULTS database to run

username = ""
password = ""
exec_label = ""

##################################################

import threading
import time
import requests
import os
import json
import getpass
import snowflake.connector
from azure.identity import InteractiveBrowserCredential
import apex.results as arp
import apex.clients as ac
import asyncio
from dataclasses import dataclass, field
from typing import Any
import re

print("\n")

@dataclass
class TestItem:
    result: Any = None
    seqid: Any = None
    ads_link: Any = None
    ads_usage: Any = None
    test_item_name: Any = None
    test_item_index: Any = None
    program_short: Any = None
    job_id: Any = None
    adId: Any = None
    summary: Any = None

class ExpandableMatrix:
    def __init__(self):
        self.matrix = []
        self.lock = threading.Lock()

    def add(self, row, value):
        with self.lock:
            while len(self.matrix) <= row:
                self.matrix.append([])

            self.matrix[row].append(value)

    def get(self, row, col):
        with self.lock:
            if row < len(self.matrix) and col < len(self.matrix[row]):
                return self.matrix[row][col]
            return None

    def __str__(self):
        with self.lock:
            return '\n'.join(str(row) for row in self.matrix)

    def print_matrix(self):     
        with self.lock:
            for row in self.matrix:
                if row:

                    print(f"\n{row[0].test_item_index}. {row[0].test_item_name}:")

                    for col in row:
                        print(f"SEQ: {col.seqid}, ads link: {col.ads_link}, AIDA ID: {col.adId}")

        
def findColIndex(col_name, columns):
    if col_name not in columns:
        raise ValueError(f"column '{col_name}' not found")
    return columns.index(col_name)

failed_items = ExpandableMatrix()

# get verification path
current_directory = os.getcwd()
relative_path = os.path.join(current_directory)
certificate_path = relative_path + "/certificates/tls-ca-bundle.crt"

def query_Snowflake(row, columns):
    item = TestItem()

    item.result = row[findColIndex("RESULT", columns)]
    item.seqid = row[findColIndex("TEST_RESULT_SEQ_ID", columns)]

    if item.result == "Pass":
        print(f"SEQ {item.seqid} pass")
        return
    
    item.ads_link = row[findColIndex("ADS_RESULT_LINK", columns)]
    item.ads_usage = row[findColIndex("ADS_USAGE", columns)]
    item.test_item_name = row[findColIndex("QUEUE_ITEM_NAME", columns)]
    item.test_item_index = row[findColIndex("QUEUE_ITEM_INDEX", columns)]

    pattern = r'/([0-9a-fA-F-]{36})/reports'
    match = re.search(pattern, str(item.ads_link))
    if match:
        item.job_id = match.group(1)

    curs = conn.cursor()
    sql_query = "SELECT * FROM VSYSTEM_CONFIG WHERE TEST_RESULT_SEQ_ID = %s"
    curs.execute(sql_query, (str(item.seqid)))
    row2 = curs.fetchone()
    columns = [d[0] for d in curs.description]

    item.program_short = row2[findColIndex("CPU_PROGRAM_SHORT", columns)]

    if item.ads_link == None:
        print(f"SEQ {item.seqid} fail, Prog: {item.program_short}, ads_usage: {item.ads_usage}")
    else:
        failed_items.add(item.test_item_index, item)

        AIDA_url = "https://aida.amd.com/api/debug/queueDebug"
        start_debug_header = {'Content-Type': 'application/json'}
        start_debug_data = {
        "queueType": "ads",
        "debugData": {
            "jobId": str(item.job_id),
            "useOfflineMethod": "true",
            "configOption": "16"
        }
        }
        AIDA_response =  session.post(AIDA_url, headers=start_debug_header, json=start_debug_data, verify=certificate_path)
        if AIDA_response.status_code != 200:
            print(f"post error {AIDA_response.status_code}")
            exit()
            
        item.adId = AIDA_response.json().get('adId')
        print(f"SEQ {item.seqid} fail, Prog: {item.program_short}, ads_link: {item.ads_link}, adId: {item.adId}")

        # wait for AIDA to end 
        AIDA_url = "https://aida.amd.com/api/debug/" + str(item.adId)
        while True:
            AIDA_summary = session.get(AIDA_url, verify=certificate_path)
            if AIDA_summary.status_code != 200:
                print(f"get error {AIDA_summary.status_code}")
                exit()
            AIDA_data_json = AIDA_summary.json().get('debugData').get('prompts')[0]
            item.summary = AIDA_data_json.get('outputlog')
            status = AIDA_data_json.get('status')
            promptid = AIDA_data_json.get('promptid')
            if status == "completed" or status == "Completed":
                break
            #print(f"yielding for adid {item.adId}")
            time.sleep(1)
            time.sleep(0) # yield

        # give feedback
        AIDA_url = "https://aida.amd.com/api/debug/addFeedback"
        add_feedback_header = {'Content-Type': 'application/json'}
        add_feedback_data = {
        "feedbackInfo": {
            "rating": "correct",
            "ratingContext": "",
            "feedback": "",
            "promptId": str(promptid),
            "adId": str(item.adId)
        }
        }
        AIDA_feedback =  session.post(AIDA_url, headers=add_feedback_header, json=add_feedback_data, verify=certificate_path)
        if AIDA_feedback.status_code != 200:
            print(f"post error {AIDA_feedback.status_code}")
            exit()

# start session
session = requests.Session()

# log in
login_header = {'Content-Type': 'application/json'}
login_data = {
"username": username,
"password": password
}
login_response = session.post("https://aida.amd.com/api/auth/login", headers=login_header, json=login_data, verify=certificate_path)
if login_response.status_code != 200:
    print("login failed. exiting")
    exit()
print("login successful\n")

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

    # VEXECUTION_RESULT VIEW
    print("\nQuerying VEXECUTION_RESULT")
    sql_query = "SELECT * FROM VEXECUTION_RESULT WHERE EXECUTION_LABEL = %s"
    cur.execute(sql_query, (exec_label))
    rows = cur.fetchall()
    columns = [d[0] for d in cur.description]

    threads = []
    for row in rows:
        thread = threading.Thread(target=query_Snowflake, args=(row, columns))
        thread.start()
        threads.append(thread)

    for thread in threads:
        #print("joining")
        thread.join()

finally:
    failed_items.print_matrix()
    print("\nClosing Snowflake connection")
    cur.close()
    conn.close()