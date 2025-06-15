# project/api.py

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from bson import ObjectId
from datetime import datetime, timedelta

from . import models

api_bp = Blueprint('api_bp', __name__)
db = models.db

# --- Email Campaign Management ---
@api_bp.route('/campaigns', methods=['POST'])
@login_required
def create_campaign():
    data = request.get_json()
    name = data.get('name')
    if not name: return jsonify({"error": "Campaign name is required"}), 400
    campaign = {'name': name, 'user_id': ObjectId(current_user.id), 'created_at': datetime.utcnow(), 'status': 'active', 'open_count': 0}
    result = db.campaigns.insert_one(campaign)
    campaign['_id'] = str(result.inserted_id)
    campaign['user_id'] = str(campaign['user_id'])
    return jsonify(campaign), 201

@api_bp.route('/campaigns', methods=['GET'])
@login_required
def get_campaigns():
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
    data = request.get_json()
    new_status = 'active' if data.get('status') is True else 'inactive'
    result = db.campaigns.update_one({'_id': ObjectId(campaign_id), 'user_id': ObjectId(current_user.id)}, {'$set': {'status': new_status}})
    if result.matched_count == 0: return jsonify({"error": "Campaign not found or unauthorized"}), 404
    return jsonify({"message": f"Campaign status updated to {new_status}"})

# --- Tracked Link Management ---
@api_bp.route('/links', methods=['POST'])
@login_required
def create_link():
    data = request.get_json()
    name = data.get('name')
    destination_url = data.get('destination_url')
    if not name or not destination_url: return jsonify({"error": "Link name and destination URL are required"}), 400
    link = {'name': name, 'destination_url': destination_url, 'user_id': ObjectId(current_user.id), 'created_at': datetime.utcnow(), 'status': 'active', 'click_count': 0}
    result = db.tracked_links.insert_one(link)
    link['_id'] = str(result.inserted_id)
    link['user_id'] = str(link['user_id'])
    return jsonify(link), 201

@api_bp.route('/links', methods=['GET'])
@login_required
def get_links():
    links_cursor = db.tracked_links.find({'user_id': ObjectId(current_user.id)}).sort('created_at', -1)
    links_list = []
    for l in links_cursor:
        l['_id'] = str(l['_id'])
        l['user_id'] = str(l['user_id'])
        links_list.append(l)
    return jsonify(links_list)

@api_bp.route('/links/<link_id>/status', methods=['PUT'])
@login_required
def toggle_link_status(link_id):
    data = request.get_json()
    new_status = 'active' if data.get('status') is True else 'inactive'
    result = db.tracked_links.update_one({'_id': ObjectId(link_id), 'user_id': ObjectId(current_user.id)}, {'$set': {'status': new_status}})
    if result.matched_count == 0: return jsonify({"error": "Link not found or unauthorized"}), 404
    return jsonify({"message": f"Link status updated to {new_status}"})

# --- Event Log Endpoints ---

@api_bp.route('/events/opens', methods=['GET'])
@login_required
def get_open_events():
    """Fetches all open events for the currently logged-in user."""
    campaign_id = request.args.get('id')
    query = {'user_id': ObjectId(current_user.id)}
    if campaign_id:
        query['campaign_id'] = ObjectId(campaign_id)

    events_cursor = db.open_events.find(query).sort('opened_at', -1)
    
    campaign_ids = [e['campaign_id'] for e in events_cursor.rewind() if 'campaign_id' in e]
    campaigns = db.campaigns.find({'_id': {'$in': campaign_ids}})
    campaign_name_map = {str(c['_id']): c['name'] for c in campaigns}
    
    events_list = []
    for event in events_cursor.rewind():
        event['_id'] = str(event['_id'])
        event['user_id'] = str(event['user_id'])
        if 'campaign_id' in event:
            campaign_id_str = str(event['campaign_id'])
            event['campaign_id'] = campaign_id_str
            event['campaign_name'] = campaign_name_map.get(campaign_id_str, 'Unknown Campaign')
        events_list.append(event)
        
    return jsonify(events_list)

