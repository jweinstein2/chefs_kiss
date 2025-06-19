from flask import Flask, request, Response
import requests
import openai
import json

# TODO
# 1. Handle multiple numbers? Multiple databases? 

# Your Twilio credentials
ACCOUNT_SID = ''
AUTH_TOKEN = ''
TWILIO_NUMBER = '+18449092927'  # Your Twilio phone number

NOTION_TOKEN = ""  # your integration token
DATABASE_ID = "" # your database ID

URL_PATTERN = "^https?:\\/\\/(?:www\\.)?[-a-zA-Z0-9@:%._\\+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b(?:[-a-zA-Z0-9()@:%_\\+.~#?&\\/=]*)$"

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def make_page_data(title, ingredients, steps):
    return {
    "parent": { "database_id": DATABASE_ID },
    "properties": {
        "Name": {
            "title": [
                {
                    "text": {
                        "content": title,
                    }
                }
            ]
        },
    },
    "children": [
        # Ingredients header
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{
                    "type": "text",
                    "text": { "content": "Ingredients" }
                }]
            }
        },
        # Ingredient items as unchecked to-dos
        *[
            {
                "object": "block",
                "type": "to_do",
                "to_do": {
                    "rich_text": [{
                        "type": "text",
                        "text": { "content": ingredient }
                    }],
                    "checked": False
                }
            } for ingredient in ingredients 
        ],
        # Instructions header
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{
                    "type": "text",
                    "text": { "content": "Instructions" }
                }]
            }
        },
        # Instruction steps as bullet points
        *[
            {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{
                        "type": "text",
                        "text": { "content": step }
                    }]
                }
            } for step in steps 
        ]
    ]
}

def post_to_notion(title, ingredients, steps):
    page_data = make_page_data(title, ingredients, steps)
    response = requests.post("https://api.notion.com/v1/pages", headers=headers, json=page_data)
    print(response.status_code)
    print(response.json())


# # Create OpenAI client
# openai.api_key = os.getenv("OPENAI_API_KEY")
ai_client = openai.OpenAI()

def parse(html_content):
    # Define the expected schema
    tool_spec = {
        "type": "function",
        "function": {
            "name": "extract_recipe",
            "description": "Extract recipe information from a webpage and return structured JSON.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": { "type": "string" },
                    "ingredients": {
                        "type": "array",
                        "items": { "type": "string" }
                    },
                    "steps": {
                        "type": "array",
                        "items": { "type": "string" }
                    }
                },
                "required": ["title", "ingredients", "steps"]
            }
        }
    }

    prompt = f"""
    Extract the recipe information from the following webpage content:

    \"\"\"
    {html_content}
    \"\"\"
    """

    response = ai_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "user", "content": prompt}
        ],
        tools=[tool_spec],
        tool_choice={"type": "function", "function": {"name": "extract_recipe"}},
    )

    # Extract structured output
    tool_output = response.choices[0].message.tool_calls[0].function.arguments
    data = json.loads(tool_output)
    title = data["title"]
    ingredients = data["ingredients"]
    steps = data["steps"]
    post_to_notion(title, ingredients, steps)

def fetch_recipe(url):
    response = requests.get(url)
    if response.status_code == 200:
        html_content = response.text
        parse(html_content)

    else:
        print(f"Failed to fetch the page: {response.status_code}")

app = Flask(__name__)

@app.route("/sms", methods=['POST'])
def sms_reply():
    incoming_msg = request.form.get('Body')
    from_number = request.form.get('From')
    print(f"Received message from {from_number}: {incoming_msg}")

    # Optional response
    resp = MessagingResponse()
    resp.message("Thanks for your message!")
    return Response(str(resp), mimetype="application/xml")

if __name__ == "__main__":
    app.run(debug=True)
