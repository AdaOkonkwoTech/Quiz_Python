import json
import os
from datetime import datetime
from pathlib import Path
import bcrypt

JSON_DATA_DIR = "data"
USERS_FILE = os.path.join(JSON_DATA_DIR, "users.json")
QUIZ_SCORES_FILE = os.path.join(JSON_DATA_DIR, "quiz_scores.json")
QUIZ_ATTEMPTED_FILE = os.path.join(JSON_DATA_DIR, "quiz_attempted.json")
IMAGES_FILE = os.path.join(JSON_DATA_DIR, "images.json")
PASSWORD_RESET_FILE = os.path.join(JSON_DATA_DIR, "password_reset_tokens.json")


def ensure_data_directory():
    """Ensure the data directory exists"""
    Path(JSON_DATA_DIR).mkdir(exist_ok=True)


def ensure_json_files():
    """Ensure all JSON files exist with initial structure"""
    ensure_data_directory()
    
    files = {
        USERS_FILE: {"users": [], "next_id": 1},
        QUIZ_SCORES_FILE: {"scores": [], "next_id": 1},
        QUIZ_ATTEMPTED_FILE: {"attempts": [], "next_id": 1},
        IMAGES_FILE: {"images": [], "next_id": 1},
        PASSWORD_RESET_FILE: {"tokens": [], "next_id": 1},
    }
    
    for file_path, default_content in files.items():
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                json.dump(default_content, f, indent=2)


