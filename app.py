# career_advisor_app/app.py
from flask import Flask, render_template, request, jsonify, send_from_directory
import json
import os
import pdfplumber
import re
from collections import defaultdict
import plotly
import plotly.express as px
from wordcloud import WordCloud
import numpy as np
from io import BytesIO
import base64
import logging
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DATA_FOLDER'] = 'data'

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DATA_FOLDER'], exist_ok=True)

# Global variable to store career data
career_data = None

# Load career data with error handling
def load_career_data():
    global career_data
    try:
        data_file_path = os.path.join(app.config['DATA_FOLDER'], 'career_data.json')
        
        # Check if file exists
        if not os.path.exists(data_file_path):
            logger.error(f"Career data file not found at: {data_file_path}")
            return create_default_career_data()
        
        # Check if file is readable
        if not os.access(data_file_path, os.R_OK):
            logger.error(f"Career data file is not readable: {data_file_path}")
            return create_default_career_data()
        
        # Load and validate JSON
        with open(data_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Validate data structure
        if not isinstance(data, dict) or 'career_roles' not in data:
            logger.error("Invalid career data structure - missing 'career_roles' key")
            return create_default_career_data()
        
        if not isinstance(data['career_roles'], list):
            logger.error("Invalid career data structure - 'career_roles' should be a list")
            return create_default_career_data()
        
        if len(data['career_roles']) == 0:
            logger.warning("Career data contains no roles")
            return create_default_career_data()
        
        # Validate each role has required fields
        required_fields = ['role', 'category', 'required_skills', 'preferred_skills', 
                          'average_salary', 'growth_trend', 'recommended_courses']
        
        valid_roles = []
        for i, role in enumerate(data['career_roles']):
            if not isinstance(role, dict):
                logger.warning(f"Role at index {i} is not a dictionary, skipping")
                continue
                
            missing_fields = [field for field in required_fields if field not in role]
            if missing_fields:
                logger.warning(f"Role '{role.get('role', f'index_{i}')}' missing fields: {missing_fields}, skipping")
                continue
            
            valid_roles.append(role)
        
        if not valid_roles:
            logger.error("No valid roles found in career data")
            return create_default_career_data()
        
        data['career_roles'] = valid_roles
        logger.info(f"Successfully loaded {len(valid_roles)} career roles")
        return data
        
    except Exception as e:
        logger.error(f"Unexpected error loading career data: {e}")
        return create_default_career_data()


def create_default_career_data():
    """Create default career data if the main file is missing or invalid"""
    logger.info("Creating default career data")
    return {
        "career_roles": [
            {
                "role": "Software Engineer",
                "category": "Technology",
                "required_skills": ["Python", "JavaScript", "Git", "SQL"],
                "preferred_skills": ["React", "Node.js", "Docker", "AWS"],
                "average_salary": {
                    "entry": 75000,
                    "mid": 110000,
                    "senior": 150000,
                    "lead": 200000
                },
                "growth_trend": {
                    "years": [2020, 2021, 2022, 2023, 2024],
                    "demand_index": [85, 90, 95, 100, 105]
                },
                "recommended_courses": [
                    {
                        "title": "Complete Python Bootcamp",
                        "platform": "Udemy",
                        "duration": "40 hours",
                        "rating": 4.6
                    }
                ],
                "job_outlook": "Excellent",
                "remote_friendly": True,
                "experience_level": "Entry to Senior",
                "top_companies": ["Google", "Microsoft", "Amazon"],
                "career_paths": ["Senior Engineer", "Tech Lead", "Engineering Manager"]
            },
            {
                "role": "Data Scientist",
                "category": "Data & Analytics",
                "required_skills": ["Python", "Statistics", "Machine Learning", "SQL"],
                "preferred_skills": ["R", "TensorFlow", "Tableau", "AWS"],
                "average_salary": {
                    "entry": 80000,
                    "mid": 120000,
                    "senior": 160000,
                    "lead": 220000
                },
                "growth_trend": {
                    "years": [2020, 2021, 2022, 2023, 2024],
                    "demand_index": [80, 85, 92, 98, 103]
                },
                "recommended_courses": [
                    {
                        "title": "Data Science Specialization",
                        "platform": "Coursera",
                        "duration": "60 hours",
                        "rating": 4.5
                    }
                ],
                "job_outlook": "Very Good",
                "remote_friendly": True,
                "experience_level": "Entry to Senior",
                "top_companies": ["Netflix", "Airbnb", "Uber"],
                "career_paths": ["Senior Data Scientist", "ML Engineer", "Data Science Manager"]
            }
        ]
    }

def get_career_data():
    """Get career data, loading it if not already loaded"""
    global career_data
    if career_data is None:
        career_data = load_career_data()
    return career_data

def reload_career_data():
    """Force reload of career data"""
    global career_data
    career_data = None
    return get_career_data()

@app.route('/api/reload_data', methods=['POST'])
def reload_data():
    """API endpoint to reload career data"""
    try:
        data = reload_career_data()
        return jsonify({
            'success': True,
            'message': f'Career data reloaded successfully. Found {len(data["career_roles"])} roles.',
            'roles_count': len(data["career_roles"])
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/data_status')
def data_status():
    """API endpoint to check data status"""
    try:
        data = get_career_data()
        data_file_path = os.path.join(app.config['DATA_FOLDER'], 'career_data.json')
        
        return jsonify({
            'file_exists': os.path.exists(data_file_path),
            'file_path': data_file_path,
            'roles_count': len(data['career_roles']),
            'categories': list(set(role['category'] for role in data['career_roles'])),
            'roles': [role['role'] for role in data['career_roles']]
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'file_path': os.path.join(app.config['DATA_FOLDER'], 'career_data.json')
        }), 500

@app.route('/')
def dashboard():
    try:
        # Ensure data is loaded
        data = get_career_data()
        return render_template('dashboard.html')
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        return render_template('error.html', error="Failed to load career data"), 500

@app.route('/trending_skills')
def trending_skills():
    try:
        data = get_career_data()
        
        # Aggregate skills demand
        skill_demand = defaultdict(int)
        for role in data['career_roles']:
            growth_trend = role.get('growth_trend', {})
            demand_index = growth_trend.get('demand_index', [100])
            current_demand = demand_index[-1] if demand_index else 100
            
            for skill in role.get('required_skills', []) + role.get('preferred_skills', []):
                skill_demand[skill] += current_demand
        
        if not skill_demand:
            return jsonify({'error': 'No skills data available'}), 404
        
        # Prepare data for charts
        sorted_skills = sorted(skill_demand.items(), key=lambda x: x[1], reverse=True)[:20]
        skills, demand = zip(*sorted_skills) if sorted_skills else ([], [])
        
        # Create bar chart
        if skills and demand:
            bar_fig = px.bar(
                x=skills, 
                y=demand,
                title='Top 20 In-Demand Skills',
                labels={'x': 'Skill', 'y': 'Demand Index'},
                color=demand,
                color_continuous_scale='Bluered'
            )
            bar_fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            
            # Create word cloud
            wordcloud = WordCloud(width=800, height=400, background_color='white').generate_from_frequencies(skill_demand)
            img_buffer = BytesIO()
            wordcloud.to_image().save(img_buffer, format='PNG')
            wordcloud_b64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
        else:
            bar_fig = px.bar(title='No Skills Data Available')
            wordcloud_b64 = None
        
        # Create salary distribution chart
        salaries = []
        categories = []
        for role in data['career_roles']:
            salary_data = role.get('average_salary', {})
            role_name = role.get('role', 'Unknown')
            
            for level in ['entry', 'mid', 'senior', 'lead']:
                if level in salary_data:
                    salaries.append(salary_data[level])
                    categories.append(f"{role_name} - {level.title()}")
        
        if salaries:
            salary_fig = px.box(
                x=salaries,
                title='Salary Distribution Across Levels',
                labels={'x': 'Annual Salary (USD)'}
            )
            salary_fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        else:
            salary_fig = px.box(title='No Salary Data Available')
        
        return jsonify({
            'bar_chart': json.loads(plotly.io.to_json(bar_fig)),
            'word_cloud': wordcloud_b64,
            'salary_distribution': json.loads(plotly.io.to_json(salary_fig))
        })
        
    except Exception as e:
        logger.error(f"Error in trending_skills: {e}")
        return jsonify({'error': 'Failed to generate trending skills data'}), 500

@app.route('/job_roles')
def job_roles():
    try:
        data = get_career_data()
        
        return jsonify({
            'categories': list(set(role.get('category', 'Unknown') for role in data['career_roles'])),
            'roles': [{
                'role': role.get('role', 'Unknown'),
                'category': role.get('category', 'Unknown'),
                'skills': {
                    'required': role.get('required_skills', []),
                    'preferred': role.get('preferred_skills', [])
                },
                'courses': role.get('recommended_courses', [])
            } for role in data['career_roles']]
        })
        
    except Exception as e:
        logger.error(f"Error in job_roles: {e}")
        return jsonify({'error': 'Failed to load job roles data'}), 500

@app.route('/job_insights')
def job_insights():
    try:
        data = get_career_data()
        insights = []
        
        for role in data['career_roles']:
            growth = role.get('growth_trend', {})
            years = growth.get('years', [2020, 2021, 2022, 2023, 2024])
            demand_index = growth.get('demand_index', [100, 100, 100, 100, 100])
            
            fig = px.line(
                x=years,
                y=demand_index,
                title=f'{role.get("role", "Unknown")} Demand Trend',
                labels={'x': 'Year', 'y': 'Demand Index'}
            )
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            
            insights.append({
                'role': role.get('role', 'Unknown'),
                'category': role.get('category', 'Unknown'),
                'salary': role.get('average_salary', {}),
                'companies': role.get('top_companies', []),
                'growth_chart': json.loads(plotly.io.to_json(fig)),
                'outlook': role.get('job_outlook', 'Unknown'),
                'remote': role.get('remote_friendly', False)
            })
        
        return jsonify(insights)
        
    except Exception as e:
        logger.error(f"Error in job_insights: {e}")
        return jsonify({'error': 'Failed to generate job insights'}), 500

@app.route('/upload_resume', methods=['POST'])
def upload_resume():
    try:
        if 'resume' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['resume']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        # Get target role - now REQUIRED
        target_role = request.form.get('target_role', '').strip()
        if not target_role:
            return jsonify({'error': 'Target role must be selected before analysis'}), 400
        
        if file and file.filename.endswith('.pdf'):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            
            # Parse PDF
            text = ""
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
            
            # Extract skills
            resume_skills = extract_skills(text)
            
            # Analyze resume with required target role
            return analyze_resume(resume_skills, target_role)
        
        return jsonify({'error': 'Invalid file format'}), 400
        
    except Exception as e:
        logger.error(f"Error in upload_resume: {e}")
        return jsonify({'error': 'Failed to process resume'}), 500

def extract_skills(text):
    """Extract skills from resume text"""
    try:
        data = get_career_data()
        
        # Simple skill extraction - real implementation would use NLP
        all_skills = set()
        for role in data['career_roles']:
            all_skills.update(role.get('required_skills', []))
            all_skills.update(role.get('preferred_skills', []))
        
        found_skills = set()
        for skill in all_skills:
            if re.search(r'\b' + re.escape(skill) + r'\b', text, re.IGNORECASE):
                found_skills.add(skill)
        
        return list(found_skills)
        
    except Exception as e:
        logger.error(f"Error extracting skills: {e}")
        return []

def analyze_resume(resume_skills, target_role):
    """Analyze resume against target role"""
    try:
        data = get_career_data()
        
        # Find matching role - target_role is now required
        role_data = None
        for role in data['career_roles']:
            if role.get('role', '').lower() == target_role.lower():
                role_data = role
                break
        
        # If target role not found, return available roles
        if not role_data:
            available_roles = [role.get('role', 'Unknown') for role in data['career_roles']]
            return jsonify({
                'error': f'Target role "{target_role}" not found.',
                'available_roles': available_roles,
                'suggestion': 'Please select a role from the available options.'
            }), 404
        
        # Compare skills
        required_skills = role_data.get('required_skills', [])
        preferred_skills = role_data.get('preferred_skills', [])
        
        missing_required = [s for s in required_skills if s not in resume_skills]
        missing_preferred = [s for s in preferred_skills if s not in resume_skills]
        matched_skills = [s for s in required_skills + preferred_skills if s in resume_skills]
        
        # Calculate match percentage
        total_skills = len(required_skills) + len(preferred_skills)
        match_percentage = int((len(matched_skills) / total_skills) * 100) if total_skills else 0
        
        # Generate improvement plan
        improvement_plan = []
        for skill in missing_required[:3]:
            improvement_plan.append({
                'skill': skill,
                'priority': 'High',
                'resources': find_courses(skill)
            })
        
        for skill in missing_preferred[:2]:
            improvement_plan.append({
                'skill': skill,
                'priority': 'Medium',
                'resources': find_courses(skill)
            })
        
        return jsonify({
            'role': role_data.get('role', 'Unknown'),
            'match_percentage': match_percentage,
            'matched_skills': matched_skills,
            'missing_required': missing_required,
            'missing_preferred': missing_preferred,
            'improvement_plan': improvement_plan,
            'salary_range': role_data.get('average_salary', {}),
            'career_paths': role_data.get('career_paths', [])
        })
        
    except Exception as e:
        logger.error(f"Error analyzing resume: {e}")
        return jsonify({'error': 'Failed to analyze resume'}), 500

def find_courses(skill):
    """Find courses for a specific skill"""
    try:
        data = get_career_data()
        courses = []
        
        for role in data['career_roles']:
            for course in role.get('recommended_courses', []):
                if skill.lower() in course.get('title', '').lower():
                    courses.append(course)
        
        return courses[:3]  # Return top 3 courses
        
    except Exception as e:
        logger.error(f"Error finding courses for skill {skill}: {e}")
        return []

@app.route('/career_path', methods=['POST'])
def career_path():
    try:
        data = get_career_data()
        request_data = request.json or {}
        resume_skills = request_data.get('skills', [])
        experience_level = request_data.get('experience', 'Entry')
        
        # Find suitable career paths
        recommended_roles = []
        for role in data['career_roles']:
            required = set(role.get('required_skills', []))
            preferred = set(role.get('preferred_skills', []))
            matched = required.intersection(resume_skills)
            
            # Experience level filter
            role_levels = role.get('experience_level', 'Entry to Senior').split(' to ')
            min_level = role_levels[0]
            max_level = role_levels[-1] if len(role_levels) > 1 else min_level
            
            level_order = ['Entry', 'Mid', 'Senior', 'Lead']
            try:
                if (level_order.index(experience_level) < level_order.index(min_level) or 
                    level_order.index(experience_level) > level_order.index(max_level)):
                    continue
            except ValueError:
                # If level not found in order, include the role
                pass
            
            # Calculate match score
            score = len(matched) + 0.5 * len(preferred.intersection(resume_skills))
            if score > 0:
                growth_trend = role.get('growth_trend', {})
                current_growth = growth_trend.get('demand_index', [100])[-1] if growth_trend.get('demand_index') else 100
                
                recommended_roles.append({
                    'role': role.get('role', 'Unknown'),
                    'category': role.get('category', 'Unknown'),
                    'match_score': score,
                    'salary': role.get('average_salary', {}),
                    'growth': current_growth,
                    'missing_skills': list(required - set(resume_skills)),
                    'recommended_courses': role.get('recommended_courses', [])
                })
        
        # Sort by match score and growth
        recommended_roles.sort(key=lambda x: (x['match_score'], x['growth']), reverse=True)
        
        return jsonify(recommended_roles[:5])
        
    except Exception as e:
        logger.error(f"Error in career_path: {e}")
        return jsonify({'error': 'Failed to generate career path recommendations'}), 500

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = get_career_data()
        request_data = request.json or {}
        message = request_data.get('message', '')
        context = request_data.get('context', {})
        
        # Simple chatbot logic - real implementation would use NLP
        response = "I can help with career advice. Ask about skills, roles, or resume tips."
        
        if 'hello' in message.lower():
            response = "Hello! How can I assist with your career development today?"
        
        elif 'skill' in message.lower() or 'learn' in message.lower():
            role = context.get('current_role', '')
            if role:
                role_data = next((r for r in data['career_roles'] if r.get('role', '').lower() == role.lower()), None)
                if role_data:
                    skills = role_data.get('required_skills', []) + role_data.get('preferred_skills', [])
                    response = f"For {role}, focus on: {', '.join(skills[:5])}..."
                else:
                    response = "I recommend learning Python, SQL, and cloud technologies which are valuable across many roles."
            else:
                response = "I recommend learning Python, SQL, and cloud technologies which are valuable across many roles."
        
        elif 'salary' in message.lower():
            role = extract_role_from_message(message)
            if role:
                role_data = next((r for r in data['career_roles'] if r.get('role', '').lower() == role.lower()), None)
                if role_data:
                    salary = role_data.get('average_salary', {})
                    response = (f"{role} salaries: Entry ${salary.get('entry', 0):,}, "
                                f"Mid ${salary.get('mid', 0):,}, Senior ${salary.get('senior', 0):,}")
                else:
                    response = "Salaries vary by role and experience. Software engineers average $110K at mid-level."
            else:
                response = "Salaries vary by role and experience. Software engineers average $110K at mid-level."
        
        elif 'course' in message.lower() or 'learn' in message.lower():
            skill = extract_skill_from_message(message)
            if skill:
                courses = find_courses(skill)
                if courses:
                    response = f"Top courses for {skill}:\n" + "\n".join(
                        [f"- {c.get('title', 'Unknown')} ({c.get('platform', 'Unknown')})" for c in courses])
                else:
                    response = f"Check Coursera, Udemy, or edX for courses on {skill}."
            else:
                response = "I recommend: Coursera's Machine Learning, Udemy's Web Development Bootcamp, or edX's Data Science courses."
        
        return jsonify({'response': response})
        
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        return jsonify({'response': 'Sorry, I encountered an error. Please try again.'}), 500

def extract_role_from_message(message):
    try:
        data = get_career_data()
        for role in [r.get('role', '') for r in data['career_roles']]:
            if role.lower() in message.lower():
                return role
        return None
    except Exception:
        return None

def extract_skill_from_message(message):
    try:
        data = get_career_data()
        all_skills = set()
        for role in data['career_roles']:
            all_skills.update(role.get('required_skills', []))
            all_skills.update(role.get('preferred_skills', []))
        
        for skill in all_skills:
            if skill.lower() in message.lower():
                return skill
        return None
    except Exception:
        return None

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Initialize career data on startup
    try:
        career_data = load_career_data()
        logger.info(f"Application started with {len(career_data['career_roles'])} career roles")
    except Exception as e:
        logger.error(f"Failed to initialize career data: {e}")
    
    app.run(debug=True)