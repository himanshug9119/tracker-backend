from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from bson import ObjectId
from datetime import datetime
from . import models

api_bp = Blueprint('api_bp', __name__)
db = models.db

# --- Email Campaign Management ---

@api_bp.route('/campaigns', methods=['POST'])
@login_required
def create_campaign():
    data = request.get_json()
    name = data.get('name')
    if not name:
        return jsonify({"error": "Campaign name is required"}), 400

    campaign = {
        'name': name,
        'user_id': ObjectId(current_user.id),
        'created_at': datetime.utcnow(),
        'status': 'active',
        'open_count': 0
    }
    result = db.campaigns.insert_one(campaign)
    
    # --- FIX IS HERE ---
    # After inserting, the 'campaign' dictionary still has an ObjectId.
    # We need to convert it to a string before sending it as JSON.
    campaign['_id'] = str(result.inserted_id)
    campaign['user_id'] = str(campaign['user_id']) # Also convert the user_id

    return jsonify(campaign), 201

@api_bp.route('/campaigns', methods=['GET'])
@login_required
def get_campaigns():
    # This function was already correct, no changes needed.
    campaigns_cursor = db.campaigns.find({'user_id': ObjectId(current_user.id)}).sort('created_at', -1)
    campaigns_list = []
    for c in campaigns_cursor:
        c['_id'] = str(c['_id'])
        c['user_id'] = str(c['user_id'])
        campaigns_list.append(c)
    return jsonify(campaigns_list)

@api_bp.route('/campaigns/<campaign_id>/status', methods=['PUT'])
@login_required
def toggle_campaign_status(campaign_id):
    # This function doesn't return the object, so it's fine.
    data = request.get_json()
    new_status = 'active' if data.get('status') == 'active' else 'inactive'
    
    result = db.campaigns.update_one(
        {'_id': ObjectId(campaign_id), 'user_id': ObjectId(current_user.id)},
        {'$set': {'status': new_status}}
    )

    if result.matched_count == 0:
        return jsonify({"error": "Campaign not found or unauthorized"}), 404
    return jsonify({"message": f"Campaign status updated to {new_status}"})


# --- Tracked Link Management ---

@api_bp.route('/links', methods=['POST'])
@login_required
def create_link():
    data = request.get_json()
    name = data.get('name')
    destination_url = data.get('destination_url')
    if not name or not destination_url:
        return jsonify({"error": "Link name and destination URL are required"}), 400

    link = {
        'name': name,
        'destination_url': destination_url,
        'user_id': ObjectId(current_user.id),
        'created_at': datetime.utcnow(),
        'status': 'active',
        'click_count': 0
    }
    result = db.tracked_links.insert_one(link)

    # --- FIX IS HERE ---
    # Convert ObjectIds to strings before returning JSON
    link['_id'] = str(result.inserted_id)
    link['user_id'] = str(link['user_id'])
    
    return jsonify(link), 201

@api_bp.route('/links', methods=['GET'])
@login_required
def get_links():
    # This function was already correct, but let's ensure consistency.
    links_cursor = db.tracked_links.find({'user_id': ObjectId(current_user.id)}).sort('created_at', -1)
    links_list = []
    for l in links_cursor:
        l['_id'] = str(l['_id'])
        l['user_id'] = str(l['user_id'])
        links_list.append(l)
    return jsonify(links_list)

# You can add other management routes here later, like for toggling link status.
# For example:
@api_bp.route('/links/<link_id>/status', methods=['PUT'])
@login_required
def toggle_link_status(link_id):
    data = request.get_json()
    new_status = 'active' if data.get('status') == 'active' else 'inactive'
    
    result = db.tracked_links.update_one(
        {'_id': ObjectId(link_id), 'user_id': ObjectId(current_user.id)},
        {'$set': {'status': new_status}}
    )

    if result.matched_count == 0:
        return jsonify({"error": "Link not found or unauthorized"}), 404
    return jsonify({"message": f"Link status updated to {new_status}"})