def read_json_file(file_path):
    """Read JSON file safely"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None


def write_json_file(file_path, data):
    """Write JSON file safely"""
    try:
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error writing to {file_path}: {e}")
        return False


# User Management
def add_user(first_name, last_name, username, password, email):
    """Add user to JSON storage"""
    ensure_json_files()
    data = read_json_file(USERS_FILE)
    
    if data is None:
        return None
    
    # Check if username or email exists
    for user in data['users']:
        if user['username'] == username or user['email'] == email:
            return None
    
    user_id = data['next_id']
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    new_user = {
        'id': user_id,
        'first_name': first_name,
        'last_name': last_name,
        'username': username,
        'password': hashed_password,
        'email': email,
        'created_at': datetime.now().isoformat()
    }
    
    data['users'].append(new_user)
    data['next_id'] += 1
    
    if write_json_file(USERS_FILE, data):
        return user_id
    return None


def get_user_by_username(username):
    """Get user by username from JSON storage"""
    ensure_json_files()
    data = read_json_file(USERS_FILE)
    
    if data is None:
        return None
    
    for user in data['users']:
        if user['username'] == username:
            return user
    return None


def get_user_by_id(user_id):
    """Get user by ID from JSON storage"""
    ensure_json_files()
    data = read_json_file(USERS_FILE)
    
    if data is None:
        return None
    
    for user in data['users']:
        if user['id'] == user_id:
            return user
    return None


def update_user(user_id, **kwargs):
    """Update user in JSON storage"""
    ensure_json_files()
    data = read_json_file(USERS_FILE)
    
    if data is None:
        return False
    
    for user in data['users']:
        if user['id'] == user_id:
            user.update(kwargs)
            return write_json_file(USERS_FILE, data)
    return False


def delete_user(user_id):
    """Delete user from JSON storage"""
    ensure_json_files()
    data = read_json_file(USERS_FILE)
    
    if data is None:
        return False
    
    data['users'] = [u for u in data['users'] if u['id'] != user_id]
    return write_json_file(USERS_FILE, data)


# Quiz Scores Management
def add_quiz_score(user_id, score, total_questions):
    """Add quiz score to JSON storage"""
    ensure_json_files()
    data = read_json_file(QUIZ_SCORES_FILE)
    
    if data is None:
        return None
    
    score_id = data['next_id']
    
    new_score = {
        'id': score_id,
        'user_id': user_id,
        'score': score,
        'total_questions': total_questions,
        'quiz_date': datetime.now().isoformat()
    }
    
    data['scores'].append(new_score)
    data['next_id'] += 1
    
    if write_json_file(QUIZ_SCORES_FILE, data):
        return score_id
    return None


def get_quiz_scores_by_user(user_id):
    """Get all quiz scores for a user from JSON storage"""
    ensure_json_files()
    data = read_json_file(QUIZ_SCORES_FILE)
    
    if data is None:
        return []
    
    return [score for score in data['scores'] if score['user_id'] == user_id]


def delete_quiz_scores_by_user(user_id):
    """Delete all quiz scores for a user from JSON storage"""
    ensure_json_files()
    data = read_json_file(QUIZ_SCORES_FILE)
    
    if data is None:
        return False
    
    data['scores'] = [s for s in data['scores'] if s['user_id'] != user_id]
    return write_json_file(QUIZ_SCORES_FILE, data)


# Quiz Attempts Management
def add_quiz_attempt(user_id, quiz_score_id, question, user_answer, correct_answer):
    """Add quiz attempt to JSON storage"""
    ensure_json_files()
    data = read_json_file(QUIZ_ATTEMPTED_FILE)
    
    if data is None:
        return None
    
    attempt_id = data['next_id']
    
    new_attempt = {
        'id': attempt_id,
        'user_id': user_id,
        'quiz_score_id': quiz_score_id,
        'question': question,
        'user_answer': user_answer,
        'correct_answer': correct_answer,
        'quiz_date': datetime.now().isoformat()
    }
    
    data['attempts'].append(new_attempt)
    data['next_id'] += 1
    
    if write_json_file(QUIZ_ATTEMPTED_FILE, data):
        return attempt_id
    return None


def get_quiz_attempts_by_score_id(quiz_score_id, user_id):
    """Get quiz attempts by score ID from JSON storage"""
    ensure_json_files()
    data = read_json_file(QUIZ_ATTEMPTED_FILE)
    
    if data is None:
        return []
    
    return [a for a in data['attempts'] if a['quiz_score_id'] == quiz_score_id and a['user_id'] == user_id]


def get_latest_quiz_attempts_by_user(user_id, limit=20):
    """Get latest quiz attempts for a user from JSON storage"""
    ensure_json_files()
    data = read_json_file(QUIZ_ATTEMPTED_FILE)
    
    if data is None:
        return []
    
    user_attempts = [a for a in data['attempts'] if a['user_id'] == user_id]
    user_attempts.sort(key=lambda x: x['quiz_date'], reverse=True)
    return user_attempts[:limit]


def delete_quiz_attempts_by_user(user_id):
    """Delete all quiz attempts for a user from JSON storage"""
    ensure_json_files()
    data = read_json_file(QUIZ_ATTEMPTED_FILE)
    
    if data is None:
        return False
    
    data['attempts'] = [a for a in data['attempts'] if a['user_id'] != user_id]
    return write_json_file(QUIZ_ATTEMPTED_FILE, data)


# Images Management
def save_user_image(user_id, image_data):
    """Save user profile image to JSON storage (base64 encoded)"""
    ensure_json_files()
    import base64
    data = read_json_file(IMAGES_FILE)
    
    if data is None:
        return False
    
    # Encode image to base64
    encoded_image = base64.b64encode(image_data).decode('utf-8')
    
    # Check if image already exists
    for img in data['images']:
        if img['user_id'] == user_id:
            img['profile_image'] = encoded_image
            return write_json_file(IMAGES_FILE, data)
    
    # Add new image
    image_id = data['next_id']
    new_image = {
        'id': image_id,
        'user_id': user_id,
        'profile_image': encoded_image
    }
    
    data['images'].append(new_image)
    data['next_id'] += 1
    
    return write_json_file(IMAGES_FILE, data)


def get_user_image(user_id):
    """Get user profile image from JSON storage (base64 encoded)"""
    ensure_json_files()
    data = read_json_file(IMAGES_FILE)
    
    if data is None:
        return None
    
    for img in data['images']:
        if img['user_id'] == user_id:
            return img['profile_image']
    return None


def delete_user_image(user_id):
    """Delete user profile image from JSON storage"""
    ensure_json_files()
    data = read_json_file(IMAGES_FILE)
    
    if data is None:
        return False
    
    data['images'] = [img for img in data['images'] if img['user_id'] != user_id]
    return write_json_file(IMAGES_FILE, data)


# Password Reset Tokens Management
def add_password_reset_token(user_id, reset_token, token_expiry):
    """Add password reset token to JSON storage"""
    ensure_json_files()
    data = read_json_file(PASSWORD_RESET_FILE)
    
    if data is None:
        return None
    
    token_id = data['next_id']
    
    new_token = {
        'id': token_id,
        'user_id': user_id,
        'reset_token': reset_token,
        'token_expiry': token_expiry
    }
    
    data['tokens'].append(new_token)
    data['next_id'] += 1
    
    if write_json_file(PASSWORD_RESET_FILE, data):
        return token_id
    return None


def get_password_reset_token(reset_token):
    """Get password reset token from JSON storage"""
    ensure_json_files()
    data = read_json_file(PASSWORD_RESET_FILE)
    
    if data is None:
        return None
    
    for token in data['tokens']:
        if token['reset_token'] == reset_token:
            return token
    return None


def delete_password_reset_tokens_by_user(user_id):
    """Delete all password reset tokens for a user from JSON storage"""
    ensure_json_files()
    data = read_json_file(PASSWORD_RESET_FILE)
    
    if data is None:
        return False
    
    data['tokens'] = [t for t in data['tokens'] if t['user_id'] != user_id]
    return write_json_file(PASSWORD_RESET_FILE, data)


# Initialize on import
ensure_json_files()
