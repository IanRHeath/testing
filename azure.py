from langchain_community.utilities.jira import JiraAPIWrapper

jira = JiraAPIWrapper(
    jira_instance_url = "https://ontrack-internal.amd.com",
    jira_api_token    = "MjQ0MzM3NDQzNTY0OsLr4yZLHgekftk2OkuNGC+Ngumk",
    # no username for DC PAT
)

issues = jira.search_issues(jql="project = STXH ORDER BY updated DESC", max_results=2)
print("Got", len(issues), "issues")
for i in issues:
    print(i.key, i.fields.summary, f"[{i.fields.status.name}]")
