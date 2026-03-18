# Student Grade Tracker

A web-based student grade tracker that supports multiple quarters/trimesters, classes, and assignments with automatic grade calculation and PDF report generation.

## Features

- **Multiple Terms**: Support for quarters, trimesters, and semesters
- **Class Management**: Track multiple classes per term with credit hours
- **Assignment Tracking**: Record assignments with categories, weights, and scores
- **Automatic Grading**: Uses custom grading scale (A+ through F)
- **PDF Reports**: Export detailed grade reports for any term

## Grading Scale

- A+ (98-100%)
- A (93-96%)
- A- (90-92%)
- B+ (88-89%)
- B (83-87%)
- B- (80-82%)
- C+ (78-79%)
- C (73-77%)
- C- (70-72%)
- D+ (68-69%)
- D (63-67%)
- D- (60-62%)
- F (<60%)

## Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python app.py
```

3. Open your browser to `http://localhost:5000`

## Deploying to Railway

1. Create a new project on [Railway](https://railway.app)
2. Connect your GitHub repository or deploy directly
3. Railway will automatically detect the Python application and deploy it
4. The app uses SQLite database which persists on Railway's volume storage

## Usage

### Adding a Term
1. Go to the "Terms" tab
2. Click "+ Add Term"
3. Enter the term name, type (quarter/trimester/semester), and optional dates
4. Click "Add Term"

### Adding a Class
1. Go to the "Classes" tab
2. Click "+ Add Class"
3. Select the term, enter class name and credits
4. Click "Add Class"

### Adding Assignments
1. Go to the "Assignments" tab
2. Click "+ Add Assignment"
3. Fill in assignment details:
   - Name, class, category
   - Points earned and possible
   - Weight (1.0 = normal weight, 2.0 = double weight, etc.)
   - Date (optional)
4. Click "Add Assignment"

### Generating Reports
1. Go to the "Terms" tab
2. Click "Download Report" on any term
3. A PDF will be generated with all classes, assignments, and grades

## Technology Stack

- **Backend**: Python Flask
- **Database**: SQLite with SQLAlchemy ORM
- **Frontend**: Vanilla JavaScript, HTML5, CSS3
- **PDF Generation**: ReportLab
- **Deployment**: Railway (with Gunicorn)
