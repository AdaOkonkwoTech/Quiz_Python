import base64
import binascii
from io import BytesIO
from flask import Flask, flash, jsonify, render_template, request, redirect, url_for, session, send_file
import bcrypt
from quiz import Quiz
import random
import os
from db import connect_to_database, create_database_if_not_exists, initialize_tables, USE_JSON_FALLBACK
from others.passwd_recovery import forgot_password_func, reset_password_func
import json_storage


app = Flask(__name__)
create_database_if_not_exists()  # ensure DB exists
initialize_tables()              # ensure tables exist

# Generate a random secret key
secret_key = os.urandom(24)
# Set the secret key for session
app.secret_key = secret_key

app.config['SESSION_COOKIE_SECURE'] = True  # Ensures cookies only work over HTTPS
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Helps with cross-site requests
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevents JS from accessing cookies

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


@app.route("/", methods=['GET', 'POST'])
def login():
    """Authenticating user """
    if request.method == 'POST':
        try:
            data = request.form
            username = data.get('username')
            passwd = data.get('password')

            if USE_JSON_FALLBACK:
                # Use JSON storage
                user = json_storage.get_user_by_username(username)
                if user:
                    if bcrypt.checkpw(passwd.encode('utf-8'), user['password'].encode('utf-8')):
                        session['user_id'] = user['id']
                        session['username'] = username
                        session['logged_in'] = True
                        print('Valid user\n')
                        return redirect(url_for('quiz'))
                    else:
                        print('wrong password\n')
                        return render_template('login.html', message="Wrong password")
                else:
                    print("User don't exist\n")
                    return render_template('login.html', message="User not found")
            else:
                # Use PostgreSQL
                db = connect_to_database()
                cursor = db.cursor()
            
                query = "SELECT id, password FROM users WHERE username = %s"
                cursor.execute(query, (username,))
                value = cursor.fetchone()

                if value:
                    user_id, hashed_password = value

                    if bcrypt.checkpw(passwd.encode('utf-8'), hashed_password.encode('utf-8')):
                        # Set session variable for logged in user
                        session['user_id'] = user_id
                        session['username'] = username
                        session['logged_in'] = True
                        print('Valid user\n')
                        session['logged_in'] = True
                        cursor.close()
                        db.close()
                        return redirect(url_for('quiz'))
                    else:
                        print('wrong password\n')
                        cursor.close()
                        db.close()
                        return render_template('login.html', message="Wrong password")
                else:
                    print("User don't exist\n")
                    cursor.close()
                    db.close()
                    return render_template('login.html', message="User not found")
        except Exception as e:
                return render_template('login.html', error=str(e))

    return render_template('login.html')


@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    return forgot_password_func(request)


@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    return reset_password_func(request)


