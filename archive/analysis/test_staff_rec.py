from io_handler import load_troops_from_json
from constrained_scheduler import ConstrainedScheduler
from models import Day

# Import the Flask app to test the API function
import sys
sys.path.insert(0, r'c:\Users\Carson\Downloads\code\summer-camp-scheduler')

from gui_web import schedule

# Manually check what the API would return
troops = load_troops_from_json('tc_week7_troops.json')
scheduler = ConstrainedScheduler(troops)
generated_schedule = scheduler.schedule_all()

# Calculate staff requirements manually
print("CHECKING STAFF RECOMMENDATIONS:\n")

for day in [Day.TUESDAY]:
    for slot_num in [1]:
        print(f"\n{day.name}-{slot_num}:")
        
        # Count people in beach and tower activities
        beach_people = 0
        tower_people = 0
        beach_staff = 0
        tower_staff = 0
        
        for e in generated_schedule.entries:
            if e.time_slot.day == day and e.time_slot.slot_number == slot_num:
                total_people = e.troop.scouts + e.troop.adults
                
                if e.activity.name in ['Aqua Trampoline', 'Troop Canoe', 'Troop Kayak', 'Canoe Snorkel',
                                       'Float for Floats', 'Greased Watermelon', 'Underwater Obstacle Course',
                                       'Troop Swim', 'Water Polo']:
                    beach_people += total_people
                    beach_staff += 2
                    print(f"  Beach: {e.troop.name} ({e.activity.name}) - {total_people} people")
                
                elif e.activity.name == 'Climbing Tower':
                    tower_people += total_people
                    tower_staff += 2
                    print(f"  Tower: {e.troop.name} - {total_people} people")
        
        # Calculate recommendations
        beach_recommended = (beach_people + 9) // 10 if beach_people > 0 else 0
        tower_recommended = (tower_people + 5) // 6 if tower_people > 0 else 0
        
        print(f"\nBeach: {beach_people} people → {beach_staff} staff assigned, {beach_recommended} recommended")
        print(f"Tower: {tower_people} people → {tower_staff} staff assigned, {tower_recommended} recommended")
        print(f"Total: {beach_staff + tower_staff} staff assigned, {beach_recommended + tower_recommended} recommended")
