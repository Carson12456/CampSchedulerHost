"""
Historical Trend Analysis (Item 16)
Track activity popularity and scheduling success across multiple weeks.
"""
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

class ScheduleAnalytics:
    """Analytics tracker for historical schedule data."""
    
    def __init__(self, db_path="analytics_db.json"):
        self.db_path = Path(db_path)
        self.data = self._load_db()
    
    def _load_db(self):
        """Load analytics database."""
        if self.db_path.exists():
            with open(self.db_path, 'r') as f:
                return json.load(f)
        return {'weeks': {}, 'activities': {}, 'last_updated': None}
    
    def _save_db(self):
        """Save analytics database."""
        self.data['last_updated'] = datetime.now().isoformat()
        with open(self.db_path, 'w') as f:
            json.dump(self.data, f, indent=2)
    
    def track_week(self, week_file, schedule_data, troops):
        """Track analytics for a completed week schedule."""
        week_name = Path(week_file).stem
        
        # Initialize week entry
        if week_name not in self.data['weeks']:
            self.data['weeks'][week_name] = {
                'schedules': [],
                'troop_count': 0,
                'total_activities': 0
            }
        
        # Track this schedule
        week_data = self.data['weeks'][week_name]
        week_data['troop_count'] = len(troops)
        week_data['total_activities'] = len(schedule_data['entries'])
        week_data['schedules'].append({
            'generated_at': schedule_data.get('generated_at'),
            'entry_count': len(schedule_data['entries'])
        })
        
        # Track activity statistics
        activity_counts = defaultdict(int)
        activity_priorities = defaultdict(list)
        
        for entry in schedule_data['entries']:
            activity = entry['activity']
            troop_name = entry['troop']
            
            # Count activity usage
            activity_counts[activity] += 1
            
            # Track priority (if available in preferences)
            troop =next((t for t in troops if t.name == troop_name), None)
            if troop:
                priority = troop.get_priority(activity)
                if priority is not None:
                    activity_priorities[activity].append(priority)
        
        # Update activity statistics
        for activity, count in activity_counts.items():
            if activity not in self.data['activities']:
                self.data['activities'][activity] = {
                    'total_requests': 0,
                    'total_scheduled': 0,
                    'avg_priority': 0.0,
                    'weeks': []
                }
            
            act_data = self.data['activities'][activity]
            act_data['total_scheduled'] += count
            act_data['weeks'].append(week_name)
            
            if activity_priorities[activity]:
                # Update average priority
                all_priorities = activity_priorities[activity]
                act_data['avg_priority'] = sum(all_priorities) / len(all_priorities)
        
        self._save_db()
    
    def get_activity_popularity(self):
        """Get list of activities sorted by popularity."""
        activities = []
        for name, data in self.data['activities'].items():
            activities.append({
                'name': name,
                'scheduled_count': data['total_scheduled'],
                'avg_priority': data['avg_priority'],
                'weeks_used': len(set(data['weeks']))
            })
        
        return sorted(activities, key=lambda x: x['scheduled_count'], reverse=True)
    
    def get_week_summary(self, week_name):
        """Get summary for a specific week."""
        if week_name in self.data['weeks']:
            return self.data['weeks'][week_name]
        return None
    
    def get_trend_report(self):
        """Generate trend analysis report."""
        lines = []
        lines.append("="*70)
        lines.append("HISTORICAL TREND ANALYSIS")
        lines.append("="*70)
        lines.append("")
        
        # Week summary
        lines.append(f"Total Weeks Analyzed: {len(self.data['weeks'])}")
        lines.append("")
        
        # Top 10 most popular activities
        lines.append("TOP 10 MOST POPULAR ACTIVITIES")
        lines.append("-"*70)
        popular = self.get_activity_popularity()[:10]
        for i, act in enumerate(popular, 1):
            lines.append(
                f"{i:2d}. {act['name']:30s} "
                f"({act['scheduled_count']:3d} times, avg priority: {act['avg_priority']:.1f})"
            )
        
        lines.append("")
        
        # Least popular activities
        lines.append("LEAST SCHEDULED ACTIVITIES")
        lines.append("-"*70)
        unpopular = self.get_activity_popularity()[-10:]
        for act in unpopular:
            if act['scheduled_count'] > 0:
                lines.append(
                    f"  {act['name']:30s} ({act['scheduled_count']:2d} times)"
                )
        
        lines.append("")
        lines.append("="*70)
        
        return "\n".join(lines)

def update_analytics_for_all_weeks():
    """Update analytics database with all week schedules."""
    import glob
    from io_handler import load_troops_from_json
    from schedule_cache import get_or_generate_schedule
    
    analytics = ScheduleAnalytics()
    
    week_files = glob.glob("tc_week*.json") + glob.glob("voyageur_week*.json")
    
    print("Updating analytics database...")
    for week_file in sorted(week_files):
        print(f"  Processing {week_file}...")
        troops = load_troops_from_json(week_file)
        schedule_data = get_or_generate_schedule(week_file)
        analytics.track_week(week_file, schedule_data, troops)
    
    print(f"✓ Analytics saved to {analytics.db_path}\n")
    
    # Print report
    print(analytics.get_trend_report())

if __name__ == "__main__":
    update_analytics_for_all_weeks()
