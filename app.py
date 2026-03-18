from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from reportlab.lib.pagesizes import letter
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from functools import wraps
import io
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///grades.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['PERMANENT_SESSION_LIFETIME'] = 86400 * 30  # 30 days
db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    terms = db.relationship('Term', backref='user', cascade='all, delete-orphan', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Term(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'quarter' or 'trimester'
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    classes = db.relationship('Class', backref='term', cascade='all, delete-orphan', lazy=True)

class Class(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    term_id = db.Column(db.Integer, db.ForeignKey('term.id'), nullable=False)
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

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

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
    if 'user_id' in session:
        return render_template('index.html')
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.json
        username = data.get('username')
        password = data.get('password')

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session.permanent = True
            session['user_id'] = user.id
            session['username'] = user.username
            return jsonify({'success': True, 'username': user.username})
        return jsonify({'error': 'Invalid username or password'}), 401

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.json
        username = data.get('username')
        password = data.get('password')

        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username already exists'}), 400

        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        session.permanent = True
        session['user_id'] = user.id
        session['username'] = user.username
        return jsonify({'success': True, 'username': user.username})

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/current-user')
def current_user():
    if 'user_id' in session:
        return jsonify({'username': session.get('username')})
    return jsonify({'error': 'Not logged in'}), 401

@app.route('/api/terms', methods=['GET', 'POST'])
@login_required
def handle_terms():
    if request.method == 'GET':
        terms = Term.query.filter_by(user_id=session['user_id']).all()
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
            end_date=datetime.fromisoformat(data['end_date']).date() if data.get('end_date') else None,
            user_id=session['user_id']
        )
        db.session.add(term)
        db.session.commit()
        return jsonify({'id': term.id, 'name': term.name}), 201

@app.route('/api/terms/<int:term_id>', methods=['DELETE'])
@login_required
def delete_term(term_id):
    term = Term.query.filter_by(id=term_id, user_id=session['user_id']).first_or_404()
    db.session.delete(term)
    db.session.commit()
    return '', 204

@app.route('/api/classes', methods=['GET', 'POST'])
@login_required
def handle_classes():
    if request.method == 'GET':
        term_id = request.args.get('term_id')
        user_terms = [t.id for t in Term.query.filter_by(user_id=session['user_id']).all()]

        if term_id:
            if int(term_id) not in user_terms:
                return jsonify([])
            classes = Class.query.filter_by(term_id=term_id).all()
        else:
            classes = Class.query.join(Term).filter(Term.user_id == session['user_id']).all()

        result = []
        for c in classes:
            grade_percent = calculate_class_grade(c.id)
            letter_grade = percentage_to_grade(grade_percent)
            result.append({
                'id': c.id,
                'name': c.name,
                'term_id': c.term_id,
                'grade': grade_percent,
                'letter_grade': letter_grade
            })

        return jsonify(result)

    elif request.method == 'POST':
        data = request.json
        class_obj = Class(
            name=data['name'],
            term_id=data['term_id']
        )
        db.session.add(class_obj)
        db.session.commit()
        return jsonify({'id': class_obj.id, 'name': class_obj.name}), 201

@app.route('/api/classes/<int:class_id>', methods=['DELETE'])
@login_required
def delete_class(class_id):
    class_obj = Class.query.join(Term).filter(
        Class.id == class_id,
        Term.user_id == session['user_id']
    ).first_or_404()
    db.session.delete(class_obj)
    db.session.commit()
    return '', 204

@app.route('/api/assignments', methods=['GET', 'POST'])
@login_required
def handle_assignments():
    if request.method == 'GET':
        class_id = request.args.get('class_id')
        user_classes = [c.id for c in Class.query.join(Term).filter(Term.user_id == session['user_id']).all()]

        if class_id:
            if int(class_id) not in user_classes:
                return jsonify([])
            assignments = Assignment.query.filter_by(class_id=class_id).all()
        else:
            assignments = Assignment.query.join(Class).join(Term).filter(Term.user_id == session['user_id']).all()

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

@app.route('/api/assignments/bulk', methods=['POST'])
@login_required
def bulk_add_assignments():
    data = request.json
    assignments_data = data.get('assignments', [])

    # Verify all classes belong to the user
    user_classes = [c.id for c in Class.query.join(Term).filter(Term.user_id == session['user_id']).all()]

    created_assignments = []
    for assign_data in assignments_data:
        class_id = assign_data.get('class_id')

        # Security check
        if class_id not in user_classes:
            return jsonify({'error': 'Unauthorized access to class'}), 403

        assignment = Assignment(
            name=assign_data['name'],
            class_id=class_id,
            category=assign_data.get('category'),
            weight=assign_data.get('weight', 1.0),
            points_earned=assign_data.get('points_earned'),
            points_possible=assign_data.get('points_possible'),
            date=datetime.fromisoformat(assign_data['date']).date() if assign_data.get('date') else None
        )
        db.session.add(assignment)
        created_assignments.append(assignment)

    db.session.commit()
    return jsonify({
        'success': True,
        'count': len(created_assignments),
        'message': f'Successfully added {len(created_assignments)} assignments'
    }), 201

@app.route('/api/assignments/<int:assignment_id>', methods=['PUT', 'DELETE'])
@login_required
def handle_assignment(assignment_id):
    assignment = Assignment.query.join(Class).join(Term).filter(
        Assignment.id == assignment_id,
        Term.user_id == session['user_id']
    ).first_or_404()

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
@login_required
def generate_report(term_id):
    term = Term.query.filter_by(id=term_id, user_id=session['user_id']).first_or_404()

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
        class_header = Paragraph(f"<b>{class_obj.name}</b>", styles['Heading2'])
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

@app.route('/api/email-report', methods=['POST'])
@login_required
def email_report():
    TEACHER_PASSWORD = 'onecreativeapp'

    data = request.json
    term_id = data.get('term_id')
    parent_email = data.get('parent_email')
    teacher_password = data.get('teacher_password')

    # Verify teacher password
    if teacher_password != TEACHER_PASSWORD:
        return jsonify({'error': 'Invalid teacher password'}), 403

    # Verify user owns this term
    term = Term.query.filter_by(id=term_id, user_id=session['user_id']).first()
    if not term:
        return jsonify({'error': 'Term not found'}), 404

    # Generate PDF report
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
        class_header = Paragraph(f"<b>{class_obj.name}</b>", styles['Heading2'])
        elements.append(class_header)
        elements.append(Spacer(1, 0.1*inch))

        assignments = Assignment.query.filter_by(class_id=class_obj.id).all()

        if assignments:
            table_data = [['Assignment', 'Category', 'Score', 'Percentage']]
            for a in assignments:
                percentage = f"{(a.points_earned / a.points_possible * 100):.1f}%" if a.points_possible else "N/A"
                score = f"{a.points_earned}/{a.points_possible}" if a.points_possible else "N/A"
                table_data.append([a.name, a.category or '-', score, percentage])

            grade_percent = calculate_class_grade(class_obj.id)
            letter_grade = percentage_to_grade(grade_percent)
            table_data.append(['', '', '<b>Class Grade:</b>', f'<b>{grade_percent:.1f}% ({letter_grade})</b>'])

            table = Table(table_data, colWidths=[2.5*inch, 1.5*inch, 1*inch, 1.2*inch])
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

    doc.build(elements)
    buffer.seek(0)

    # Send email
    try:
        # Get email configuration from environment variables
        smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.environ.get('SMTP_PORT', 587))
        sender_email = os.environ.get('SENDER_EMAIL')
        sender_password = os.environ.get('SENDER_PASSWORD')

        if not sender_email or not sender_password:
            return jsonify({'error': 'Email not configured. Please set SENDER_EMAIL and SENDER_PASSWORD environment variables.'}), 500

        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = parent_email
        msg['Subject'] = f'Grade Report - {term.name}'

        body = f"""
Dear Parent/Guardian,

Please find attached the grade report for {term.name}.

This report contains detailed information about all classes and assignments for this term.

Best regards,
{session.get('username')}
        """

        msg.attach(MIMEText(body, 'plain'))

        # Attach PDF
        attachment = MIMEBase('application', 'pdf')
        attachment.set_payload(buffer.read())
        encoders.encode_base64(attachment)
        attachment.add_header('Content-Disposition', f'attachment; filename=grade_report_{term.name.replace(" ", "_")}.pdf')
        msg.attach(attachment)

        # Send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()

        return jsonify({'success': True, 'message': f'Report sent to {parent_email}'}), 200

    except Exception as e:
        return jsonify({'error': f'Failed to send email: {str(e)}'}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
