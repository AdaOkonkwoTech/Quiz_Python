import os
import json
import threading
import logging
import base64
from datetime import datetime
from pathlib import Path
import psycopg

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JSONDatabase:
    """JSON file-based database for local caching and fallback"""
    
    def __init__(self, db_path="app_data/db.json"):
        self.db_path = db_path
        self.lock = threading.RLock()
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize_db_file()
    
    def _initialize_db_file(self):
        """Initialize JSON database file with default structure"""
        if not Path(self.db_path).exists():
            default_data = {
                "users": [],
                "quiz_scores": [],
                "quiz_attempted": [],
                "images": [],
                "password_reset_tokens": [],
                "_counters": {
                    "user_id": 0,
                    "quiz_score_id": 0,
                    "quiz_attempted_id": 0,
                    "image_id": 0,
                    "token_id": 0
                }
            }
            with self.lock:
                with open(self.db_path, 'w') as f:
                    json.dump(default_data, f, indent=2)
                logger.info(f"JSON database initialized at {self.db_path}")
    
    def _load_data(self):
        """Load JSON data from file"""
        with self.lock:
            try:
                with open(self.db_path, 'r') as f:
                    return json.load(f)
            except (FileNotFoundError, json.JSONDecodeError) as e:
                logger.error(f"Error loading JSON database: {e}")
                self._initialize_db_file()
                with open(self.db_path, 'r') as f:
                    return json.load(f)
    
    def _save_data(self, data):
        """Save JSON data to file"""
        with self.lock:
            with open(self.db_path, 'w') as f:
                json.dump(data, f, indent=2)
    
    def _get_next_id(self, counter_key):
        """Get next available ID"""
        data = self._load_data()
        data["_counters"][counter_key] += 1
        next_id = data["_counters"][counter_key]
        self._save_data(data)
        return next_id
    
    # User operations
    def create_user(self, first_name, last_name, username, password, email):
        """Create a new user"""
        data = self._load_data()
        user_id = self._get_next_id("user_id")
        
        user = {
            "id": user_id,
            "first_name": first_name,
            "last_name": last_name,
            "username": username,
            "password": password,
            "email": email
        }
        
        data["users"].append(user)
        self._save_data(data)
        return user_id
    
    def get_user_by_username(self, username):
        """Get user by username"""
        data = self._load_data()
        for user in data["users"]:
            if user["username"] == username:
                return (user["id"], user["password"])
        return None
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        data = self._load_data()
        for user in data["users"]:
            if user["id"] == user_id:
                return user
        return None
    
    def username_exists(self, username):
        """Check if username exists"""
        data = self._load_data()
        return any(user["username"] == username for user in data["users"])
    
    def email_exists(self, email):
        """Check if email exists"""
        data = self._load_data()
        return any(user["email"] == email for user in data["users"])
    
    def update_user(self, user_id, **kwargs):
        """Update user fields"""
        data = self._load_data()
        for user in data["users"]:
            if user["id"] == user_id:
                for key, value in kwargs.items():
                    if key in user:
                        user[key] = value
                self._save_data(data)
                return True
        return False
    
    def delete_user(self, user_id):
        """Delete user and related data"""
        data = self._load_data()
        data["users"] = [u for u in data["users"] if u["id"] != user_id]
        data["quiz_scores"] = [qs for qs in data["quiz_scores"] if qs["user_id"] != user_id]
        data["quiz_attempted"] = [qa for qa in data["quiz_attempted"] if qa["user_id"] != user_id]
        data["images"] = [img for img in data["images"] if img["user_id"] != user_id]
        data["password_reset_tokens"] = [pt for pt in data["password_reset_tokens"] if pt["user_id"] != user_id]
        self._save_data(data)
        return True
    
    # Quiz Score operations
    def create_quiz_score(self, user_id, score, total_questions):
        """Create a quiz score entry"""
        data = self._load_data()
        quiz_score_id = self._get_next_id("quiz_score_id")
        
        quiz_score = {
            "id": quiz_score_id,
            "user_id": user_id,
            "score": score,
            "total_questions": total_questions,
            "quiz_date": datetime.now().isoformat()
        }
        
        data["quiz_scores"].append(quiz_score)
        self._save_data(data)
        return quiz_score_id
    
    def get_quiz_scores_by_user(self, user_id):
        """Get all quiz scores for a user"""
        data = self._load_data()
        scores = [qs for qs in data["quiz_scores"] if qs["user_id"] == user_id]
        # Sort by quiz_date descending
        scores.sort(key=lambda x: x["quiz_date"], reverse=True)
        return [(qs["id"], qs["score"], qs["total_questions"], qs["quiz_date"]) for qs in scores]
    
    def delete_quiz_scores_by_user(self, user_id):
        """Delete all quiz scores for a user"""
        data = self._load_data()
        data["quiz_scores"] = [qs for qs in data["quiz_scores"] if qs["user_id"] != user_id]
        self._save_data(data)
        return True
    
    # Quiz Attempted operations
    def create_quiz_attempt(self, user_id, question, user_answer, correct_answer, quiz_score_id):
        """Create a quiz attempt entry"""
        data = self._load_data()
        attempt_id = self._get_next_id("quiz_attempted_id")
        
        attempt = {
            "id": attempt_id,
            "user_id": user_id,
            "quiz_score_id": quiz_score_id,
            "question": question,
            "user_answer": user_answer,
            "correct_answer": correct_answer,
            "quiz_date": datetime.now().isoformat()
        }
        
        data["quiz_attempted"].append(attempt)
        self._save_data(data)
        return attempt_id
    
    def get_quiz_attempts_by_score_id(self, quiz_score_id, user_id):
        """Get all quiz attempts for a specific quiz score"""
        data = self._load_data()
        attempts = [
            qa for qa in data["quiz_attempted"] 
            if qa["quiz_score_id"] == quiz_score_id and qa["user_id"] == user_id
        ]
        return [(qa["question"], qa["user_answer"], qa["correct_answer"]) for qa in attempts]
    
    def get_recent_quiz_attempts(self, user_id, limit=20):
        """Get recent quiz attempts for a user"""
        data = self._load_data()
        attempts = [qa for qa in data["quiz_attempted"] if qa["user_id"] == user_id]
        attempts.sort(key=lambda x: x["quiz_date"], reverse=True)
        attempts = attempts[:limit]
        
        return [
            (qa["id"], qa["question"], qa["user_answer"], qa["correct_answer"]) 
            for qa in attempts
        ]
    
    def delete_quiz_attempts_by_user(self, user_id):
        """Delete all quiz attempts for a user"""
        data = self._load_data()
        data["quiz_attempted"] = [qa for qa in data["quiz_attempted"] if qa["user_id"] != user_id]
        self._save_data(data)
        return True
    
    # Image operations
    def save_profile_image(self, user_id, image_binary):
        """Save or update user profile image"""
        data = self._load_data()
        
        # Convert binary to base64 for JSON storage
        image_b64 = base64.b64encode(image_binary).decode('utf-8')
        
        # Check if image exists
        for img in data["images"]:
            if img["user_id"] == user_id:
                img["profile_image"] = image_b64
                self._save_data(data)
                return True
        
        # Create new image entry
        image_id = self._get_next_id("image_id")
        image_entry = {
            "id": image_id,
            "user_id": user_id,
            "profile_image": image_b64
        }
        
        data["images"].append(image_entry)
        self._save_data(data)
        return True
    
    def get_profile_image(self, user_id):
        """Get user profile image"""
        data = self._load_data()
        for img in data["images"]:
            if img["user_id"] == user_id:
                # Convert base64 back to binary
                return (base64.b64decode(img["profile_image"].encode('utf-8')),)
        return None
    
    def delete_profile_image(self, user_id):
        """Delete user profile image"""
        data = self._load_data()
        data["images"] = [img for img in data["images"] if img["user_id"] != user_id]
        self._save_data(data)
        return True
    
    # Password reset token operations
    def create_password_reset_token(self, user_id, reset_token, token_expiry):
        """Create a password reset token"""
        data = self._load_data()
        token_id = self._get_next_id("token_id")
        
        token_entry = {
            "id": token_id,
            "user_id": user_id,
            "reset_token": reset_token,
            "token_expiry": token_expiry
        }
        
        data["password_reset_tokens"].append(token_entry)
        self._save_data(data)
        return token_id
    
    def get_password_reset_token(self, reset_token):
        """Get password reset token"""
        data = self._load_data()
        for token in data["password_reset_tokens"]:
            if token["reset_token"] == reset_token:
                return (token["id"], token["user_id"], token["reset_token"], token["token_expiry"])
        return None
    
    def delete_password_reset_token(self, user_id):
        """Delete password reset tokens for user"""
        data = self._load_data()
        data["password_reset_tokens"] = [
            t for t in data["password_reset_tokens"] if t["user_id"] != user_id
        ]
        self._save_data(data)
        return True


