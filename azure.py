issues = jira.client.search_issues(         # note “client”, not “run”
            jql_str   = "project = STXH ORDER BY updated DESC",
            maxResults=2                    # camel‑case R (SDK style)
)
for i in issues:
    print(i.key, i.fields.summary)