def generate_username_suggestions(username):
    suggestions = []
    for i in range(3):
        # Append a random number to the username
        suggestion = str(username) + str(random.randint(1, 1000))
        suggestions.append(suggestion)
    return suggestions


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    ''' creating a new user '''
    if request.method == 'POST':
        data = request.form
        firstname = data.get('firstname')
        lastname = data.get('lastname')
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')

        # Ensure password is at least 6 character
        if len(password) < 6:
            return render_template('signup.html', error='Password must be at least six characters long')

        try:
            if USE_JSON_FALLBACK:
                # Use JSON storage
                existing_user = json_storage.get_user_by_username(username)
                if existing_user:
                    suggestions = generate_username_suggestions(username)
                    return render_template('signup.html', error='Username already exist.', suggestions=suggestions)

                user_id = json_storage.add_user(firstname, lastname, username, password, email)
                if user_id:
                    return redirect(url_for('login'))
                else:
                    return render_template('signup.html', error='Username or email already exists.')
            else:
                # Use PostgreSQL
                db = connect_to_database()
                cursor = db.cursor()

                query = "SELECT username FROM users WHERE username = %s"
                cursor.execute(query, (username,))
                existing_usernames = cursor.fetchone()

                if existing_usernames:
                    # Username already exists, generate suggestions
                    suggestions = generate_username_suggestions(existing_usernames)
                    cursor.close()
                    db.close()
                    return render_template('signup.html', error='Username already exist.', suggestions=suggestions)

                # encrypt the password
                hashed_passwd = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

                # insert new users into table
                query = 'INSERT INTO users (first_name, last_name, username, password, email) VALUES (%s, %s, %s, %s, %s)'
                cursor.execute(query, (firstname, lastname, username, hashed_passwd, email))
                db.commit()

                cursor.close()
                db.close()
                return redirect(url_for('login'))
        except Exception as e:
            if not USE_JSON_FALLBACK:
                db = connect_to_database()
                cursor = db.cursor()

                query = "SELECT username FROM users WHERE username = %s"
                cursor.execute(query, (username,))
                existing_usernames = cursor.fetchone()

                query2 = "SELECT email FROM users WHERE email = %s"
                cursor.execute(query2, (email,))
                existing_email = cursor.fetchone()

                cursor.close()
                db.close()

                if existing_usernames:
                    # Username already exists, generate suggestions
                    suggestions = generate_username_suggestions(existing_usernames)
                    return render_template('signup.html', error='Username already exist.', suggestions=suggestions)

                if existing_email:
                    # Email already exists
                    return render_template('signup.html', error='Email already exist.')

            # if registration fails return response
            return render_template('signup.html', error=str(e))

    return render_template('signup.html')


@app.route('/quiz')
def quiz():
    try:
        ''' output to browser '''
        print("Logged in status:", session.get('logged_in'))
        if 'logged_in' not in session or not session['logged_in']:
            return redirect(url_for('login'))

        # api endpoint
        api_url = "https://the-trivia-api.com/v2/questions"

        # create Quiz instance
        quiz = Quiz(api_url)
        random.shuffle(quiz.questions)
        # print("Quiz Questions:", quiz.questions)
        return render_template('quiz.html', questions=quiz.questions)
    except Exception as e:
        render_template('quiz.html', error=str(e))


@app.route('/submit', methods=['POST'])
def submit():
    ''' handle form returned data '''
    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('login'))

    user_id = session.get('user_id')
    score = 0
    total_questions = int(request.form.get('total_questions'))
    question_data = []

    for key, value in request.form.items():
        if key.startswith('opt'):
            que_index = key[3:] # Extract index of the question
            question_key = 'question' + que_index
            correct_answer_key = 'correct' + que_index

            question = request.form.get(question_key)
            correct_ans = request.form.get(correct_answer_key)

            # gather questions data for table display
            question_data.append({
                'question': question,
                'user_answer': value,
                'correct_answer': correct_ans
            })
            
            # increase score by 1 for correct answer
            if value == correct_ans:
                score += 1

    try:
        if USE_JSON_FALLBACK:
            # Use JSON storage
            quiz_score_id = json_storage.add_quiz_score(user_id, score, total_questions)
            
            # Insert attempted quiz data
            if quiz_score_id:
                for attempt in question_data:
                    json_storage.add_quiz_attempt(user_id, quiz_score_id, attempt['question'], 
                                                 attempt['user_answer'], attempt['correct_answer'])
        else:
            # Use PostgreSQL
            db = connect_to_database()
            cursor = db.cursor()

            # Insert quiz score into quiz_score table
            cursor.execute('''INSERT INTO quiz_scores (user_id, score, total_questions)
                              VALUES (%s, %s, %s)''', (user_id, score, total_questions))

            db.commit()

            # Retrieve quiz_score_id
            quiz_score_id = None
            if cursor.lastrowid is not None:
                quiz_score_id = cursor.lastrowid

            # Insert attempted quiz data into quiz_attempted table
            if quiz_score_id is not None:
                for attempt in question_data:
                    cursor.execute('''INSERT INTO quiz_attempted (user_id, question, user_answer, correct_answer, quiz_score_id)
                                      VALUES (%s, %s, %s, %s, %s)''', (user_id, attempt['question'], attempt['user_answer'], attempt['correct_answer'], quiz_score_id))

            db.commit()
            cursor.close()
            db.close()
    except Exception as e:
        print(f"Error saving quiz: {e}")

    return render_template('result.html',
        score=score,
        total_questions=total_questions,
        question_data=question_data)


