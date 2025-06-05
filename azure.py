# jira_probe.py  –  run with:  python jira_probe.py
# The "atlassian" package is already a dependency of langchain‑community
from atlassian import Jira

jira = Jira(
    url   = "https://ontrack-internal.amd.com",
    token = "MjQ0MzM3NDQzNTY0OsLr4yZLHgekftk2OkuNGC+Ngumk",  #  PAT  (Data‑Center)
    cloud = False                                           #  DC/Server mode
    # If your server still requires a username, add  username="iheath12"
)

response = jira.jql(
    "project = STXH ORDER BY updated DESC",
    limit = 2          # hard cap to 2 results
)

issues = response["issues"]
print("Got", len(issues), "issues")
for i in issues:
    fields = i["fields"]
    print(
        i["key"],
        fields["summary"],
        f"[{fields['status']['name']}]"
    )
