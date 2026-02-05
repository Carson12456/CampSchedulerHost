
import sys
from constrained_scheduler import ConstrainedScheduler
from io_handler import load_troops_from_json
from models import Day

def calculate_troop_score(troop, schedule_entries):
    """
    Calculate a comprehensive 'Happiness Score' for a troop.
    
    Components:
    1. Preference Satisfaction:
       - Top 1: 50 pts
       - Top 2: 40 pts
       - Top 3: 30 pts
       - Top 4: 20 pts
       - Top 5: 10 pts
       - Top 6-10: 5 pts
    2. Early Week Bonus (Super Troop/Delta):
       - Mon/Tue: +100 pts
       - Wed: +50 pts
       - Thu/Fri: 0 pts
    3. Clustering/Batching Bonus:
       - Consecutive slots (same day): +20 pts per pair
    """
    score = 0
    details = []
    
    # 1. Preferences
    scheduled_activities = {e.activity.name for e in schedule_entries}
    for i, pref in enumerate(troop.preferences):
        rank = i + 1
        if pref in scheduled_activities:
            if rank == 1: pts = 50
            elif rank == 2: pts = 40
            elif rank == 3: pts = 30
            elif rank == 4: pts = 20
            elif rank == 5: pts = 10
            elif rank <= 10: pts = 5
            else: pts = 1
            
            score += pts
            details.append(f"Preference #{rank} ({pref}): +{pts}")
            
    # 2. Early Week Bonus
    for e in schedule_entries:
        if e.activity.name in ["Super Troop", "Delta"]:
            if e.time_slot.day in [Day.MONDAY, Day.TUESDAY]:
                score += 100
                details.append(f"Early {e.activity.name} ({e.time_slot.day.name}): +100")
            elif e.time_slot.day == Day.WEDNESDAY:
                score += 50
                details.append(f"Mid-week {e.activity.name} ({e.time_slot.day.name}): +50")
            else:
                details.append(f"Late {e.activity.name} ({e.time_slot.day.name}): +0")

    # 3. Batching/Clustering (Consecutive slots)
    # Sort entries by day, slot
    sorted_entries = sorted(schedule_entries, key=lambda x: (x.time_slot.day.value, x.time_slot.slot_number))
    for i in range(len(sorted_entries) - 1):
        e1 = sorted_entries[i]
        e2 = sorted_entries[i+1]
        
        if e1.time_slot.day == e2.time_slot.day:
            if e2.time_slot.slot_number == e1.time_slot.slot_number + 1:
                # Consecutive!
                score += 20
                details.append(f"Cluster ({e1.activity.name} -> {e2.activity.name}): +20")
    
    return score, details

def run_analysis(filename, target_troops):
    print(f"\nAnalyzing {filename}...")
    troops = load_troops_from_json(filename)
    scheduler = ConstrainedScheduler(troops)
    scheduler.schedule_all()
    
    for troop_name in target_troops:
        troop = next((t for t in troops if t.name == troop_name), None)
        if not troop:
            print(f"Troop {troop_name} not found.")
            continue
            
        entries = [e for e in scheduler.schedule.entries if e.troop == troop]
        score, details = calculate_troop_score(troop, entries)
        
        print(f"\nTroop: {troop_name}")
        print(f"Total Score: {score}")
        print("Breakdown:")
        for d in details:
            print(f"  - {d}")

if __name__ == "__main__":
    import sys
    with open("score_report.txt", "w") as f:
        sys.stdout = f
        
        print("="*60)
        print("TROOP SCORE ANALYSIS (FOCUSED)")
        print("="*60)
        
        # Week 5 Analysis - Massasoit
        run_analysis("tc_week5_troops.json", ["Massasoit"])
        
        # Week 6 Analysis - Black Hawk
        run_analysis("tc_week6_troops.json", ["Black Hawk"])
