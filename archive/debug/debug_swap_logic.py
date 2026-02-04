"""Debug why Samoset GPS swap didn't happen."""
from io_handler import load_troops_from_json
from constrained_scheduler import ConstrainedScheduler
from models import Day

troops = load_troops_from_json('tc_week7_troops.json')
scheduler = ConstrainedScheduler(troops)
schedule = scheduler.schedule_all()

# Find Samoset's entries
samoset = [t for t in troops if t.name == 'Samoset'][0]
samoset_entries = [e for e in schedule.entries if e.troop.name == 'Samoset']

print("\n=== SAMOSET FULL SCHEDULE ===")
for entry in sorted(samoset_entries, key=lambda x: (x.time_slot.day.value, x.time_slot.slot_number)):
    prio = samoset.preferences.index(entry.activity.name) + 1 if entry.activity.name in samoset.preferences else 'N/A'
    print(f"{entry.time_slot}: {entry.activity.name} (Pref #{prio})")

# Find GPS entry and 9 Square entry
gps_entry = next((e for e in samoset_entries if e.activity.name == "GPS & Geocaching"), None)
nine_square_entry = next((e for e in samoset_entries if e.activity.name == "9 Square"), None)

print(f"\n=== SWAP CANDIDATES ===")
print(f"GPS: {gps_entry.time_slot if gps_entry else 'N/A'}")
print(f"9 Square: {nine_square_entry.time_slot if nine_square_entry else 'N/A'}")

# Check ODS cluster days GLOBALLY
ods_activities = ["Knots and Lashings", "Orienteering", "GPS & Geocaching", 
                 "Ultimate Survivor", "What's Cooking", "Chopped!"]

print(f"\n=== ODS GLOBAL CLUSTERING ===")
from collections import defaultdict
by_day = defaultdict(int)
for entry in schedule.entries:
    if entry.activity.name in ods_activities:
        by_day[entry.time_slot.day] += 1

sorted_days = sorted(by_day.items(), key=lambda x: x[1], reverse=True)
print("Days sorted by ODS activity count:")
for day, count in sorted_days:
    print(f"  {day.name}: {count} activities")

print(f"\nTop 2 cluster days: {[d.name for d, c in sorted_days[:2]]}")
print(f"GPS is at: {gps_entry.time_slot.day.name if gps_entry else 'N/A'}")
print(f"9 Square is at: {nine_square_entry.time_slot.day.name if nine_square_entry else 'N/A'}")

# Check if swap would be beneficial
if gps_entry and nine_square_entry:
    gps_day = gps_entry.time_slot.day
    nine_sq_day = nine_square_entry.time_slot.day
    
    cluster_days = [d for d, c in sorted_days]
    
    print(f"\n=== SWAP ANALYSIS ===")
    print(f"GPS currently at {gps_day.name} (rank in ODS days: {cluster_days.index(gps_day)+1 if gps_day in cluster_days else 'N/A'})")
    print(f"9 Square at {nine_sq_day.name} (rank in ODS days: {cluster_days.index(nine_sq_day)+1 if nine_sq_day in cluster_days else 'N/A'})")
    
    top_2_cluster_days = cluster_days[:2] if len(cluster_days) >= 2 else cluster_days
    
    would_improve = (
        nine_sq_day in top_2_cluster_days and gps_day not in top_2_cluster_days
    )
    
    print(f"\nWould swap improve clustering? {would_improve}")
    print(f"  9 Square day ({nine_sq_day.name}) in top 2 cluster days? {nine_sq_day in top_2_cluster_days}")
    print(f"  GPS day ({gps_day.name}) NOT in top 2 cluster days? {gps_day not in top_2_cluster_days}")

# Check swappable activities classification
SWAPPABLE_ACTIVITIES = {
    "Gaga Ball", "9 Square", "Fishing", "Sauna",
    "Reserve Shower House", "Reserve Trading Post",
    "Campsite Time/Free Time"
}

print(f"\n=== ACTIVITY CLASSIFICATION ===")
print(f"GPS & Geocaching is swappable? {gps_entry.activity.name in SWAPPABLE_ACTIVITIES if gps_entry else 'N/A'}")
print(f"9 Square is swappable? {nine_square_entry.activity.name in SWAPPABLE_ACTIVITIES if nine_square_entry else 'N/A'}")
print(f"GPS & Geocaching is ODS activity? {gps_entry.activity.name in ods_activities if gps_entry else 'N/A'}")
