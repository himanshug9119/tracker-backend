# project/tracking.py

from flask import Blueprint, request, redirect, send_file
from . import models
from datetime import datetime
import io
import requests
from bson import ObjectId

tracking_bp = Blueprint('tracking_bp', __name__)

TRANSPARENT_PNG = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
db = models.db

def get_ip_info(ip_address: str) -> dict:
    try:
        from flask import current_app
        api_key = current_app.config['ABSTRACT_API_KEY']
        
        url = f"https://ipgeolocation.abstractapi.com/v1/?api_key={api_key}&ip_address={ip_address}"
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            return {
                'city': data.get('city'), 'country': data.get('country'), 'country_code': data.get('country_code'),
                'isp': data.get('connection', {}).get('isp_name')
            }
    except Exception as e:
        print(f"IP info lookup failed: {e}")
    return {}

@tracking_bp.route('/track')
def track_open():
    api_key = request.args.get('api_key')
    uid = request.args.get('uid')

    user = models.User.find_by_api_key(api_key) if api_key else None
    if not user or not uid:
        return send_file(io.BytesIO(TRANSPARENT_PNG), mimetype='image/png')

    user_agent = request.headers.get('User-Agent', '')
    is_google_proxy = 'GoogleImageProxy' in user_agent

    if is_google_proxy:
        try:
            campaign = db.campaigns.find_one({'_id': ObjectId(uid), 'user_id': ObjectId(user.id)})
            
            if not campaign or campaign.get('status') != 'active':
                return send_file(io.BytesIO(TRANSPARENT_PNG), mimetype='image/png')

            ip_address = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
            now = datetime.utcnow()
            geo_info = get_ip_info(ip_address)
            
            # --- USING STANDARDIZED 'campaign_id' FIELD ---
            db.open_events.insert_one({
                'campaign_id': ObjectId(uid), # CORRECT
                'user_id': ObjectId(user.id),
                'ip': ip_address,
                'user_agent': user_agent,
                'opened_at': now,
                'geo_info': geo_info,
                'is_real_open': True
            })
            
            db.campaigns.update_one({'_id': ObjectId(uid)}, {'$inc': {'open_count': 1}})
            print(f"Tracked OPEN for campaign: {uid}")
        except Exception as e:
            print(f"Error during open tracking: {e}")
    
    return send_file(io.BytesIO(TRANSPARENT_PNG), mimetype='image/png')


@tracking_bp.route('/click')
def track_click():
    api_key = request.args.get('api_key')
    uid = request.args.get('uid')
    dest_url = request.args.get('url')

    if not dest_url:
        return "Invalid link: No destination URL provided.", 400
        
    user = models.User.find_by_api_key(api_key) if api_key else None
    if not user or not uid:
        return redirect(dest_url, code=302)

    try:
        tracked_link = db.tracked_links.find_one({'_id': ObjectId(uid), 'user_id': ObjectId(user.id)})

        if not tracked_link or tracked_link.get('status') != 'active':
            return redirect(dest_url, code=302)
        
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
        now = datetime.utcnow()
        geo_info = get_ip_info(ip_address)
        
        # --- USING STANDARDIZED 'link_id' FIELD ---
        db.click_events.insert_one({
            'link_id': ObjectId(uid), # CORRECT
            'user_id': ObjectId(user.id),
            'destination_url': dest_url,
            'ip': ip_address,
            'user_agent': request.headers.get('User-Agent', ''),
            'clicked_at': now,
            'geo_info': geo_info
        })
        
        db.tracked_links.update_one({'_id': ObjectId(uid)}, {'$inc': {'click_count': 1}})
        print(f"Tracked CLICK for link: {uid}")
    except Exception as e:
        print(f"Error during click tracking: {e}")

    return redirect(dest_url, code=302)