@app.route('/dashboard')
def dashboard():
    ''' display users personal data '''
    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('login'))

    user_id = session.get('user_id')

    try:
        if USE_JSON_FALLBACK:
            # Use JSON storage
            profile_image = json_storage.get_user_image(user_id)
            
            user = json_storage.get_user_by_id(user_id)
            username = user['username'] if user else "Unknown"
            
            quiz_scores = json_storage.get_quiz_scores_by_user(user_id)
            quiz_scores.sort(key=lambda x: x['quiz_date'], reverse=True)
            
            quiz_metadata = [{'quiz_date': score['quiz_date'], 'score': score['score'], 
                            'total_questions': score['total_questions'], 'id': score['id']} 
                            for score in quiz_scores]
        else:
            # Use PostgreSQL
            db = connect_to_database()
            cursor = db.cursor()

            # Retrieve profile image from the database
            cursor.execute("SELECT profile_image FROM images WHERE user_id = %s", (user_id,))
            profile_image_data = cursor.fetchone()
            profile_image = None
            if profile_image_data:
                profile_image = base64.b64encode(profile_image_data[0]).decode('utf-8')

            # Retrieve username
            cursor.execute('''SELECT username FROM users WHERE id = %s''', (user_id,))
            username = cursor.fetchone()[0]
            print(username)

            # Retrieve quiz data for the user
            cursor.execute('''SELECT id, score, total_questions, quiz_date FROM quiz_scores WHERE user_id = %s ORDER BY quiz_date DESC''', (user_id,))
            quiz_metadata = cursor.fetchall()

            # Convert quiz_metadata tuples to dictionaries for easier access
            quiz_metadata = [{'quiz_date': row[3], 'score': row[1], 'total_questions': row[2], 'id': row[0]} for row in quiz_metadata]

            cursor.close()
            db.close()
    except Exception as e:
        print(f"Error loading dashboard: {e}")
        return redirect(url_for('login'))
    
    api_endpoint = request.url_root + url_for('attempted_question_api')
    
    return render_template(
        'dashboard.html',
        username=username,
        profile_image=profile_image,
        quiz_metadata=quiz_metadata,
        api_endpoint=api_endpoint)


@app.route('/view_quiz/<int:quiz_score_id>')
def view_quiz(quiz_score_id):
    """display specific quiz data"""
    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('login'))

    user_id = session.get('user_id')

    try:
        if USE_JSON_FALLBACK:
            # Use JSON storage
            quizzes = json_storage.get_quiz_attempts_by_score_id(quiz_score_id, user_id)
            quiz_metadata = [{'question': q['question'], 'user_answer': q['user_answer'], 
                            'correct_answer': q['correct_answer']} for q in quizzes]
        else:
            # Use PostgreSQL
            db = connect_to_database()
            cursor = db.cursor()

            # query db for specific quiz
            cursor.execute('''SELECT question, user_answer, correct_answer FROM quiz_attempted WHERE quiz_score_id = %s AND user_id = %s''',
                           (quiz_score_id, user_id))
            quizzes = cursor.fetchall()

            # Convert quiz_metadata tuples to dictionaries for easier access
            quiz_metadata = [{'question': row[0], 'user_answer': row[1], 'correct_answer': row[2]} for row in quizzes]

            cursor.close()
            db.close()
    except Exception as e:
        print(f"Error loading quiz: {e}")
        return redirect(url_for('dashboard'))

    return render_template('view_quiz.html', quizzes=quiz_metadata)