class HybridDatabaseConnection:
    """Wraps database operations with PostgreSQL primary and JSON fallback"""
    
    def __init__(self):
        self.postgres_available = False
        self.db = None
        self.cursor = None
        self.json_db = JSONDatabase()
        self._check_postgres_availability()
    
    def _check_postgres_availability(self):
        """Check if PostgreSQL is available"""
        try:
            test_conn = psycopg.connect(
                host=os.getenv("DB_HOST"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                dbname=os.getenv("DB_NAME"),
                port=int(os.getenv("DB_PORT", 5432)),
                timeout=5
            )
            test_conn.close()
            self.postgres_available = True
            logger.info("✓ PostgreSQL is available")
        except Exception as e:
            self.postgres_available = False
            logger.warning(f"✗ PostgreSQL unavailable, using JSON fallback: {str(e)}")
    
    def connect(self):
        """Connect to database (PostgreSQL or JSON)"""
        if self.postgres_available:
            try:
                self.db = psycopg.connect(
                    host=os.getenv("DB_HOST"),
                    user=os.getenv("DB_USER"),
                    password=os.getenv("DB_PASSWORD"),
                    dbname=os.getenv("DB_NAME"),
                    port=int(os.getenv("DB_PORT", 5432)),
                    timeout=5
                )
                self.cursor = self.db.cursor()
                return self
            except Exception as e:
                logger.warning(f"PostgreSQL connection failed: {e}, falling back to JSON")
                self.postgres_available = False
        
        return self
    
    def is_using_postgres(self):
        """Check if currently using PostgreSQL"""
        return self.postgres_available and self.db is not None
    
    def is_using_json(self):
        """Check if currently using JSON database"""
        return not self.is_using_postgres()
    
    def close(self):
        """Close database connection"""
        if self.cursor:
            try:
                self.cursor.close()
            except:
                pass
        if self.db:
            try:
                self.db.close()
            except:
                pass
    
    def __enter__(self):
        return self.connect()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Helper functions for app.py
def get_db_connection():
    """Get a hybrid database connection"""
    conn = HybridDatabaseConnection()
    conn.connect()
    return conn


def get_json_db():
    """Get JSON database instance"""
    return JSONDatabase()
