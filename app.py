import os
import json
from flask import Flask, request, render_template
from flask_cors import CORS
from groq import Groq  # Importing Groq API client
import re
app = Flask(__name__)
CORS(app)

# Load Groq API Key
API_KEY = "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"
if not API_KEY:
    raise ValueError("GROQ_API_KEY is not set")

client = Groq(api_key=API_KEY)  # Initialize the Groq client

@app.route('/')
def index():
    return render_template('index.html')

def parse_api_response(response):
    """Parses the JSON response from the Groq API and ensures valid MCQ structure."""
    # Ensure response exists and contains the expected fields
    try:
        # Extract text content from API response
        response_text = response.strip()
        print(response_text)
        response_text = re.sub(r"```json|\```", "", response).strip()
        print(response_text)
        # If response is empty, return a default message
        if not response_text:
            return [{"question": "No content in API response", "category": "N/A", "options": [], "correct_answer": "N/A"}]

        # Try parsing as JSON
        parsed_data = json.loads(response_text)
        # Ensure response is a list of questions
        if isinstance(parsed_data, list):
            questions = []
            for item in parsed_data:
                if isinstance(item, dict) and "question" in item and "options" in item and "correct_answer" in item:
                    questions.append({
                        "question": item["question"],
                        "category": item.get("category", "General Knowledge"),
                        "options": item["options"],
                        "correct_answer": item["correct_answer"]
                    })
                else:
                    print("Invalid item structure:", item)

            return questions if questions else [{"question": "Invalid API response", "category": "N/A", "options": [], "correct_answer": "N/A"}]

        else:
            return [{"question": "API response format incorrect", "category": "N/A", "options": [], "correct_answer": "N/A"}]

    except json.JSONDecodeError as e:
        print(f"Error parsing API response: {e}")
        return [{"question": "Error parsing response", "category": "N/A", "options": [], "correct_answer": "N/A"}]

@app.route('/get_mcq', methods=['POST'])
def get_mcq():
    if request.method == 'POST':
        data = request.json
        try:
            result = generate_mcq_questions(data)
            return render_template('result.html', result1=result)
        except Exception as e:
            return render_template('result.html', error=str(e))

def generate_mcq_questions(data):
    """Generates MCQ questions using Groq API."""
    course = data.get('course', 'Unknown')
    stream = data.get('stream', 'General')
    try:
        count1 = int(data.get('Q1_count', 5))
        Q1_time = int(data.get('Q1_time', 10))
    except (ValueError, TypeError):
        raise ValueError("Q1_count and Q1_time must be valid numbers")
    
    if count1 <= 0 or Q1_time <= 0:
        raise ValueError("Q1_count and Q1_time must be positive")

    category = f"{course} for {stream}"
    format_example = """
    {
      "question": "Sample question?",
      "category": "Technical Proficiency",
      "options": ["Option1", "Option2", "Option3", "Option4"],
      "correct_answer": "Option1"
    }
    """

    prompt = f"""
    Generate {count1} multiple-choice questions for a Technical Proficiency test on '{category}'.
    Each question should have 4 options and one correct answer.
    Return the output as a JSON array, following this structure:
    {format_example}
    """

    try:
        chat_completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}]
        )
        result_text = chat_completion.choices[0].message.content if chat_completion.choices else ""
    except Exception as e:
        raise Exception(f"API Error: {str(e)}")

    questions = parse_api_response(result_text)
    result = {
        "testname": "Technical Proficiency",
        "questions": questions if questions else [{"question": "No questions generated", "category": category, "options": [], "correct_answer": "N/A"}]
    }
    try:
        with open("Questions.json", "w") as json_file:
            json.dump({'MCQ_Questions': [result]}, json_file, indent=4)
    except Exception as e:
        print(f"Error writing to file: {e}")

    return result

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
