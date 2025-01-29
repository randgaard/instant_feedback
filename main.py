import time
import os
import json
from flask import Flask, request, jsonify, render_template
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
    # Hent filer
    cv_file = request.files.get("cv")
    cover_letter_file = request.files.get("cover_letter")

    if not cv_file:
        # Evt. kun tving brugeren til at uploade CV
        return jsonify({"error": "CV skal uploades"}), 400

    # Gem filer midlertidigt
    cv_path = os.path.join(app.config['UPLOAD_FOLDER'], cv_file.filename)
    cv_file.save(cv_path)
    cv_markdown = convert_pdf_to_markdown(cv_path)
    os.remove(cv_path)

    # OpenAI Assistant ID
    ID = "asst_dzEA0dbwCb5in1OMWgcIp2z7"
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    try:
        if cover_letter_file and cover_letter_file.filename != "":
            # ============================
            # CV + Ansøgning logik
            # ============================
            cover_letter_path = os.path.join(app.config['UPLOAD_FOLDER'], cover_letter_file.filename)
            cover_letter_file.save(cover_letter_path)
            cover_letter_markdown = convert_pdf_to_markdown(cover_letter_path)
            os.remove(cover_letter_path)

            # Prompt med CV og ansøgning + JSON schema for begge
            chat = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "user", "content": "Giv feedback baseret på dette CV og ansøgning:"},
                    {"role": "user", "content": f"CV: {cv_markdown}"},
                    {"role": "user", "content": f"Ansøgning: {cover_letter_markdown}"}
                ],
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

            feedback = chat.choices[0].message.content
            feedback_parsed = json.loads(feedback)

            return jsonify({
                "cv_feedback": feedback_parsed["cv_feedback"],
                "cover_letter_feedback": feedback_parsed["cover_letter_feedback"]
            })

        else:
            # ============================
            # Kun CV logik
            # ============================
            # Prompt KUN for CV + JSON schema KUN for CV
            chat = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "user", "content": "Giv feedback baseret på dette CV:"},
                    {"role": "user", "content": f"CV: {cv_markdown}"}
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "cv_only_feedback",
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
                                }
                            },
                            "required": ["cv_feedback"],
                            "additionalProperties": False
                        }
                    }
                }
            )

            feedback = chat.choices[0].message.content
            feedback_parsed = json.loads(feedback)

            # Returner kun CV-feedback
            return jsonify({
                "cv_feedback": feedback_parsed["cv_feedback"]
            })

    except Exception as e:
        return jsonify({"error": f"Fejl ved API-kald: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True)
