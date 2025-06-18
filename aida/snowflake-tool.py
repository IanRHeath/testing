# Snowflake execution label finding tool

# This script finds execution labels that can be used to test auto filer
# test requirements: 
#   recent (june 2025)
#   execution label is not none
#   ADS on
#   ADS report generated
#   some failures occured

# Step 1: run script with your username entered below
#   - must have snowflake access to APEX_TEST_RESULTS database to run
# Step 2: examine each execution label for validity
#   - open ads report to ensure it's still valid
#   - make sure scrut shows some fails 

username =

#######################################################

import snowflake.connector

conn = snowflake.connector.connect(
    user=username,
    account='amd02.east-us-2.azure',
    warehouse='APEX_WH',
    database='APEX_TEST_RESULTS',
    schema='V2',
    authenticator='externalbrowser'  # SSO login
)

def findColIndex(col_name, columns):
    if col_name not in columns:
        raise ValueError(f"column '{col_name}' not found")
    return columns.index(col_name)

execution_labels = []
ads_links = []
scrut_links = []

unique_labels = set()

try:
    print("\nConnecting to Snowflake\n")
    cur = conn.cursor()
    cur.execute("SELECT CURRENT_USER(), CURRENT_ACCOUNT(), CURRENT_ROLE()")
    print(cur.fetchone())

    # VEXECUTION_RESULT VIEW
    print("\nQuerying VEXECUTION_RESULT")
    sql_query = "SELECT * FROM VEXECUTION_RESULT WHERE ADS_RESULT_LINK IS NOT NULL AND LEFT(ADS_RESULT_LINK, %s) = %s AND EXECUTION_LABEL != %s LIMIT 50"
    prefix = 'file://atlcorpnetfs.amd.com/ads_data_na/ads2/2025/06'
    prefix_length = str(len(prefix))
    cur.execute(sql_query, (prefix_length, prefix, "== None =="))
    columns = [d[0] for d in cur.description]

    rows = cur.fetchall()
    
    for row in rows:
        exec_label = str(row[findColIndex("EXECUTION_LABEL", columns)])
        execution_labels.append(exec_label)
        ads_links.append(str(row[findColIndex("ADS_RESULT_LINK", columns)]))
        test_queue = str(row[findColIndex("QUEUE_NAME", columns)])
        s_link = "http://scrutinizer.amd.com/project/v2?queue_string=" + test_queue + "&execution_label=" + exec_label
        scrut_links.append(s_link)

    for i in range(0, 50):
        if execution_labels[i] in unique_labels:
            continue
        else:
            unique_labels.add(execution_labels[i])
            print(f"\nexecution label: {execution_labels[i]}")
            print(f"ads link: {ads_links[i]}")
            print(f"scrut link: {scrut_links[i]}")
    
finally:
    print("\nClosing Snowflake connection")
    cur.close()
    conn.close()