@api_bp.route('/events/clicks', methods=['GET'])
@login_required
def get_click_events():
    """Fetches all click events for the currently logged-in user."""
    link_id = request.args.get('id')
    query = {'user_id': ObjectId(current_user.id)}
    if link_id:
        query['link_id'] = ObjectId(link_id)

    events_cursor = db.click_events.find(query).sort('clicked_at', -1)
    
    link_ids = [e['link_id'] for e in events_cursor.rewind() if 'link_id' in e]
    links = db.tracked_links.find({'_id': {'$in': link_ids}})
    link_name_map = {str(l['_id']): l['name'] for l in links}
    
    events_list = []
    for event in events_cursor.rewind():
        event['_id'] = str(event['_id'])
        event['user_id'] = str(event['user_id'])
        if 'link_id' in event:
            link_id_str = str(event['link_id'])
            event['link_id'] = link_id_str
            event['link_name'] = link_name_map.get(link_id_str, 'Unknown Link')
        events_list.append(event)
        
    return jsonify(events_list)


# --- Dashboard Stats ---
@api_bp.route('/stats/summary')
@login_required
def get_summary_stats():
    user_id = ObjectId(current_user.id)
    total_campaigns = db.campaigns.count_documents({'user_id': user_id})
    total_links = db.tracked_links.count_documents({'user_id': user_id})
    opens_pipeline = [{'$match': {'user_id': user_id}}, {'$group': {'_id': '$user_id', 'total_opens': {'$sum': '$open_count'}}}]
    opens_result = list(db.campaigns.aggregate(opens_pipeline))
    total_opens = opens_result[0]['total_opens'] if opens_result else 0
    clicks_pipeline = [{'$match': {'user_id': user_id}}, {'$group': {'_id': '$user_id', 'total_clicks': {'$sum': '$click_count'}}}]
    clicks_result = list(db.tracked_links.aggregate(clicks_pipeline))
    total_clicks = clicks_result[0]['total_clicks'] if clicks_result else 0
    return jsonify({'total_campaigns': total_campaigns, 'total_links': total_links, 'total_opens': total_opens, 'total_clicks': total_clicks})


# --- Analytics Endpoints ---

@api_bp.route('/analytics/email')
@login_required
def get_email_analytics_overview():
    """Provides aggregated analytics for ALL email campaigns for the user."""
    user_id = ObjectId(current_user.id)

    opens_by_day = list(db.open_events.aggregate([
        {'$match': {'user_id': user_id, 'is_real_open': True, 'opened_at': {'$gte': datetime.utcnow() - timedelta(days=30)}}},
        {'$project': {'date': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$opened_at'}}}},
        {'$group': {'_id': '$date', 'count': {'$sum': 1}}},
        {'$sort': {'_id': 1}}
    ]))
    
    top_countries = list(db.open_events.aggregate([
        {'$match': {'user_id': user_id, 'is_real_open': True, 'geo_info.country': {'$ne': None}}},
        {'$group': {'_id': '$geo_info.country', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}},
        {'$limit': 5}
    ]))

    recent_opens_cursor = db.open_events.find({'user_id': user_id, 'is_real_open': True}).sort('opened_at', -1).limit(10)
    
    campaign_ids = [event['campaign_id'] for event in recent_opens_cursor.rewind() if 'campaign_id' in event]
    campaigns = db.campaigns.find({'_id': {'$in': campaign_ids}})
    campaign_name_map = {str(c['_id']): c['name'] for c in campaigns}

    recent_opens = []
    for event in recent_opens_cursor.rewind():
        event['_id'] = str(event['_id'])
        event['user_id'] = str(event['user_id'])
        if 'campaign_id' in event:
            campaign_id_str = str(event['campaign_id'])
            event['campaign_id'] = campaign_id_str
            event['campaign_name'] = campaign_name_map.get(campaign_id_str, "Unknown Campaign")
        recent_opens.append(event)

    return jsonify({
        'opens_by_day': opens_by_day,
        'top_countries': top_countries,
        'recent_opens': recent_opens
    })