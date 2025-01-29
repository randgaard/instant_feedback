from flask import Flask, request, jsonify, render_template
import os
import json
import PyPDF2
from markitdown import MarkItDown
from openai import OpenAI

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def convert_pdf_to_markdown(pdf_path):
    try:
        md = MarkItDown()
        result = md.convert(pdf_path)
        return result.text_content
    except Exception as e:
        return f"Fejl ved konvertering af PDF til Markdown: {e}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    user_input = request.form.get("user_input", "")
    cv_file = request.files.get("cv")
    cover_letter_file = request.files.get("cover_letter")

    if not cv_file or not cover_letter_file:
        return jsonify({"error": "Både CV og ansøgning skal uploades."}), 400

    cv_path = os.path.join(app.config['UPLOAD_FOLDER'], cv_file.filename)
    cover_letter_path = os.path.join(app.config['UPLOAD_FOLDER'], cover_letter_file.filename)

    cv_file.save(cv_path)
    cover_letter_file.save(cover_letter_path)

    # Konverter PDF-filer til Markdown
    cv_markdown = convert_pdf_to_markdown(cv_path)
    cover_letter_markdown = convert_pdf_to_markdown(cover_letter_path)

    # os.remove(cv_path)
    # os.remove(cover_letter_path)

    # OpenAI Assistant ID
    ID = "asst_dzEA0dbwCb5in1OMWgcIp2z7"

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    try:
        chat = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": "Giv feedback baseret på dette CV og ansøgning:"},
                {"role": "user", "content": f"CV: {cv_markdown}"},
                {"role": "user", "content": f"Ansøgning: {cover_letter_markdown}"}
            ],
            # Det vigtigste er at opdatere response_format til at forvente en JSON-struktur
            # opdelt i "cv_feedback" og "cover_letter_feedback".
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "evaluation_feedback",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "cv_feedback": {
                                "type": "object",
                                "properties": {
                                    "strong_sides": {"type": "string"},
                                    "areas_for_improvement": {"type": "string"},
                                    "improvement_suggestions": {"type": "string"},
                                    "additional_tips": {"type": "string"}
                                },
                                "required": [
                                    "strong_sides",
                                    "areas_for_improvement",
                                    "improvement_suggestions",
                                    "additional_tips"
                                ],
                                "additionalProperties": False
                            },
                            "cover_letter_feedback": {
                                "type": "object",
                                "properties": {
                                    "strong_sides": {"type": "string"},
                                    "areas_for_improvement": {"type": "string"},
                                    "improvement_suggestions": {"type": "string"},
                                    "additional_tips": {"type": "string"}
                                },
                                "required": [
                                    "strong_sides",
                                    "areas_for_improvement",
                                    "improvement_suggestions",
                                    "additional_tips"
                                ],
                                "additionalProperties": False
                            }
                        },
                        "required": ["cv_feedback", "cover_letter_feedback"],
                        "additionalProperties": False
                    }
                }
            }
        )

        # Hent og parse det strukturerede svar
        feedback = chat.choices[0].message.content
        feedback_parsed = json.loads(feedback)

        # Ekstrahér delene til CV og ansøgning
        cv_feedback = feedback_parsed["cv_feedback"]
        cover_letter_feedback = feedback_parsed["cover_letter_feedback"]

        # Returner feedback opdelt for CV og ansøgning
        return jsonify({
            "cv_feedback": {
                "strong_sides": cv_feedback["strong_sides"],
                "areas_for_improvement": cv_feedback["areas_for_improvement"],
                "improvement_suggestions": cv_feedback["improvement_suggestions"],
                "additional_tips": cv_feedback["additional_tips"]
            },
            "cover_letter_feedback": {
                "strong_sides": cover_letter_feedback["strong_sides"],
                "areas_for_improvement": cover_letter_feedback["areas_for_improvement"],
                "improvement_suggestions": cover_letter_feedback["improvement_suggestions"],
                "additional_tips": cover_letter_feedback["additional_tips"]
            }
        })

    except Exception as e:
        return jsonify({"error": f"Fejl ved API-kald: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True)
