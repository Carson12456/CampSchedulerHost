"""
Enhanced GUI Routes for Commissioner Dashboard and Conflict Visualization (Items 10 & 11)
Adds new routes to gui_web.py for improved dashboard and conflict detection.
"""

# ===== ADD TO gui_web.py =====

# Commissioner Workload Dashboard (Item 10 Enhancement)
@app.route('/api/commissioner_workload/<commissioner>')
def get_commissioner_workload(commissioner):
    """Get detailed workload data for a commissioner."""
    schedule_data = _get_schedule_data()
    
    # Group activities by day and slot
    workload = {}
    for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
        workload[day] = {1: [], 2: [], 3: []}
    
    for entry in schedule_data['entries']:
        # Check if this is a commissioner-led activity
        activity = entry['activity']
        if activity in ['Archery', 'Delta', 'Super Troop', 'Reflection']:
            day = entry['day']
            slot = entry['slot']
            troop = entry['troop']
            
            # Check if this troop belongs to this commissioner
            troop_obj = next((t for t in schedule_data['troops'] if t['name'] == troop), None)
            if troop_obj and troop_obj.get('commissioner') == commissioner:
                workload[day][slot].append({
                    'activity': activity,
                    'troop': troop,
                    'scouts': troop_obj.get('scouts', 10)
                })
    
    # Calculate stats
    total_activities = sum(len(workload[day][slot]) for day in workload for slot in workload[day])
    busiest_slot = max(
        [(day, slot, len(workload[day][slot])) for day in workload for slot in workload[day]],
        key=lambda x: x[2]
    )
    
    return jsonify({
        'commissioner': commissioner,
        'workload': workload,
        'total_activities': total_activities,
        'busiest_slot': {
            'day': busiest_slot[0],
            'slot': busiest_slot[1],
            'count': busiest_slot[2]
        }
    })

# Conflict Visualization (Item 11)
@app.route('/api/conflicts')
def get_conflicts():
    """Detect and return all scheduling conflicts and warnings."""
    schedule_data = _get_schedule_data()
    
    conflicts = {
        'errors': [],  # Hard constraint violations
        'warnings': [],  # Soft constraint violations
        'capacity_issues': []
    }
    
    # Check beach slot constraint
    BEACH_ACTS = ['Water Polo', 'Greased Watermelon', 'Aqua Trampoline']
    for entry in schedule_data['entries']:
        if entry['activity'] in BEACH_ACTS:
            if entry['day'] != 'Tuesday' and entry['slot'] == 2:
                conflicts['errors'].append({
                    'type': 'beach_slot_violation',
                    'troop': entry['troop'],
                    'activity': entry['activity'],
                    'day': entry['day'],
                    'slot': entry['slot'],
                    'message': f"{entry['activity']} in slot 2 on {entry['day']} (should be 1 or 3)"
                })
    
    # Check capacity - Beach staff
    from collections import defaultdict
    slot_staff = defaultdict(int)
    BEACH_STAFFED = ['Aqua Trampoline', 'Troop Canoe', 'Water Polo', 'Greased Watermelon', 'Troop Swim']
    
    for entry in schedule_data['entries']:
        if entry['activity'] in BEACH_STAFFED:
            key = (entry['day'], entry['slot'])
            slot_staff[key] += 2  # Each activity needs 2 staff
    
    for (day, slot), staff_needed in slot_staff.items():
        if staff_needed > 12:
            conflicts['capacity_issues'].append({
                'type': 'beach_staff_overload',
                'day': day,
                'slot': slot,
                'staff_needed': staff_needed,
                'max_staff': 12,
                'message': f"{day} slot {slot}: {staff_needed} beach staff needed (max 12)"
            })
    
    # Check accuracy limit
    from collections import defaultdict
    troop_day_accuracy = defaultdict(lambda: defaultdict(set))
    ACCURACY = ['Troop Rifle', 'Troop Shotgun', 'Archery']
    
    for entry in schedule_data['entries']:
        if entry['activity'] in ACCURACY:
            troop_day_accuracy[entry['troop']][entry['day']].add(entry['activity'])
    
    for troop, days in troop_day_accuracy.items():
        for day, activities in days.items():
            if len(activities) > 1:
                conflicts['errors'].append({
                    'type': 'accuracy_limit_violation',
                    'troop': troop,
                    'day': day,
                    'activities': list(activities),
                    'message': f"{troop}: {len(activities)} accuracy activities on {day}"
                })
    
    return jsonify(conflicts)

# Conflict Heatmap Data
@app.route('/api/conflict_heatmap')
def get_conflict_heatmap():
    """Generate heatmap data for conflict visualization."""
    schedule_data = _get_schedule_data()
    
    # Create grid: days x slots
    heatmap = {}
    for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
        heatmap[day] = {1: 0, 2: 0, 3: 0}
    
    # Count activities per slot (load indicator)
    for entry in schedule_data['entries']:
        heatmap[entry['day']][entry['slot']] += 1
    
    # Normalize and categorize
    max_load = max(heatmap[day][slot] for day in heatmap for slot in heatmap[day])
    
    for day in heatmap:
        for slot in heatmap[day]:
            load = heatmap[day][slot]
            # Categorize: 0 = empty, 1-3 = low, 4-6 = medium, 7+ = high
            if load == 0:
                category = 'empty'
            elif load <= 3:
                category = 'low'
            elif load <= 6:
                category = 'medium'
            else:
                category = 'high'
            
            heatmap[day][slot] = {
                'load': load,
                'category': category,
                'percentage': (load / max_load * 100) if max_load > 0 else 0
            }
    
    return jsonify({'heatmap': heatmap, 'max_load': max_load})