@app.route('/questions')
def attempted_question_api():
    """Retrieve latest 20 attempted_quiz data in JSON"""
    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('login'))

    user_id = session.get('user_id')

    try:
        if USE_JSON_FALLBACK:
            # Use JSON storage
            quizzes = json_storage.get_latest_quiz_attempts_by_user(user_id, limit=20)
        else:
            # Use PostgreSQL
            db = connect_to_database()
            cursor = db.cursor()

            # Query the database for latest 20 quiz data
            cursor.execute('''SELECT qa.id, qa.question, qa.user_answer, qa.correct_answer 
                              FROM quiz_attempted qa
                              JOIN users u ON qa.user_id = u.id
                              WHERE u.id = %s
                              ORDER BY qa.quiz_date DESC 
                              LIMIT 20''', (user_id,))
            quizzes = cursor.fetchall()

            cursor.close()
            db.close()
    except Exception as e:
        print(f"Error retrieving questions: {e}")
        return jsonify({'questions': []})

    json_quiz = []
    for row in quizzes:
        # Ensure all elements of the row are defined
        if USE_JSON_FALLBACK:
            # JSON format
            quiz_data = {
                "id": row['id'],
                "text": row['question'],
                "answer": [
                    {"text": row['user_answer'], "correct": row['correct_answer'] == row['user_answer']},
                    {"text": row['correct_answer'], "correct": True}
                ]
            }
        else:
            # Database format (tuple)
            quiz_data = {
                "id": row[0],
                "text": row[1],
                "answer": [
                    {"text": row[2], "correct": row[3] == row[2]},
                    {"text": row[3], "correct": True}
                ]
            }
        json_quiz.append(quiz_data)

    # Return the data as JSON and endpoint URL
    return jsonify({'questions': json_quiz})


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    ''' uploads, retrieval, display, and editing user Profle page '''
    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('login'))
    
    user_id = session.get('user_id')
    message = None

    try:
        if request.method == 'POST':
           
            # retrieve details to edit from client side
            firstname = request.form.get('firstname')
            lastname = request.form.get('lastname')
            username = request.form.get('username')
            profile_image = request.files.get('profile_image')
        
            print(profile_image)
            
            if USE_JSON_FALLBACK:
                # Use JSON storage
                # Update user details
                if firstname:
                    json_storage.update_user(user_id, first_name=firstname)
                if lastname:
                    json_storage.update_user(user_id, last_name=lastname)
                if username:
                    json_storage.update_user(user_id, username=username)
                if profile_image:
                    if profile_image.filename == '':
                        print('No selected file')
                        return redirect(request.url)

                    if allowed_file(profile_image.filename):
                        try:
                            profile_binary = profile_image.read()
                            print(profile_binary)
                            if json_storage.save_user_image(user_id, profile_binary):
                                message = "Profile image updated successfully"
                            else:
                                message = "Failed to save profile image"
                        except Exception as e:
                            print(f"An error occurred: {e}")
                            message = f"An error occurred: {e}"
                            return redirect(request.url)
                    else:
                        print('Invalid file type')
                        message = "Invalid file type"
            else:
                # Use PostgreSQL
                db = connect_to_database()
                cursor = db.cursor()
                
                # Update user details to db
                if firstname:
                    cursor.execute('''UPDATE users SET first_name = %s WHERE id = %s''',
                                    (firstname, user_id))
                    db.commit()
                if lastname:
                    cursor.execute('''UPDATE users SET last_name = %s WHERE id = %s''',
                                    (lastname, user_id))
                    db.commit()
                if username:
                    cursor.execute('''UPDATE users SET username = %s WHERE id = %s''',
                                    (username, user_id))
                    db.commit()
                if profile_image:
                    if profile_image.filename == '':
                        print('No selected file')
                        cursor.close()
                        db.close()
                        return redirect(request.url)

                    if allowed_file(profile_image.filename):
                        try:
                            profile_binary = profile_image.read()
                            print(profile_binary)
                            cursor.execute('''SELECT * FROM images WHERE user_id = %s''', (user_id,))
                            existing_image = cursor.fetchone()

                            if existing_image:
                                cursor.execute('''UPDATE images SET profile_image = %s WHERE user_id = %s''', (profile_binary, user_id))
                                db.commit()
                                message = "Profile image updated successfully"
                            else:
                                cursor.execute('''INSERT INTO images (user_id, profile_image) VALUES (%s, %s)''', (user_id, profile_binary))
                                message = "Profile image added successfully"
                            db.commit()
                        except Exception as e:
                            print(f"An error occurred: {e}")
                            message = "An error occurred: {e}"
                            cursor.close()
                            db.close()
                            return redirect(request.url)
                    else:
                        print('Invalid file type')
                        message = "Invalid file type"
                
                cursor.close()
                db.close()

        if USE_JSON_FALLBACK:
            # Use JSON storage
            user = json_storage.get_user_by_id(user_id)
            user = (user['first_name'], user['last_name'], user['username']) if user else (None, None, None)
            profile_image = json_storage.get_user_image(user_id)
        else:
            # Use PostgreSQL
            db = connect_to_database()
            cursor = db.cursor()

            # Fetch user details from the database
            cursor.execute('''SELECT first_name, last_name, username FROM users WHERE id = %s''', (user_id,))
            user = cursor.fetchone()

            # Retrieve profile image from the database
            cursor.execute("SELECT profile_image FROM images WHERE user_id = %s", (user_id,))
            profile_image_data = cursor.fetchone()
            profile_image = None
            if profile_image_data:
                profile_image = base64.b64encode(profile_image_data[0]).decode('utf-8')

            cursor.close()
            db.close()
    except Exception as e:
        print(f"Error in profile: {e}")
        return redirect(url_for('login'))

    return render_template('profile.html', user=user, profile_image=profile_image, message=message)


