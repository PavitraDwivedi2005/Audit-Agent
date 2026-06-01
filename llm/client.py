# llm/client.py
# pyrefly: ignore [missing-import]
import google.generativeai as genai
import json
import os

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")

def generate_audit(data: dict) -> str:
    # Extract username safely for the title
    username = data.get("profile_metrics", {}).get("username", {}).get("value", "User")
    
    # Convert structured data to a clean JSON string for the LLM
    json_metrics = json.dumps(data, indent=2)

    prompt = f"""You are a professional Instagram analytics auditor.

Analyze the following Instagram profile data and generate a comprehensive audit report for @{username}.
The data is provided in JSON format. Note that some metrics may have a status of "missing" or "unavailable". 

**Profile Data:**
```json
{json_metrics}
```

**Generate a report with these sections:**
1. 📋 Profile Overview (2-3 sentences)
2. 💪 Strengths (3-5 bullet points)
3. ⚠️ Weaknesses (3-5 bullet points)
4. 📊 Engagement Analysis (compare to industry benchmarks)
5. 🎯 Recommendations (5 actionable steps)
6. 📈 Overall Score (out of 100, with justification)

Use a professional but approachable tone. Include specific numbers. If a metric is unavailable, do not invent it."""

    response = model.generate_content(prompt)
    return response.text
