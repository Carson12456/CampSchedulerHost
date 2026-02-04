from io_handler import load_troops_from_json, save_troops_to_json
from models import Troop

# Load existing troops
troops = load_troops_from_json('tc_week5_troops.json')

# Add a large troop that needs splitting (30 scouts + 4 adults = 34 people)
large_troop_data = {
    'name': 'Crazy Horse',
    'campsite': 'CH',
    'preferences': [
        'Aqua Trampoline', 'Troop Swim', 'Climbing Tower', 'Archery/Tomahawks/Slingshots',
        'Greased Watermelon', 'Troop Rifle', 'Sailing', 'Gaga Ball', '9 Square', 'Water Polo',
        'Troop Shotgun', 'Reserve Shower House', 'Fishing', 'Tie Dye', 'Troop Canoe',
        'Reserve Trading Post', 'Canoe Snorkel', 'Campsite Time/Free Time', 'Orienteering', 'GPS & Geocaching'
    ],
    'scouts': 30,
    'adults': 4,
    'commissioner': 'A',
    'day_requests': {}
}

# Save to new test file with large troop
test_data = {
    'troops': [
        {'name': 'Tecumseh', 'campsite': 'TH', 'preferences': troops[0].preferences, 'scouts': 11, 'adults': 3, 'commissioner': 'A', 'day_requests': {}},
        {'name': 'Taskalusa', 'campsite': 'TK', 'preferences': troops[1].preferences, 'scouts': 6, 'adults': 1, 'commissioner': 'C', 'day_requests': {}},
        large_troop_data
    ]
}

import json
with open('test_split_troops.json', 'w') as f:
    json.dump(test_data, f, indent=2)

print("Created test_split_troops.json with large troop")
print("\nNow loading to test splitting:")
test_troops = load_troops_from_json('test_split_troops.json')
print(f"\nTotal troops after loading: {len(test_troops)}")
for t in test_troops:
    print(f"  {t.name:20s}: {t.scouts}/{t.adults} = {t.scouts + t.adults} people")
