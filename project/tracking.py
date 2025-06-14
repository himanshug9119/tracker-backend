from flask import Blueprint, request, redirect, send_file
from . import models
from datetime import datetime
import io
import requests

tracking_bp = Blueprint('tracking_bp', __name__)

TRANSPARENT_PNG = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
db = models.db

# Re-using a simplified version of your IP info helper
def get_ip_info(ip_address: str, api_key: str) -> dict:
    try:
        url = f"https://ipgeolocation.abstractapi.com/v1/?api_key={api_key}&ip_address={ip_address}"
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            return {
                'city': data.get('city'), 'country': data.get('country'),
                'isp': data.get('connection', {}).get('isp_name')
            }
    except Exception:
        return {}
    return {}

@tracking_bp.route('/track')
def track_open():
    api_key = request.args.get('api_key')
    uid = request.args.get('uid') # This is the campaign/link id

    user = models.User.find_by_api_key(api_key) if api_key else None
    if not user or not uid:
        return send_file(io.BytesIO(TRANSPARENT_PNG), mimetype='image/png')

    user_agent = request.headers.get('User-Agent', '')
    is_google_proxy = 'GoogleImageProxy' in user_agent

    if is_google_proxy:
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
        now = datetime.utcnow()
        geo_info = get_ip_info(ip_address, models.db.app.config['ABSTRACT_API_KEY'])
        
        db.open_events.insert_one({
            'campaign_uid': uid,
            'user_id': ObjectId(user.id),
            'ip': ip_address,
            'user_agent': user_agent,
            'opened_at': now,
            'geo_info': geo_info
        })
        # Increment open count for the campaign
        db.campaigns.update_one({'_id': ObjectId(uid)}, {'$inc': {'open_count': 1}})

    return send_file(io.BytesIO(TRANSPARENT_PNG), mimetype='image/png')


@tracking_bp.route('/click')
def track_click():
    api_key = request.args.get('api_key')
    uid = request.args.get('uid') # This is the campaign/link id
    dest_url = request.args.get('url')

    user = models.User.find_by_api_key(api_key) if api_key else None
    if not user or not uid or not dest_url:
        return "Invalid tracking link.", 400

    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
    now = datetime.utcnow()
    geo_info = get_ip_info(ip_address, models.db.app.config['ABSTRACT_API_KEY'])
    
    db.click_events.insert_one({
        'link_uid': uid,
        'user_id': ObjectId(user.id),
        'destination_url': dest_url,
        'ip': ip_address,
        'user_agent': request.headers.get('User-Agent', ''),
        'clicked_at': now,
        'geo_info': geo_info
    })
    # Increment click count for the tracked link
    db.tracked_links.update_one({'_id': ObjectId(uid)}, {'$inc': {'click_count': 1}})

    return redirect(dest_url, code=302) # Using 302 is common and safe here