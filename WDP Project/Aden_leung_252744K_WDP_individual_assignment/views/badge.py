from datetime import datetime
from storage import data_store
from models import UserBadge

def check_and_award_badges(user):
    """Check if user has earned any new badges"""
    newly_earned = []
    
    for badge in data_store.badges:
        # Check if user already has this badge
        user_badge = next(
            (ub for ub in data_store.user_badges 
             if ub.user_id == user.id and ub.badge_id == badge.id),
            None
        )
        
        # If user doesn't have badge, check if they qualify
        if not user_badge or not user_badge.earned:
            if check_badge_requirement(user, badge):
                if user_badge:
                    user_badge.earned = True
                    user_badge.earned_at = datetime.utcnow().isoformat()
                else:
                    user_badge = UserBadge(
                        user_id=user.id,
                        badge_id=badge.id,
                        id=data_store.get_next_id('user_badge'),
                        earned=True,
                        earned_at=datetime.utcnow().isoformat()
                    )
                    data_store.user_badges.append(user_badge)
                
                newly_earned.append(badge)
    
    if newly_earned:
        data_store.save_data()
    
    return newly_earned


def check_badge_requirement(user, badge):
    """Check if user meets badge requirements"""
    if badge.requirement_type == 'points':
        return user.total_points >= badge.threshold
    
    elif badge.requirement_type == 'landmarks':
        completed_landmarks = sum(
            1 for ul in data_store.user_landmarks 
            if ul.user_id == user.id and ul.completed
        )
        return completed_landmarks >= badge.threshold
    
    elif badge.requirement_type == 'quests':
        completed_quests = sum(
            1 for uq in data_store.user_quests 
            if uq.user_id == user.id and uq.completed
        )
        return completed_quests >= badge.threshold
    
    elif badge.requirement_type == 'tier':
        return user.current_tier >= badge.threshold
    
    return False


def get_user_badges(user_id):
    """Get all badges for a user"""
    user_badges = [ub for ub in data_store.user_badges if ub.user_id == user_id]
    
    result = []
    for ub in user_badges:
        badge = next((b for b in data_store.badges if b.id == ub.badge_id), None)
        if badge:
            result.append({
                'badge': badge.to_dict(),
                'earned': ub.earned,
                'earned_at': ub.earned_at
            })
    
    return result


def register_badge_routes(app):
    """Register badge-related routes"""
    from flask import jsonify
    
    @app.route('/api/users/<int:user_id>/badges', methods=['GET'])
    def get_badges_for_user(user_id):
        """Get all badges for a user"""
        badges = get_user_badges(user_id)
        return jsonify(badges)
    
    @app.route('/api/badges', methods=['GET'])
    def get_all_badges():
        """Get all available badges"""
        return jsonify([b.to_dict() for b in data_store.badges])