from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from . import models, bcrypt

auth_bp = Blueprint('auth_bp', __name__)

@auth_bp.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not name or not email or not password:
        return jsonify({"error": "Missing required fields"}), 400

    if models.User.find_by_email(email):
        return jsonify({"error": "Email address already in use"}), 409

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    user_id = models.User.create(name, email, hashed_password)
    
    new_user = models.User.find_by_id(user_id)
    login_user(new_user)

    return jsonify({
        "message": "Signup successful",
        "user": {"id": new_user.id, "name": new_user.name, "email": new_user.email, "apiKey": new_user.api_key}
    }), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    user = models.User.find_by_email(email)

    if user and bcrypt.check_password_hash(user.password_hash, password):
        login_user(user)
        return jsonify({
            "message": "Login successful",
            "user": {"id": user.id, "name": user.name, "email": user.email, "apiKey": user.api_key}
        })

    return jsonify({"error": "Invalid credentials"}), 401

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logout successful"}), 200

@auth_bp.route('/status')
def status():
    if current_user.is_authenticated:
        return jsonify({
            "loggedIn": True,
            "user": {"id": current_user.id, "name": current_user.name, "email": current_user.email, "apiKey": current_user.api_key}
        })
    return jsonify({"loggedIn": False})