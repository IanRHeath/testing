curl -X POST \
  "https://llm-api.amd.com/openai/deployments/<DEPLOYMENT_NAME>/chat/completions?api-version=2024-05-01-preview" \
  -H "Content-Type: application/json" \
  -H "api-key: 37f0bc138e7944eab89e3421d445675f" \
  -H "Ocp-Apim-Subscription-Key: 37f0bc138e7944eab89e3421d445675f" \
  -d '{
        "messages":[{"role":"user","content":"Hello"}],
        "max_tokens":1
      }'
