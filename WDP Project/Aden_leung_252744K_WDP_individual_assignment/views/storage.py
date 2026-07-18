import json
import os
from .models import User, Landmark, LandmarkOption, UserLandmark, Quest, UserQuest, Badge, UserBadge

DATA_FILE = 'data.json'

class DataStore:
    def __init__(self):
        self.next_id = {
            'user': 1,
            'landmark': 1,
            'landmark_option': 1,
            'user_landmark': 1,
            'quest': 1,
            'user_quest': 1,
            'badge': 1,
            'user_badge': 1,
            'quest_log': 1
        }
        self.users = []
        self.landmarks = []
        self.landmark_options = []
        self.user_landmarks = []
        self.quests = []
        self.user_quests = []
        self.badges = []
        self.user_badges = []
        self.quest_log = []   # NEW: per-user quest progress
        self.load_data()
    
    def load_data(self):
        """Load data from JSON file"""
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r') as f:
                    data = json.load(f)
                    self.users = [User.from_dict(u) for u in data.get('users', [])]
                    self.landmarks = [Landmark.from_dict(l) for l in data.get('landmarks', [])]
                    self.landmark_options = [LandmarkOption.from_dict(lo) for lo in data.get('landmark_options', [])]
                    self.user_landmarks = [UserLandmark.from_dict(ul) for ul in data.get('user_landmarks', [])]
                    self.quests = [Quest.from_dict(q) for q in data.get('quests', [])]
                    self.user_quests = [UserQuest.from_dict(uq) for uq in data.get('user_quests', [])]
                    self.badges = [Badge.from_dict(b) for b in data.get('badges', [])]
                    self.user_badges = [UserBadge.from_dict(ub) for ub in data.get('user_badges', [])]
                    self.quest_log = data.get("quest_log", [])
                    self.next_id = data.get('next_id', self.next_id)
            except Exception as e:
                print(f"Error loading data: {e}")
    
    def save_data(self):
        """Save data to JSON file"""
        try:
            data = {
                'users': [u.to_dict() for u in self.users],
                'landmarks': [l.to_dict() for l in self.landmarks],
                'landmark_options': [lo.to_dict() for lo in self.landmark_options],
                'user_landmarks': [ul.to_dict() for ul in self.user_landmarks],
                'quests': [q.to_dict() for q in self.quests],
                'user_quests': [uq.to_dict() for uq in self.user_quests],
                'badges': [b.to_dict() for b in self.badges],
                'user_badges': [ub.to_dict() for ub in self.user_badges],
                'quest_log': self.quest_log,
                'next_id': self.next_id
            }
            with open(DATA_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving data: {e}")
    
    def get_next_id(self, entity_type):
        """Get next available ID for entity"""
        current_id = self.next_id[entity_type]
        self.next_id[entity_type] += 1
        return current_id

# Global data store instance
data_store = DataStore()
store = data_store
