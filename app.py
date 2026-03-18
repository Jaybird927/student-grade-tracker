from flask import Flask, render_template, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import io
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///grades.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Database Models
class Term(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'quarter' or 'trimester'
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    classes = db.relationship('Class', backref='term', cascade='all, delete-orphan', lazy=True)

class Class(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    term_id = db.Column(db.Integer, db.ForeignKey('term.id'), nullable=False)
    credits = db.Column(db.Float, default=1.0)
    assignments = db.relationship('Assignment', backref='class_ref', cascade='all, delete-orphan', lazy=True)

class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    category = db.Column(db.String(50))  # homework, test, quiz, project, etc.
    weight = db.Column(db.Float, default=1.0)  # weight multiplier
    points_earned = db.Column(db.Float)
    points_possible = db.Column(db.Float)
    date = db.Column(db.Date)

# Initialize database
with app.app_context():
    db.create_all()

# Helper function to convert percentage to letter grade
def percentage_to_grade(percentage):
    if percentage >= 98:
        return 'A+'
    elif percentage >= 93:
        return 'A'
    elif percentage >= 90:
        return 'A-'
    elif percentage >= 88:
        return 'B+'
    elif percentage >= 83:
        return 'B'
    elif percentage >= 80:
        return 'B-'
    elif percentage >= 78:
        return 'C+'
    elif percentage >= 73:
        return 'C'
    elif percentage >= 70:
        return 'C-'
    elif percentage >= 68:
        return 'D+'
    elif percentage >= 63:
        return 'D'
    elif percentage >= 60:
        return 'D-'
    else:
        return 'F'

# API Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/terms', methods=['GET', 'POST'])
def handle_terms():
    if request.method == 'GET':
        terms = Term.query.all()
        return jsonify([{
            'id': t.id,
            'name': t.name,
            'type': t.type,
            'start_date': t.start_date.isoformat() if t.start_date else None,
            'end_date': t.end_date.isoformat() if t.end_date else None
        } for t in terms])

    elif request.method == 'POST':
        data = request.json
        term = Term(
            name=data['name'],
            type=data['type'],
            start_date=datetime.fromisoformat(data['start_date']).date() if data.get('start_date') else None,
            end_date=datetime.fromisoformat(data['end_date']).date() if data.get('end_date') else None
        )
        db.session.add(term)
        db.session.commit()
        return jsonify({'id': term.id, 'name': term.name}), 201

@app.route('/api/terms/<int:term_id>', methods=['DELETE'])
def delete_term(term_id):
    term = Term.query.get_or_404(term_id)
    db.session.delete(term)
    db.session.commit()
    return '', 204

@app.route('/api/classes', methods=['GET', 'POST'])
def handle_classes():
    if request.method == 'GET':
        term_id = request.args.get('term_id')
        if term_id:
            classes = Class.query.filter_by(term_id=term_id).all()
        else:
            classes = Class.query.all()

        result = []
        for c in classes:
            grade_percent = calculate_class_grade(c.id)
            letter_grade = percentage_to_grade(grade_percent)
            result.append({
                'id': c.id,
                'name': c.name,
                'term_id': c.term_id,
                'credits': c.credits,
                'grade': grade_percent,
                'letter_grade': letter_grade
            })

        return jsonify(result)

    elif request.method == 'POST':
        data = request.json
        class_obj = Class(
            name=data['name'],
            term_id=data['term_id'],
            credits=data.get('credits', 1.0)
        )
        db.session.add(class_obj)
        db.session.commit()
        return jsonify({'id': class_obj.id, 'name': class_obj.name}), 201

@app.route('/api/classes/<int:class_id>', methods=['DELETE'])
def delete_class(class_id):
    class_obj = Class.query.get_or_404(class_id)
    db.session.delete(class_obj)
    db.session.commit()
    return '', 204

@app.route('/api/assignments', methods=['GET', 'POST'])
def handle_assignments():
    if request.method == 'GET':
        class_id = request.args.get('class_id')
        if class_id:
            assignments = Assignment.query.filter_by(class_id=class_id).all()
        else:
            assignments = Assignment.query.all()

        return jsonify([{
            'id': a.id,
            'name': a.name,
            'class_id': a.class_id,
            'category': a.category,
            'weight': a.weight,
            'points_earned': a.points_earned,
            'points_possible': a.points_possible,
            'date': a.date.isoformat() if a.date else None,
            'percentage': (a.points_earned / a.points_possible * 100) if a.points_possible else None
        } for a in assignments])

    elif request.method == 'POST':
        data = request.json
        assignment = Assignment(
            name=data['name'],
            class_id=data['class_id'],
            category=data.get('category'),
            weight=data.get('weight', 1.0),
            points_earned=data.get('points_earned'),
            points_possible=data.get('points_possible'),
            date=datetime.fromisoformat(data['date']).date() if data.get('date') else None
        )
        db.session.add(assignment)
        db.session.commit()
        return jsonify({'id': assignment.id, 'name': assignment.name}), 201

@app.route('/api/assignments/<int:assignment_id>', methods=['PUT', 'DELETE'])
def handle_assignment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)

    if request.method == 'PUT':
        data = request.json
        assignment.name = data.get('name', assignment.name)
        assignment.category = data.get('category', assignment.category)
        assignment.weight = data.get('weight', assignment.weight)
        assignment.points_earned = data.get('points_earned', assignment.points_earned)
        assignment.points_possible = data.get('points_possible', assignment.points_possible)
        if data.get('date'):
            assignment.date = datetime.fromisoformat(data['date']).date()
        db.session.commit()
        return jsonify({'id': assignment.id, 'name': assignment.name})

    elif request.method == 'DELETE':
        db.session.delete(assignment)
        db.session.commit()
        return '', 204

@app.route('/api/report/<int:term_id>')
def generate_report(term_id):
    term = Term.query.get_or_404(term_id)

    # Create PDF in memory
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    # Title
    title = Paragraph(f"<b>Grade Report - {term.name}</b>", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 0.2*inch))

    # Term info
    if term.start_date and term.end_date:
        date_range = Paragraph(f"{term.start_date.strftime('%m/%d/%Y')} - {term.end_date.strftime('%m/%d/%Y')}", styles['Normal'])
        elements.append(date_range)
        elements.append(Spacer(1, 0.3*inch))

    # Classes and assignments
    classes = Class.query.filter_by(term_id=term_id).all()

    for class_obj in classes:
        # Class header
        class_header = Paragraph(f"<b>{class_obj.name}</b> (Credits: {class_obj.credits})", styles['Heading2'])
        elements.append(class_header)
        elements.append(Spacer(1, 0.1*inch))

        # Assignments table
        assignments = Assignment.query.filter_by(class_id=class_obj.id).all()

        if assignments:
            data = [['Assignment', 'Category', 'Score', 'Percentage']]
            for a in assignments:
                percentage = f"{(a.points_earned / a.points_possible * 100):.1f}%" if a.points_possible else "N/A"
                score = f"{a.points_earned}/{a.points_possible}" if a.points_possible else "N/A"
                data.append([a.name, a.category or '-', score, percentage])

            # Add class grade
            grade_percent = calculate_class_grade(class_obj.id)
            letter_grade = percentage_to_grade(grade_percent)
            data.append(['', '', '<b>Class Grade:</b>', f'<b>{grade_percent:.1f}% ({letter_grade})</b>'])

            table = Table(data, colWidths=[2.5*inch, 1.5*inch, 1*inch, 1.2*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, -1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -2), 1, colors.black),
                ('LINEABOVE', (0, -1), (-1, -1), 2, colors.black),
            ]))
            elements.append(table)
        else:
            elements.append(Paragraph("No assignments recorded", styles['Normal']))

        elements.append(Spacer(1, 0.3*inch))

    # Build PDF
    doc.build(elements)
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'grade_report_{term.name.replace(" ", "_")}.pdf'
    )

def calculate_class_grade(class_id):
    assignments = Assignment.query.filter_by(class_id=class_id).all()
    if not assignments:
        return 0.0

    total_weighted_points = 0
    total_weighted_possible = 0

    for a in assignments:
        if a.points_possible and a.points_earned is not None:
            total_weighted_points += a.points_earned * a.weight
            total_weighted_possible += a.points_possible * a.weight

    if total_weighted_possible == 0:
        return 0.0

    return (total_weighted_points / total_weighted_possible) * 100


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
