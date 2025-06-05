from langchain_community.utilities.jira import JiraAPIWrapper

jira = JiraAPIWrapper(
    jira_instance_url="https://ontrack-internal.amd.com",
    jira_api_token   ="MjQ0MzM3NDQzNTY0OsLr4yZLHgekftk2OkuNGC+Ngumk",
)

print([attr for attr in dir(jira) if attr.startswith("_") or attr.endswith("client")])