@app.route('/header_profile_image')
def header_profile_image():
    ''' Fetch and render the header with profile image '''
    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('login'))

    user_id = session.get('user_id')

    try:
        if USE_JSON_FALLBACK:
            # Use JSON storage
            profile_image = json_storage.get_user_image(user_id)
        else:
            # Use PostgreSQL
            db = connect_to_database()
            cursor = db.cursor()

            # Retrieve profile image from the database
            cursor.execute("SELECT profile_image FROM images WHERE user_id = %s", (user_id,))
            profile_image_data = cursor.fetchone()
            profile_image = None
            if profile_image_data:
                profile_image = base64.b64encode(profile_image_data[0]).decode('utf-8')

            cursor.close()
            db.close()
    except Exception as e:
        print(f"Error retrieving profile image: {e}")
        profile_image = None

    return profile_image


@app.route('/about')
def about():
    ''' display about page '''
    return render_template('about.html')


@app.route('/logout')
def logout():
    ''' end and clear sessions for logged in users '''
    # clear the sessions
    session.clear()
    return redirect(url_for('login'))


@app.route('/delete_acct')
def delete_acct():
    ''' route to warning page '''
    return render_template('delete_acct.html')


@app.route('/delete_account', methods=['GET', 'POST'])
def delete_account():
    
    """Delete user account"""
    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('login'))

    user_id = session.get('user_id')

    try:
        if USE_JSON_FALLBACK:
            # Use JSON storage
            json_storage.delete_password_reset_tokens_by_user(user_id)
            json_storage.delete_user_image(user_id)
            json_storage.delete_quiz_attempts_by_user(user_id)
            json_storage.delete_quiz_scores_by_user(user_id)
            json_storage.delete_user(user_id)
        else:
            # Use PostgreSQL
            db = connect_to_database()
            cursor = db.cursor()
            
            # Delete user's password reset tokens
            cursor.execute("DELETE FROM password_reset_tokens WHERE user_id = %s", (user_id,))
            
            # Delete user's images
            cursor.execute("DELETE FROM images WHERE user_id = %s", (user_id,))

            # Delete user's attempted quizzes from quiz_attempted table
            cursor.execute("DELETE FROM quiz_attempted WHERE user_id = %s", (user_id,))

            # Delete user's quiz scores from quiz_scores table
            cursor.execute("DELETE FROM quiz_scores WHERE user_id = %s", (user_id,))

            # Delete user from users table
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))

            # Commit the transactions
            db.commit()
            
            cursor.close()
            db.close()

        # Clear the session
        session.clear()

        return redirect(url_for('login'))
    except Exception as e:
        # If an error occurs, render an error message
        return render_template('delete_acct.html', error=str(e))


if __name__ == '__main__':
    app.run(debug=True)
