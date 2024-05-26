from flask import Flask, render_template, request, redirect, url_for, session, make_response
from pymongo import MongoClient
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import random
import logging

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MongoDB connection
client = MongoClient('mongodb+srv://tapusahamnb:fjdaZM74M9xbAzY5@cluster0.4hpeghp.mongodb.net/')
db = client["LMS"]
credentials_collection = db["credentials"]

logging.basicConfig(level=logging.DEBUG)

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'email' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']
    user = credentials_collection.find_one({'email': email, 'password': password})
    if user:
        session['email'] = email
        return redirect(url_for('dashboard'))
    return 'Invalid Credentials'

@app.route('/dashboard')
def dashboard():
    if 'email' in session:
        return render_template('dashboard.html', email=session['email'])
    return redirect(url_for('index'))

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'email' in session:
        if request.method == 'POST':
            year = request.form['year']
            semester = request.form['semester']
            marks = request.form['marks']
            question = request.form['question']

            collection_name = f"{year}_{semester}"
            collection = db[collection_name]
            collection.insert_one({
                'marks': marks,
                'question': question
            })
            return redirect(url_for('dashboard'))
        return render_template('upload_questions.html')
    return redirect(url_for('index'))


@app.route('/generate', methods=['GET', 'POST'])
def generate():
    if 'email' in session:
        if request.method == 'POST':
            year = request.form['year']
            semester = request.form['semester']
            num_2_marks = int(request.form['num_2_marks'])
            num_5_marks = int(request.form['num_5_marks'])
            num_10_marks = int(request.form['num_10_marks'])

            collection_name = f"{year}_{semester}"
            collection = db[collection_name]

            questions_2_marks = list(collection.find({'marks': '2'}))
            questions_5_marks = list(collection.find({'marks': '5'}))
            questions_10_marks = list(collection.find({'marks': '10'}))

            selected_questions = (
                random.sample(questions_2_marks, min(num_2_marks, len(questions_2_marks))) +
                random.sample(questions_5_marks, min(num_5_marks, len(questions_5_marks))) +
                random.sample(questions_10_marks, min(num_10_marks, len(questions_10_marks)))
            )

            if not selected_questions:
                selected_questions = [{'marks': 'N/A', 'question': 'No questions available for the selected criteria.'}]

            pdf_buffer = generate_pdf(selected_questions)

            response = make_response(pdf_buffer)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = 'attachment; filename=question_paper.pdf'

            return response
        return render_template('generate_questions.html')
    return redirect(url_for('index'))

def generate_pdf(questions):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Load the background image
    background_image_path = 'static/Copy of DATE2.png'
    try:
        background = ImageReader(background_image_path)
    except Exception as e:
        logging.error(f"Error loading background image: {e}")
        return b''

    def draw_background(c, width, height):
        try:
            c.drawImage(background, 0, 0, width=width, height=height)
        except Exception as e:
            logging.error(f"Error drawing background image: {e}")

    # Draw the first page background
    draw_background(c, width, height)

    y_position = height - 190  # Adjust this value to move content lower
    serial_number = 1

    c.setFont("Helvetica-Bold", 16)
    c.drawString(250, height - 160, "Question Paper")  # Adjust title position
    c.setFont("Helvetica", 12)
    for question in questions:
        if y_position < 60:
            c.showPage()
            draw_background(c, width, height)
            y_position = height - 80  # Adjust this value to move content lower on new pages
        c.drawString(40, y_position, f"{serial_number}. {question['marks']} Marks")
        y_position -= 20
        text = c.beginText(40, y_position)
        text.setFont("Helvetica", 12)
        for line in question['question'].splitlines():
            if y_position < 40:
                c.showPage()
                draw_background(c, width, height)
                y_position = height - 60  # Adjust this value to move content lower on new pages
                text = c.beginText(40, y_position)
                text.setFont("Helvetica", 12)
            text.textLine(line)
            y_position -= 14
        c.drawText(text)
        y_position -= 20
        serial_number += 1

    c.save()
    buffer.seek(0)
    return buffer.getvalue()


if __name__ == '__main__':
    app.run(debug=True)
