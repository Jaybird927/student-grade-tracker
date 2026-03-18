// Tab switching
function showTab(tabName) {
    const tabs = document.querySelectorAll('.tab-content');
    const buttons = document.querySelectorAll('.tab-button');

    tabs.forEach(tab => tab.classList.remove('active'));
    buttons.forEach(btn => btn.classList.remove('active'));

    document.getElementById(`${tabName}-tab`).classList.add('active');
    event.target.classList.add('active');

    if (tabName === 'terms') loadTerms();
    if (tabName === 'classes') {
        loadClasses();
        populateTermSelect('class-term');
        populateTermSelect('class-filter-term');
    }
    if (tabName === 'assignments') {
        loadAssignments();
        populateClassSelect('assignment-class');
        populateClassSelect('assignment-filter-class');
    }
}

// Helper function to get grade class
function getGradeClass(letterGrade) {
    if (letterGrade.startsWith('A')) return 'grade-a';
    if (letterGrade.startsWith('B')) return 'grade-b';
    if (letterGrade.startsWith('C')) return 'grade-c';
    if (letterGrade.startsWith('D')) return 'grade-d';
    return 'grade-f';
}

// Terms
function showAddTermForm() {
    document.getElementById('add-term-form').style.display = 'block';
}

function hideAddTermForm() {
    document.getElementById('add-term-form').style.display = 'none';
    document.getElementById('term-name').value = '';
    document.getElementById('term-start').value = '';
    document.getElementById('term-end').value = '';
}

async function loadTerms() {
    const response = await fetch('/api/terms');
    const terms = await response.json();

    const list = document.getElementById('terms-list');
    list.innerHTML = '';

    for (const term of terms) {
        const card = document.createElement('div');
        card.className = 'card';

        const dateStr = term.start_date && term.end_date
            ? `${new Date(term.start_date).toLocaleDateString()} - ${new Date(term.end_date).toLocaleDateString()}`
            : 'No dates set';

        card.innerHTML = `
            <div class="card-header">
                <div>
                    <span class="card-title">${term.name}</span>
                    <span class="badge badge-${term.type}">${term.type}</span>
                </div>
                <div class="card-actions">
                    <button class="btn btn-success" onclick="downloadReport(${term.id}, '${term.name}')">Download Report</button>
                    <button class="btn btn-danger" onclick="deleteTerm(${term.id})">Delete</button>
                </div>
            </div>
            <div class="card-body">
                <p>${dateStr}</p>
            </div>
        `;
        list.appendChild(card);
    }
}

async function addTerm(event) {
    event.preventDefault();

    const data = {
        name: document.getElementById('term-name').value,
        type: document.getElementById('term-type').value,
        start_date: document.getElementById('term-start').value || null,
        end_date: document.getElementById('term-end').value || null
    };

    await fetch('/api/terms', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });

    hideAddTermForm();
    loadTerms();
}

async function deleteTerm(termId) {
    if (!confirm('Are you sure? This will delete all classes and assignments in this term.')) return;

    await fetch(`/api/terms/${termId}`, { method: 'DELETE' });
    loadTerms();
}

async function downloadReport(termId, termName) {
    window.location.href = `/api/report/${termId}`;
}

// Classes
function showAddClassForm() {
    document.getElementById('add-class-form').style.display = 'block';
    populateTermSelect('class-term');
}

function hideAddClassForm() {
    document.getElementById('add-class-form').style.display = 'none';
    document.getElementById('class-name').value = '';
    document.getElementById('class-credits').value = '1.0';
}

async function populateTermSelect(selectId) {
    const response = await fetch('/api/terms');
    const terms = await response.json();

    const select = document.getElementById(selectId);
    const currentValue = select.value;
    select.innerHTML = selectId.includes('filter') ? '<option value="">All Terms</option>' : '';

    terms.forEach(term => {
        const option = document.createElement('option');
        option.value = term.id;
        option.textContent = `${term.name} (${term.type})`;
        select.appendChild(option);
    });

    if (currentValue) select.value = currentValue;
}

async function loadClasses() {
    const termFilter = document.getElementById('class-filter-term')?.value || '';
    const url = termFilter ? `/api/classes?term_id=${termFilter}` : '/api/classes';

    const response = await fetch(url);
    const classes = await response.json();

    const list = document.getElementById('classes-list');
    list.innerHTML = '';

    if (classes.length === 0) {
        list.innerHTML = '<p style="text-align: center; color: #999;">No classes found. Add a class to get started!</p>';
        return;
    }

    for (const cls of classes) {
        const card = document.createElement('div');
        card.className = 'card';

        card.innerHTML = `
            <div class="card-header">
                <div>
                    <span class="card-title">${cls.name}</span>
                    <span class="grade-display ${getGradeClass(cls.letter_grade)}">
                        ${cls.grade.toFixed(1)}% (${cls.letter_grade})
                    </span>
                </div>
                <div class="card-actions">
                    <button class="btn btn-danger" onclick="deleteClass(${cls.id})">Delete</button>
                </div>
            </div>
            <div class="card-body">
                <p><strong>Credits:</strong> ${cls.credits}</p>
            </div>
        `;
        list.appendChild(card);
    }
}

