from io_handler import load_troops_from_json

troops = load_troops_from_json('tc_week7_troops.json')

print("Rifle/Shotgun priorities:")
for t in troops:
    rifle_pos = t.preferences.index("Troop Rifle") if "Troop Rifle" in t.preferences else None
    shotgun_pos = t.preferences.index("Troop Shotgun") if "Troop Shotgun" in t.preferences else None
    
    if rifle_pos is not None or shotgun_pos is not None:
        print(f"{t.name}:")
        if rifle_pos is not None:
            print(f"  Troop Rifle: position {rifle_pos} (Top {rifle_pos+1})")
        if shotgun_pos is not None:
            print(f"  Troop Shotgun: position {shotgun_pos} (Top {shotgun_pos+1})")