async function addClass(event) {
    event.preventDefault();

    const data = {
        name: document.getElementById('class-name').value,
        term_id: parseInt(document.getElementById('class-term').value),
        credits: parseFloat(document.getElementById('class-credits').value)
    };

    await fetch('/api/classes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });

    hideAddClassForm();
    loadClasses();
}

async function deleteClass(classId) {
    if (!confirm('Are you sure? This will delete all assignments for this class.')) return;

    await fetch(`/api/classes/${classId}`, { method: 'DELETE' });
    loadClasses();
}

// Assignments
function showAddAssignmentForm() {
    document.getElementById('add-assignment-form').style.display = 'block';
    populateClassSelect('assignment-class');
}

function hideAddAssignmentForm() {
    document.getElementById('add-assignment-form').style.display = 'none';
    document.querySelector('#add-assignment-form form').reset();
    document.getElementById('assignment-weight').value = '1.0';
}

async function populateClassSelect(selectId) {
    const response = await fetch('/api/classes');
    const classes = await response.json();

    const select = document.getElementById(selectId);
    const currentValue = select.value;
    select.innerHTML = selectId.includes('filter') ? '<option value="">All Classes</option>' : '';

    classes.forEach(cls => {
        const option = document.createElement('option');
        option.value = cls.id;
        option.textContent = cls.name;
        select.appendChild(option);
    });

    if (currentValue) select.value = currentValue;
}

async function loadAssignments() {
    const classFilter = document.getElementById('assignment-filter-class')?.value || '';
    const url = classFilter ? `/api/assignments?class_id=${classFilter}` : '/api/assignments';

    const response = await fetch(url);
    const assignments = await response.json();

    const list = document.getElementById('assignments-list');
    list.innerHTML = '';

    if (assignments.length === 0) {
        list.innerHTML = '<p style="text-align: center; color: #999;">No assignments found. Add an assignment to get started!</p>';
        return;
    }

    // Get class names
    const classResponse = await fetch('/api/classes');
    const classes = await classResponse.json();
    const classMap = {};
    classes.forEach(c => classMap[c.id] = c.name);

    // Create table
    const table = document.createElement('table');
    table.className = 'table';
    table.innerHTML = `
        <thead>
            <tr>
                <th>Assignment</th>
                <th>Class</th>
                <th>Category</th>
                <th>Score</th>
                <th>Weight</th>
                <th>Percentage</th>
                <th>Date</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody id="assignments-tbody"></tbody>
    `;

    const tbody = table.querySelector('#assignments-tbody');
    assignments.forEach(assignment => {
        const row = document.createElement('tr');
        const percentage = assignment.percentage ? `${assignment.percentage.toFixed(1)}%` : 'N/A';
        const score = assignment.points_possible ? `${assignment.points_earned}/${assignment.points_possible}` : 'N/A';
        const date = assignment.date ? new Date(assignment.date).toLocaleDateString() : 'N/A';

        row.innerHTML = `
            <td>${assignment.name}</td>
            <td>${classMap[assignment.class_id] || 'Unknown'}</td>
            <td>${assignment.category || '-'}</td>
            <td>${score}</td>
            <td>${assignment.weight}x</td>
            <td>${percentage}</td>
            <td>${date}</td>
            <td>
                <button class="btn btn-danger" onclick="deleteAssignment(${assignment.id})">Delete</button>
            </td>
        `;
        tbody.appendChild(row);
    });

    list.appendChild(table);
}

async function addAssignment(event) {
    event.preventDefault();

    const data = {
        name: document.getElementById('assignment-name').value,
        class_id: parseInt(document.getElementById('assignment-class').value),
        category: document.getElementById('assignment-category').value || null,
        points_earned: parseFloat(document.getElementById('assignment-earned').value),
        points_possible: parseFloat(document.getElementById('assignment-possible').value),
        weight: parseFloat(document.getElementById('assignment-weight').value),
        date: document.getElementById('assignment-date').value || null
    };

    await fetch('/api/assignments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });

    hideAddAssignmentForm();
    loadAssignments();
}

async function deleteAssignment(assignmentId) {
    if (!confirm('Are you sure you want to delete this assignment?')) return;

    await fetch(`/api/assignments/${assignmentId}`, { method: 'DELETE' });
    loadAssignments();
}

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    // Load current user
    try {
        const response = await fetch('/api/current-user');
        if (response.ok) {
            const data = await response.json();
            document.getElementById('username-display').textContent = `Welcome, ${data.username}`;
        } else {
            window.location.href = '/login';
        }
    } catch (error) {
        window.location.href = '/login';
    }

    loadTerms();
});
