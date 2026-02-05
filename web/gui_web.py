"""
Web-based GUI for Summer Camp Scheduler using Flask.
This generates an HTML interface that properly displays 1.5-slot activities.
yaya
"""
from flask import Flask, render_template, send_from_directory, request, jsonify
from pathlib import Path
import json
import sys

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from core.models import Day, TimeSlot, generate_time_slots, ScheduleEntry, Troop, Schedule
from core.activities import get_all_activities
from core.io_handler import load_troops_from_json, save_schedule_to_json
from core.constrained_scheduler import ConstrainedScheduler

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
SCRIPT_DIR = Path(__file__).parent.resolve()

# Disable browser caching on API responses
@app.after_request
def add_header(response):
    if request.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response


# Load schedules from JSON cache or generate if needed
print("Loading schedules...")

SCHEDULES_DIR = SCRIPT_DIR.parent / "data/schedules"
WEEK_DATA = {}
activities = get_all_activities()
time_slots = generate_time_slots()

def load_schedule_from_json(schedule_file):
    """Load a cached schedule from JSON with enhanced error handling."""
    try:
        with open(schedule_file, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Schedule file not found: {schedule_file}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in schedule file {schedule_file}: {e}")
    except Exception as e:
        raise RuntimeError(f"Error reading schedule file {schedule_file}: {e}")
    
    # Validate required fields
    required_fields = ['troops', 'entries']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        raise ValueError(f"Missing required fields in schedule file: {missing_fields}")
    
    # Reconstruct troops from JSON with validation
    troops = []
    for t_data in data['troops']:
        try:
            troop = Troop(
                name=t_data['name'],
                scouts=t_data['scouts'],
                adults=t_data['adults'],
                campsite=t_data.get('campsite', t_data['name']),
                commissioner=t_data.get('commissioner'),
                preferences=t_data.get('preferences', []),
                day_requests=t_data.get('day_requests', {})
            )
            troops.append(troop)
        except Exception as e:
            raise ValueError(f"Invalid troop data in schedule file: {e}")
    
    # Reconstruct schedule from entries with validation
    schedule = Schedule()
    
    # Create a mapping of troop names to troop objects
    troop_map = {t.name: t for t in troops}
    activity_map = {a.name: a for a in activities}
    slot_map = {}
    for ts in time_slots:
        slot_map[(ts.day.name, ts.slot_number)] = ts
    
    for entry_data in data['entries']:
        try:
            troop = troop_map.get(entry_data['troop_name'])
            activity = activity_map.get(entry_data['activity_name'])
            time_slot = slot_map.get((entry_data['day'], entry_data['slot']))
            
            if not troop or not activity or not time_slot:
                # If any data is invalid/missing, raise error to force regeneration
                # This handles cases where activities were renamed or removed
                missing = []
                if not troop: missing.append(f"Troop: {entry_data.get('troop_name')}")
                if not activity: missing.append(f"Activity: {entry_data.get('activity_name')}")
                if not time_slot: missing.append(f"Slot: {entry_data.get('day')}-{entry_data.get('slot')}")
                raise ValueError(f"Invalid schedule entry data: {', '.join(missing)}")
                
            entry = ScheduleEntry(time_slot, activity, troop)
            schedule.entries.append(entry)
        except Exception as e:
            raise ValueError(f"Error processing schedule entry: {e}")
            
    unscheduled = data.get('unscheduled', {})
    
    return troops, schedule, unscheduled

def generate_schedule(troops_file):
    """Generate schedule from troops file (fallback)."""
    print(f"  Generating schedule from {troops_file.name}...")
    troops = load_troops_from_json(troops_file)
    voyageur_mode = "voyageur" in troops_file.name.lower()
    scheduler = ConstrainedScheduler(troops, activities, voyageur_mode=voyageur_mode)
    schedule = scheduler.schedule_all()
    
    # Calculate unscheduled activities
    unscheduled_data = {}
    # HC/DG exemption: if all 3 Tuesday slots are HC or DG, troops who missed HC/DG get exempt
    tuesday_hc_dg_slots = set()
    for e in schedule.entries:
        if e.time_slot.day == Day.TUESDAY and e.activity.name in ("History Center", "Disc Golf"):
            tuesday_hc_dg_slots.add(e.time_slot.slot_number)
    hc_dg_tuesday_full = tuesday_hc_dg_slots >= {1, 2, 3}

    for troop in scheduler.troops:
        troop_schedule = schedule.get_troop_schedule(troop)
        scheduled_activity_names = {e.activity.name for e in troop_schedule}
        
        missing_top5 = []
        # Check if troop has ANY 3-hour activity scheduled
        has_3hr_scheduled = any(name in ConstrainedScheduler.THREE_HOUR_ACTIVITIES for name in scheduled_activity_names)
        
        for i, pref in enumerate(troop.preferences[:5]):
            if pref not in scheduled_activity_names:
                is_exempt = False
                if pref in ConstrainedScheduler.THREE_HOUR_ACTIVITIES and has_3hr_scheduled:
                    is_exempt = True
                elif pref in ("History Center", "Disc Golf") and hc_dg_tuesday_full:
                    is_exempt = True  # All 3 Tuesday slots given to troops who wanted it more
                missing_top5.append({'name': pref, 'rank': i+1, 'is_exempt': is_exempt})
                
        missing_top10 = []
        for i, pref in enumerate(troop.preferences[5:10]):
            if pref not in scheduled_activity_names:
                is_exempt = False
                if pref in ConstrainedScheduler.THREE_HOUR_ACTIVITIES and has_3hr_scheduled:
                    is_exempt = True
                elif pref in ("History Center", "Disc Golf") and hc_dg_tuesday_full:
                    is_exempt = True
                missing_top10.append({'name': pref, 'rank': i+6, 'is_exempt': is_exempt})
                
        if missing_top5 or missing_top10:
            unscheduled_data[troop.name] = {
                'top5': missing_top5,
                'top10': missing_top10
            }
            
    # vital: return scheduler.troops because they might have been split
    return scheduler.troops, schedule, unscheduled_data

# Auto-discover all troop files (LAZY LOADING - only get names, don't load yet)
print("Discovering available weeks...")
troop_files = sorted((SCRIPT_DIR.parent / "data/troops").glob("*.json"))

# Just store metadata, not actual schedules
WEEK_METADATA = {}
for troops_file in troop_files:
    week_id = troops_file.stem
    
    # Determine display name
    if week_id.startswith('tc_week'):
        week_num = week_id.replace('tc_week', '').replace('_troops', '')
        week_number = f'TC Week {week_num}'
    elif week_id.startswith('voyageur_week'):
        week_num = week_id.replace('voyageur_week', '').replace('_troops', '')
        week_number = f'Voyageur Week {week_num}'
    else:
        week_number = week_id.replace('_troops', '').replace('_', ' ').title()
    
    WEEK_METADATA[week_id] = {
        'week_number': week_number,
        'file': troops_file,
        'loaded': False  # Flag for lazy loading
    }

# In-memory cache for loaded weeks (populated on-demand)
WEEK_DATA = {}
# Performance optimization: Pre-warm cache for commonly used weeks
PREWARM_WEEKS = ['tc_week1_troops', 'tc_week2_troops', 'tc_week3_troops']

def get_week_data(week_id):
    """Lazy load a week's data on demand, with cache invalidation."""
    if week_id not in WEEK_METADATA:
        return None
    
    meta = WEEK_METADATA[week_id]
    troops_file = meta['file']
    schedule_file = SCHEDULES_DIR / f"{week_id}_schedule.json"
    
    # Check if cache needs invalidation (schedule file was modified)
    if week_id in WEEK_DATA:
        cached_mtime = WEEK_DATA[week_id].get('_mtime', 0)
        if schedule_file.exists():
            current_mtime = schedule_file.stat().st_mtime
            if current_mtime > cached_mtime:
                print(f"  Cache invalidated for {week_id} (file updated)")
                del WEEK_DATA[week_id]
    
    if week_id in WEEK_DATA:
        return WEEK_DATA[week_id]
    
    print(f"Loading {week_id} on demand...")
    
    # Try cache first with better error handling
    schedule_mtime = 0
    unscheduled_data = {}
    
    if schedule_file.exists():
        try:
            troops, schedule, unscheduled_data = load_schedule_from_json(schedule_file)
            schedule_mtime = schedule_file.stat().st_mtime
            print(f"  Loaded from cache")
        except Exception as e:
            print(f"  Cache failed: {e}, regenerating...")
            try:
                troops, schedule, unscheduled_data = generate_schedule(troops_file)
            except Exception as e2:
                print(f"  Schedule generation failed: {e2}")
                # Return empty data rather than crashing
                return {
                    'troops': [],
                    'schedule': Schedule(),
                    'unscheduled': {},
                    'week_number': meta['week_number'],
                    'file': troops_file.name,
                    '_mtime': 0,
                    'error': str(e2)
                }
    else:
        try:
            print(f"  Generating fresh schedule...")
            troops, schedule, unscheduled_data = generate_schedule(troops_file)
        except Exception as e:
            print(f"  Schedule generation failed: {e}")
            # Return empty data rather than crashing
            return {
                'troops': [],
                'schedule': Schedule(),
                'unscheduled': {},
                'week_number': meta['week_number'],
                'file': troops_file.name,
                '_mtime': 0,
                'error': str(e)
            }
    
    WEEK_DATA[week_id] = {
        'troops': troops,
        'schedule': schedule,
        'unscheduled': unscheduled_data,
        'week_number': meta['week_number'],
        'file': troops_file.name,
        '_mtime': schedule_mtime  # Track file modification time
    }
    meta['loaded'] = True
    
    return WEEK_DATA[week_id]


# Default week (don't load yet, just set the name)
available_weeks = list(WEEK_METADATA.keys())
current_week = 'tc_week1_troops' if 'tc_week1_troops' in WEEK_METADATA else (available_weeks[0] if available_weeks else None)

print(f"Discovered {len(WEEK_METADATA)} week(s): {available_weeks}")
print("Schedules will load on-demand when selected.")

# Performance optimization: Pre-warm cache for commonly used weeks
print("Pre-warming cache for common weeks...")
for week_id in PREWARM_WEEKS:
    if week_id in WEEK_METADATA:
        print(f"  Pre-warming {week_id}...")
        get_week_data(week_id)
print("Cache pre-warming complete.")


@app.route('/')
def index():
    """Main page with schedule viewer."""
    week = request.args.get('week', current_week)
    if week not in WEEK_METADATA:
        week = current_week
    
    # Lazy load the selected week
    data = get_week_data(week)
    if not data:
        return "No weeks available", 404
    
    # Create week_data mapping for dropdown display (use metadata, not loaded data)
    week_data_display = {week_id: meta['week_number'] for week_id, meta in WEEK_METADATA.items()}
    
    return render_template('index.html', 
                         troops=data['troops'],
                         time_slots=time_slots,
                         week_number=data['week_number'],
                         available_weeks=available_weeks,
                         current_week=week,
                         week_data=week_data_display)

@app.route('/api/weeks')
def get_weeks():
    """Get list of available weeks."""
    return jsonify({
        'weeks': [{'key': k, 'name': v['week_number']} for k, v in WEEK_METADATA.items()],
        'current': current_week
    })


@app.route('/api/evaluation/<week_id>')
def get_evaluation(week_id):
    """Return evaluation metrics for a week (score, violations, exclusive double-book, beach slot 2, schedule invalid)."""
    if week_id not in WEEK_METADATA:
        return jsonify({'error': 'Week not found'}), 404
    try:
        from utils.evaluate_week_success import evaluate_week
        meta = WEEK_METADATA[week_id]
        troops_file = meta['file']
        # evaluate_week expects filename like tc_week5_troops.json (relative or absolute)
        week_file_path = str(troops_file)
        metrics = evaluate_week(week_file_path)
        return jsonify({
            'final_score': metrics.get('final_score', 0),
            'constraint_violations': metrics.get('constraint_violations', 0),
            'exclusive_double_book': metrics.get('exclusive_double_book', 0),
            'beach_slot_2_uses': metrics.get('beach_slot_2_uses', 0),
            'schedule_invalid': metrics.get('schedule_invalid', False),
            'missing_top5': metrics.get('missing_top5', 0),
            'top5_pct': metrics.get('top5_pct', 0),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/regenerate/<week_id>', methods=['POST'])
def regenerate_week(week_id):
    """Force regenerate a week's schedule (deletes cache and recreates)."""
    if week_id not in WEEK_METADATA:
        return jsonify({'error': 'Week not found'}), 404
    
    meta = WEEK_METADATA[week_id]
    troops_file = meta['file']
    schedule_file = SCHEDULES_DIR / f"{week_id}_schedule.json"
    
    # Delete cached schedule if exists
    if schedule_file.exists():
        import os
        os.remove(schedule_file)
        print(f"Deleted cached schedule: {schedule_file}")
    
    # Clear from memory cache
    if week_id in WEEK_DATA:
        del WEEK_DATA[week_id]
    meta['loaded'] = False
    
    # Regenerate schedule
    print(f"Regenerating schedule for {week_id}...")
    troops, schedule, unscheduled_data = generate_schedule(troops_file)
    
    # Save to cache using io_handler
    save_schedule_to_json(schedule, troops, str(schedule_file), unscheduled_data)
    
    # Update memory cache
    WEEK_DATA[week_id] = {
        'troops': troops,
        'schedule': schedule,
        'unscheduled': unscheduled_data,
        'week_number': meta['week_number'],
        'file': troops_file.name
    }
    meta['loaded'] = True
    
    return jsonify({'success': True, 'week': week_id, 'entries': len(schedule.entries)})


# def save_schedule_to_json(week_id, troops, schedule):
#     """Removed in favor of io_handler.save_schedule_to_json"""
#     pass

@app.route('/api/schedule/<troop_name>')
def get_troop_schedule(troop_name):
    """Get schedule for a specific troop as JSON with enhanced error handling."""
    week = request.args.get('week', current_week)
    if week not in WEEK_METADATA:
        week = current_week
    
    try:
        data = get_week_data(week)
        if not data:
            return {"error": "Week data not available"}, 404
        
        troops = data['troops']
        schedule = data['schedule']
        
        troop = next((t for t in troops if t.name == troop_name), None)
        if not troop:
            return {"error": "Troop not found"}, 404
        
        entries = schedule.get_troop_schedule(troop)
        
        # Group by day and slot
        schedule_grid = {}
        for day in Day:
            schedule_grid[day.name] = {1: None, 2: None, 3: None}
        
        for entry in entries:
            day_name = entry.time_slot.day.name
            slot_num = entry.time_slot.slot_number
            
            # Check if this is a continuation
            is_continuation = False
            for other_entry in entries:
                if (other_entry.activity.name == entry.activity.name and 
                    other_entry.time_slot.day == entry.time_slot.day and
                    other_entry.time_slot.slot_number < slot_num):
                    is_continuation = True
                    break
            
            # Detect spillovers (Delta/Super Troop not on designated commissioner days)
            is_spillover = False
            if entry.activity.name in ['Delta', 'Super Troop']:
                commissioner = troop.commissioner
                if commissioner:
                    # Get designated day for this activity and commissioner
                    if entry.activity.name == 'Delta':
                        designated_days = {
                            'Commissioner A': Day.MONDAY,
                            'Commissioner B': Day.TUESDAY,
                            'Commissioner C': Day.WEDNESDAY
                        }
                    else:  # Super Troop
                        designated_days = {
                            'Commissioner A': Day.TUESDAY,
                            'Commissioner B': Day.WEDNESDAY,
                            'Commissioner C': Day.THURSDAY
                        }
                    
                    designated_day = designated_days.get(commissioner)
                    if designated_day and entry.time_slot.day != designated_day:
                        is_spillover = True
            
            schedule_grid[day_name][slot_num] = {
                'activity': entry.activity.name,
                'is_continuation': is_continuation,
                'is_spillover': is_spillover,
                'priority': troop.get_priority(entry.activity.name),
                'zone': entry.activity.zone.name if entry.activity.zone else None,
                'slots': entry.activity.slots  # Add slots information for multi-slot display
            }
        
        return jsonify({
            'troop': troop_name,
            'commissioner': troop.commissioner,
            'schedule': schedule_grid,
            'preferences': troop.preferences,
            'exemptions': []  # TODO: Calculate exemptions if needed
        })
        
    except Exception as e:
        print(f"Error getting troop schedule for {troop_name}: {e}")
        return {"error": f"Internal server error: {str(e)}"}, 500

@app.route('/api/area/<path:area_name>')
def get_area_schedule(area_name):
    week = request.args.get('week', current_week)
    if week not in WEEK_METADATA:
        week = current_week
    data = get_week_data(week)
    schedule = data['schedule']
    
    # Map area names to activity names
    area_to_activities = {
        'Boats': ['Troop Canoe', 'Troop Kayak', 'Canoe Snorkel', 'Nature Canoe', 'Float for Floats'],
        'Sailing': ['Sailing'],
        'Handicrafts': ['Tie Dye', 'Hemp Craft', 'Woggle Neckerchief Slide', 'Monkey\'s Fist'],
        'Delta': ['Delta'],
        'Super Troop': ['Super Troop'],
        'Tower/Climbing': ['Climbing Tower'],
        'Rifle Range': ['Troop Rifle', 'Troop Shotgun'],
        'Archery': ['Archery'],
        'Outdoor Skills': ['Knots and Lashings', 'Orienteering', 
                          'GPS & Geocaching', 'Ultimate Survivor',
                          'What\'s Cooking', 'Chopped!'],
        'Off-Camp': ['Disc Golf', 'Tamarac Wildlife Refuge', 'Itasca State Park', 'History Center'],
        'Nature Center': ['Dr. DNA', 'Loon Lore', 'Ecosystem in a Jar', 'Nature Salad', 'Nature Bingo'],
        'Campsite': ['Campsite Free Time'],
        'Reserves': ['Trading Post', 'Shower House'],
        'Reflection': ['Reflection']
    }
    
    # Find activities for this area
    area_activities = area_to_activities.get(area_name, [])
    
    if not area_activities:
        # Try to match by zone name
        area_activities = [a.name for a in activities if a.zone.name.replace('_', ' ').replace('/', ' ').upper() == area_name.replace('/', ' ').upper()]
    
    if not area_activities:
        return {"error": f"Area not found: {area_name}"}, 404
    
    # Special handling for Sailing: show 2 staggered 1.5-slot sessions per day
    if area_name == 'Sailing':
        sailing_grid = {}
        for day in Day:
            sailing_grid[day.name] = {
                'session1': {'slots': '1-2', 'troops': []},  # Slot 1 + half of Slot 2
                'session2': {'slots': '2-3', 'troops': []}   # Slot 2 + half of Slot 3
            }
        
        # Find all sailing entries (only the starting slot, not continuations)
        for entry in schedule.entries:
            if entry.activity.name == 'Sailing':
                day_name = entry.time_slot.day.name
                slot_num = entry.time_slot.slot_number
                
                # Check if this is a starting slot (not continuation)
                is_start = True
                for other_entry in schedule.entries:
                    if (other_entry.activity.name == 'Sailing' and 
                        other_entry.troop == entry.troop and
                        other_entry.time_slot.day == entry.time_slot.day and
                        other_entry.time_slot.slot_number < slot_num):
                        is_start = False
                        break
                
                if is_start:
                    if slot_num == 1:
                        sailing_grid[day_name]['session1']['troops'].append(entry.troop.name)
                    elif slot_num == 2:
                        sailing_grid[day_name]['session2']['troops'].append(entry.troop.name)
        
        return sailing_grid
    
    # Regular area handling
    schedule_grid = {}
    for day in Day:
        schedule_grid[day.name] = {1: [], 2: [], 3: []}
    
    # Filter entries once for efficiency
    area_entries = [e for e in schedule.entries if e.activity.name in area_activities]
    
    for entry in area_entries:
        day_name = entry.time_slot.day.name
        slot_num = entry.time_slot.slot_number
        
        # Calculate preference satisfaction for this troop
        troop = entry.troop
        troop_entries = [e for e in schedule.entries if e.troop == troop]
        scheduled_activities = {e.activity.name for e in troop_entries}
        prefs_achieved = sum(1 for p in troop.preferences if p in scheduled_activities)
        prefs_total = len(troop.preferences)
        
        schedule_grid[day_name][slot_num].append({
            'troop': entry.troop.name,
            'activity': entry.activity.name,
            'priority': entry.troop.get_priority(entry.activity.name),
            'scouts': entry.troop.scouts,
            'adults': entry.troop.adults,
            'prefs_achieved': prefs_achieved,
            'prefs_total': prefs_total
        })
    
    return schedule_grid

@app.route('/api/commissioner/<commissioner_name>')
def get_commissioner_schedule(commissioner_name):
    """Get schedule for a specific commissioner as JSON."""
    week = request.args.get('week', current_week)
    if week not in WEEK_METADATA:
        week = current_week
    data = get_week_data(week)
    schedule = data['schedule']
    
    # Build COMMISSIONER_TROOPS dynamically from actual troop data (supports TC and Voyageur)
    troops = data['troops']
    COMMISSIONER_TROOPS = {}
    for troop in troops:
        comm = troop.commissioner if hasattr(troop, 'commissioner') else getattr(troop, 'commissioner', None)
        if comm:
            if comm not in COMMISSIONER_TROOPS:
                COMMISSIONER_TROOPS[comm] = []
            COMMISSIONER_TROOPS[comm].append(troop.name)
    
    # Fallback for TC if no commissioner data
    if not COMMISSIONER_TROOPS:
        COMMISSIONER_TROOPS = {
            "Commissioner A": ["Tecumseh", "Red Cloud", "Massasoit", "Joseph"],
            "Commissioner B": ["Tamanend", "Samoset", "Black Hawk"],
            "Commissioner C": ["Taskalusa", "Powhatan", "Cochise"]
        }
    
    # Day assignments - support both TC and Voyageur
    COMMISSIONER_DELTA_DAYS = {
        "Commissioner A": Day.MONDAY, "Commissioner B": Day.TUESDAY, "Commissioner C": Day.WEDNESDAY,
        "Voyageur A": Day.TUESDAY, "Voyageur B": Day.WEDNESDAY, "Voyageur C": Day.THURSDAY
    }
    
    COMMISSIONER_SUPER_TROOP_DAYS = {
        "Commissioner A": Day.TUESDAY, "Commissioner B": Day.WEDNESDAY, "Commissioner C": Day.THURSDAY,
        "Voyageur A": Day.TUESDAY, "Voyageur B": Day.WEDNESDAY, "Voyageur C": Day.THURSDAY
    }
    
    # Build commissioner activity day ownership with SINGLE-ACTIVITY-PER-DAY constraint
    # Each commissioner can only run ONE activity type per day
    from collections import defaultdict
    DAY_ARCHERY_OWNER = {}
    DAY_SUPER_TROOP_OWNER = {}
    DAY_DELTA_OWNER = {}
    
    # Track which commissioner is assigned to which day (one activity type max per day per comm)
    commissioner_day_activity = defaultdict(dict)  # {commissioner: {day: activity_type}}
    
    # For each day, assign activities to commissioners
    for day in Day:
        # Collect all activities on this day with their preferred commissioner (majority)
        day_activities = []
        
        for activity_name, owner_dict in [("Archery", DAY_ARCHERY_OWNER), ("Super Troop", DAY_SUPER_TROOP_OWNER), ("Delta", DAY_DELTA_OWNER)]:
            comm_counts = defaultdict(int)
            for entry in schedule.entries:
                if entry.time_slot.day == day and entry.activity.name == activity_name:
                    troop_comm = None
                    for comm, troop_list in COMMISSIONER_TROOPS.items():
                        if entry.troop.name in troop_list:
                            troop_comm = comm
                            break
                    if troop_comm:
                        comm_counts[troop_comm] += 1
            
            if comm_counts:
                preferred_comm = max(comm_counts, key=comm_counts.get)
                slot_count = sum(comm_counts.values())
                day_activities.append({
                    'activity': activity_name,
                    'owner_dict': owner_dict,
                    'preferred_comm': preferred_comm,
                    'comm_counts': dict(comm_counts),
                    'slot_count': slot_count
                })
        
        # Sort by activity count (more activities = higher priority for preferred comm)
        day_activities.sort(key=lambda x: x['slot_count'], reverse=True)
        
        # Assign each activity on this day to a commissioner
        for activity_info in day_activities:
            preferred_comm = activity_info['preferred_comm']
            comm_counts = activity_info['comm_counts']
            owner_dict = activity_info['owner_dict']
            
            # Check if preferred commissioner is available for this day
            if day not in commissioner_day_activity[preferred_comm]:
                # Available! Assign to preferred commissioner
                assigned_comm = preferred_comm
            else:
                # Preferred commissioner already has an activity on this day
                # Find an alternative commissioner
                assigned_comm = None
                
                # Try other commissioners that have troops in this activity
                for alt_comm in sorted(comm_counts.keys(), key=lambda c: comm_counts[c], reverse=True):
                    if alt_comm != preferred_comm and day not in commissioner_day_activity[alt_comm]:
                        assigned_comm = alt_comm
                        break
                
                # If still no assignment, try any available commissioner
                if not assigned_comm:
                    for alt_comm in COMMISSIONER_TROOPS.keys():
                        if day not in commissioner_day_activity[alt_comm]:
                            assigned_comm = alt_comm
                            break
                
                # Last resort: use preferred anyway
                if not assigned_comm:
                    assigned_comm = preferred_comm
            
            # Record the assignment
            commissioner_day_activity[assigned_comm][day] = activity_info['activity']
            owner_dict[day] = assigned_comm
    
    # Fallback: If no activities scheduled, use static assignments
    COMMISSIONER_ARCHERY_DAYS = {
        "Commissioner A": Day.WEDNESDAY, "Commissioner B": Day.FRIDAY, "Commissioner C": Day.MONDAY,
        "Voyageur A": Day.WEDNESDAY, "Voyageur B": Day.FRIDAY, "Voyageur C": Day.MONDAY
    }
    
    # Commissioner D / Comm Spare shows commissioner activities that need EXTRA coverage
    # This happens when the designated commissioner for a day/activity is already busy
    # with their OWN troops during that slot
    if commissioner_name in ["Commissioner D", "Comm Spare"]:
        schedule_grid = {}
        for day in Day:
            schedule_grid[day.name] = {1: [], 2: [], 3: []}
        
        COMMISSIONER_ACTIVITIES = ["Delta", "Archery", "Super Troop", "Reflection"]
        
        # Build a map of day -> which commissioner runs activities that day
        DAY_TO_COMMISSIONER = {
            # Delta days
            Day.MONDAY: "Commissioner A",    # A runs Delta on Monday
            Day.TUESDAY: "Commissioner B",   # B runs Delta on Tuesday
            Day.WEDNESDAY: "Commissioner C", # C runs Delta on Wednesday
        }
        
        # For each time slot, find if the designated commissioner is double-booked
        for day in Day:
            for slot_num in [1, 2, 3]:
                if day == Day.THURSDAY and slot_num == 3:
                    continue
                
                # Find all commissioner activities in this slot
                slot_comm_activities = []
                for entry in schedule.entries:
                    if (entry.time_slot.day == day and 
                        entry.time_slot.slot_number == slot_num and
                        entry.activity.name in COMMISSIONER_ACTIVITIES):
                        
                        # Find troop's commissioner
                        troop_comm = None
                        for comm, troop_list in COMMISSIONER_TROOPS.items():
                            if entry.troop.name in troop_list:
                                troop_comm = comm
                                break
                        
                        slot_comm_activities.append({
                            'entry': entry,
                            'troop_commissioner': troop_comm
                        })
                
                if len(slot_comm_activities) <= 1:
                    # Only 0 or 1 commissioner activity - no conflict, no D needed
                    continue
                
                # Multiple commissioner activities in same slot - check for conflicts
                # Group by which commissioner would run this based on activity + day
                running_commissioners = {}
                
                for item in slot_comm_activities:
                    entry = item['entry']
                    troop_comm = item['troop_commissioner']
                    activity_name = entry.activity.name
                    
                    # Determine which commissioner SHOULD run this
                    if activity_name == "Delta":
                        runner = DAY_TO_COMMISSIONER.get(day)
                    elif activity_name == "Super Troop":
                        # Super Troop: A on Tue, B on Wed, C on Thu
                        if day == Day.TUESDAY:
                            runner = "Commissioner A"
                        elif day == Day.WEDNESDAY:
                            runner = "Commissioner B"
                        elif day == Day.THURSDAY:
                            runner = "Commissioner C"
                        else:
                            runner = None
                    elif activity_name == "Archery":
                        # Archery: A on Wed, B on Fri, C on Mon
                        if day == Day.WEDNESDAY:
                            runner = "Commissioner A"
                        elif day == Day.FRIDAY:
                            runner = "Commissioner B"
                        elif day == Day.MONDAY:
                            runner = "Commissioner C"
                        else:
                            runner = None
                    elif activity_name == "Reflection":
                        # All commissioners run their own on Friday
                        runner = troop_comm
                    else:
                        runner = None
                    
                    if runner:
                        if runner not in running_commissioners:
                            running_commissioners[runner] = []
                        running_commissioners[runner].append(item)
                
                # Check if any commissioner has MORE than one activity to run
                # If so, the extras need Comm D coverage
                for comm, activities in running_commissioners.items():
                    if len(activities) > 1:
                        # This commissioner is double-booked
                        # First activity they handle themselves, rest go to Comm D
                        for extra in activities[1:]:
                            entry = extra['entry']
                            schedule_grid[day.name][slot_num].append({
                                'troop': entry.troop.name,
                                'activity': entry.activity.name,
                                'borrowed': False,
                                'covers_for': comm
                            })
        
        return schedule_grid

    
    if commissioner_name not in COMMISSIONER_TROOPS:
        return {"error": "Commissioner not found"}, 404
    
    assigned_troops = COMMISSIONER_TROOPS[commissioner_name]
    delta_day = COMMISSIONER_DELTA_DAYS[commissioner_name]
    archery_day = COMMISSIONER_ARCHERY_DAYS[commissioner_name]
    st_day = COMMISSIONER_SUPER_TROOP_DAYS[commissioner_name]
    
    # Group by day and slot
    schedule_grid = {}
    for day in Day:
        schedule_grid[day.name] = {1: [], 2: [], 3: []}
    
    # First, add this commissioner's own troops' activities
    # ONLY show commissioner activities if THIS commissioner RUNS them on this day
    for entry in schedule.entries:
        if entry.troop.name not in assigned_troops:
            continue
        
        activity_name = entry.activity.name
        day_name = entry.time_slot.day.name
        slot_num = entry.time_slot.slot_number
        
        # For commissioner activities, only show if THIS commissioner owns the day
        # If another commissioner runs it, don't show it here (it'll show on their schedule)
        runs_this = False
        
        if activity_name == "Delta":
            day_owner = DAY_DELTA_OWNER.get(entry.time_slot.day)
            runs_this = (day_owner == commissioner_name)
        elif activity_name == "Archery":
            day_owner = DAY_ARCHERY_OWNER.get(entry.time_slot.day)
            runs_this = (day_owner == commissioner_name)
        elif activity_name == "Super Troop":
            day_owner = DAY_SUPER_TROOP_OWNER.get(entry.time_slot.day)
            runs_this = (day_owner == commissioner_name)
        elif activity_name == "Reflection" and entry.time_slot.day == Day.FRIDAY:
            runs_this = True  # Always own their own Reflection
        
        if runs_this:
            schedule_grid[day_name][slot_num].append({
                'troop': entry.troop.name,
                'activity': activity_name,
                'borrowed': False,
                'runs_activity': True
            })
    
    # Second, add "borrowed" activities - other commissioners' troops on THIS commissioner's days
    for entry in schedule.entries:
        # Skip our own troops
        if entry.troop.name in assigned_troops:
            continue
        
        activity_name = entry.activity.name
        day_name = entry.time_slot.day.name
        slot_num = entry.time_slot.slot_number
        
        # Check if this activity falls on THIS commissioner's owned day (dynamic)
        is_borrowed = False
        if activity_name == "Delta":
            # Check if THIS commissioner owns Delta on this day
            day_owner = DAY_DELTA_OWNER.get(entry.time_slot.day)
            if day_owner == commissioner_name:
                is_borrowed = True
        elif activity_name == "Archery":
            # Check if THIS commissioner owns Archery on this day
            day_owner = DAY_ARCHERY_OWNER.get(entry.time_slot.day)
            if day_owner == commissioner_name:
                is_borrowed = True
        elif activity_name == "Super Troop":
            # Check if THIS commissioner owns Super Troop on this day
            day_owner = DAY_SUPER_TROOP_OWNER.get(entry.time_slot.day)
            if day_owner == commissioner_name:
                is_borrowed = True
        
        if is_borrowed:
            # Find which commissioner this troop belongs to
            troop_commissioner = None
            for comm, troop_list in COMMISSIONER_TROOPS.items():
                if entry.troop.name in troop_list:
                    troop_commissioner = comm
                    break
            
            schedule_grid[day_name][slot_num].append({
                'troop': entry.troop.name,
                'activity': activity_name,
                'borrowed': True,
                'from_commissioner': troop_commissioner
            })
    
    return schedule_grid

@app.route('/api/beach_board')
def get_beach_board():
    """Get Beach Board schedule showing all beach activities with troops filled in."""
    week = request.args.get('week', current_week)
    if week not in WEEK_METADATA:
        week = current_week
    data = get_week_data(week)
    schedule = data['schedule']
    
    # Define beach activities to display (NO BALLS - those have their own area)
    beach_activities = [
        'Aqua Trampoline',
        'Greased Watermelon', 
        'Troop Swim/UOC',  # Group Troop Swim and Underwater Obstacle Course together
        'Water Polo',
        'Sauna',
        'Fishing'
    ]
    
    # Create grid structure: {activity: {day: {slot: [troops]}}}
    beach_grid = {}
    for activity in beach_activities:
        beach_grid[activity] = {}
        for day in Day:
            beach_grid[activity][day.name] = {1: [], 2: [], 3: []}
    
    # Track already-seen entries to avoid duplicates from multi-slot activities
    seen_entries = set()
    
    # Fill in the grid with scheduled troops
    for entry in schedule.entries:
        activity_name = entry.activity.name
        day_name = entry.time_slot.day.name
        slot_num = entry.time_slot.slot_number
        troop_name = entry.troop.name
        
        # Create unique key to prevent duplicates
        entry_key = (activity_name, day_name, troop_name)
        if entry_key in seen_entries:
            continue
        seen_entries.add(entry_key)
        
        # Map activities to beach board categories
        if activity_name == 'Aqua Trampoline':
            # Track troop with shared indicator
            beach_grid['Aqua Trampoline'][day_name][slot_num].append({
                'troop': troop_name,
                'shared': False  # Will be updated after all entries processed
            })
        elif activity_name == 'Greased Watermelon':
            beach_grid['Greased Watermelon'][day_name][slot_num].append(troop_name)
        elif activity_name in ['Troop Swim', 'Underwater Obstacle Course']:
            beach_grid['Troop Swim/UOC'][day_name][slot_num].append(troop_name)
        elif activity_name == 'Water Polo':
            beach_grid['Water Polo'][day_name][slot_num].append(troop_name)
        elif activity_name == 'Sauna':
            beach_grid['Sauna'][day_name][slot_num].append(troop_name)
        elif activity_name == 'Fishing':
            beach_grid['Fishing'][day_name][slot_num].append(troop_name)
    
    # Post-process Aqua Trampoline to mark shared slots
    for day_name in beach_grid['Aqua Trampoline']:
        for slot_num in beach_grid['Aqua Trampoline'][day_name]:
            entries = beach_grid['Aqua Trampoline'][day_name][slot_num]
            if len(entries) >= 2:
                # Mark all troops in this slot as shared
                for entry in entries:
                    entry['shared'] = True
    
    return beach_grid

@app.route('/api/balls')
def get_balls_schedule():
    """Get Balls (Gaga Ball, 9 Square) schedule."""
    week = request.args.get('week', current_week)
    if week not in WEEK_METADATA:
        week = current_week
    data = get_week_data(week)
    schedule = data['schedule']
    
    balls_activities = ['Gaga Ball', '9 Square']
    
    # Create grid structure: {activity: {day: {slot: [troops]}}}
    balls_grid = {}
    for activity in balls_activities:
        balls_grid[activity] = {}
        for day in Day:
            balls_grid[activity][day.name] = {1: [], 2: [], 3: []}
    
    # Track already-seen entries to avoid duplicates
    seen_entries = set()
    
    for entry in schedule.entries:
        activity_name = entry.activity.name
        if activity_name not in balls_activities:
            continue
            
        day_name = entry.time_slot.day.name
        slot_num = entry.time_slot.slot_number
        troop_name = entry.troop.name
        
        entry_key = (activity_name, day_name, troop_name)
        if entry_key in seen_entries:
            continue
        seen_entries.add(entry_key)
        
        balls_grid[activity_name][day_name][slot_num].append(troop_name)
    
    return balls_grid

@app.route('/api/reflection')
def get_reflection_schedule():
    """Get Reflection schedule showing all troops by commissioner and slot, with availability."""
    week = request.args.get('week', current_week)
    if week not in WEEK_METADATA:
        week = current_week
    data = get_week_data(week)
    schedule = data['schedule']
    
    
    # Build COMMISSIONER_TROOPS dynamically from actual troop data (supports TC and Voyageur)
    troops = data['troops']
    COMMISSIONER_TROOPS = {}
    for troop in troops:
        comm = troop.commissioner if hasattr(troop, 'commissioner') else getattr(troop, 'commissioner', None)
        if comm:
            if comm not in COMMISSIONER_TROOPS:
                COMMISSIONER_TROOPS[comm] = []
            COMMISSIONER_TROOPS[comm].append(troop.name)
    
    # Fallback for TC if no commissioner data
    if not COMMISSIONER_TROOPS:
        COMMISSIONER_TROOPS = {
            "Commissioner A": ["Tecumseh", "Red Cloud", "Massasoit", "Joseph"],
            "Commissioner B": ["Tamanend", "Samoset", "Black Hawk"],
            "Commissioner C": ["Taskalusa", "Powhatan", "Cochise"]
        }
    
    # Commissioner designated activities that would prevent them from running Reflection
    # Day assignments - support both TC and Voyageur
    COMMISSIONER_DELTA_DAYS = {
        "Commissioner A": Day.MONDAY, "Commissioner B": Day.TUESDAY, "Commissioner C": Day.WEDNESDAY,
        "Voyageur A": Day.TUESDAY, "Voyageur B": Day.WEDNESDAY, "Voyageur C": Day.THURSDAY
    }
    
    COMMISSIONER_SUPER_TROOP_DAYS = {
        "Commissioner A": Day.TUESDAY, "Commissioner B": Day.WEDNESDAY, "Commissioner C": Day.THURSDAY,
        "Voyageur A": Day.TUESDAY, "Voyageur B": Day.WEDNESDAY, "Voyageur C": Day.THURSDAY
    }
    
    COMMISSIONER_ARCHERY_DAYS = {
        "Commissioner A": Day.WEDNESDAY,
        "Commissioner B": Day.FRIDAY,
        "Commissioner C": Day.MONDAY
    }
    
    # Group by slot - include availability info
    reflection_grid = {
        1: {},
        2: {},
        3: {}
    }
    
    # Find all Reflection entries on Friday
    friday_slots = [s for s in time_slots if s.day == Day.FRIDAY]
    
    # First, check commissioner availability for each slot
    for slot_num in [1, 2, 3]:
        friday_slot = next((s for s in friday_slots if s.slot_number == slot_num), None)
        if not friday_slot:
            continue
            
        for commissioner, troop_list in COMMISSIONER_TROOPS.items():
            # Check if commissioner has conflicting activities in this slot
            has_conflict = False
            conflict_activity = None
            
            # Check if any of commissioner's troops have Delta/Archery/Super Troop in this slot
            for entry in schedule.entries:
                if entry.time_slot == friday_slot and entry.troop.name in troop_list:
                    # These activities mean commissioner is busy
                    if entry.activity.name in ["Delta", "Archery", "Super Troop"]:
                        has_conflict = True
                        conflict_activity = entry.activity.name
                        break
            
            reflection_grid[slot_num][commissioner] = {
                'troops': [],
                'available': not has_conflict,
                'conflict': conflict_activity
            }
    
    # Now add the actual Reflection assignments
    for entry in schedule.entries:
        if entry.activity.name == "Reflection" and entry.time_slot in friday_slots:
            slot_num = entry.time_slot.slot_number
            troop_name = entry.troop.name
            
            # Find which commissioner this troop belongs to
            commissioner = None
            for comm, troops in COMMISSIONER_TROOPS.items():
                if troop_name in troops:
                    commissioner = comm
                    break
            
            if commissioner and commissioner in reflection_grid[slot_num]:
                reflection_grid[slot_num][commissioner]['troops'].append(troop_name)
    
    return reflection_grid

@app.route('/api/staff/<staff_name>')
def get_staff_schedule(staff_name):
    """Get schedule for a staff member showing their activities."""
    week = request.args.get('week', current_week)
    if week not in WEEK_METADATA:
        week = current_week
    data = get_week_data(week)
    schedule = data['schedule']
    
    # Map staff names to their activities
    staff_to_activities = {
        'Beach Staff': ['Aqua Trampoline', 'Greased Watermelon', 'Water Polo', 
                       'Troop Swim', 'Underwater Obstacle Course', 'Troop Canoe', 'Troop Kayak',
                       'Canoe Snorkel', 'Float for Floats'],
        'Ass. Aquatics': ['Sailing'],
        'Shooting Sports Director': ['Troop Rifle', 'Troop Shotgun'],
        'Archery Director': ['Archery'],
        'Tower Director': ['Climbing Tower'],
        'Outdoor Skills Director': ['Knots and Lashings', 'Orienteering', 'GPS & Geocaching',
                                   'Ultimate Survivor', 'What\'s Cooking', 'Chopped!'],
        'Nature Director': ['Dr. DNA', 'Loon Lore', 'Nature Canoe', 'Ecosystem in a Jar',
                          'Nature Salad', 'Nature Bingo'],
        'Handicrafts Director': ['Tie Dye', 'Hemp Craft', 'Woggle Neckerchief Slide', 'Monkey\'s Fist']
    }
    
    if staff_name not in staff_to_activities:
        return {"error": "Staff not found"}, 404
    
    staff_activities = staff_to_activities[staff_name]
    
    # Create schedule grid
    schedule_grid = {}
    for day in Day:
        schedule_grid[day.name] = {1: [], 2: [], 3: []}
    
    # Find all entries for this staff member's activities
    staff_entries = [e for e in schedule.entries if e.activity.name in staff_activities]
    
    for entry in staff_entries:
        day_name = entry.time_slot.day.name
        slot_num = entry.time_slot.slot_number
        schedule_grid[day_name][slot_num].append({
            'troop': entry.troop.name,
            'activity': entry.activity.name,
            'priority': entry.troop.get_priority(entry.activity.name),
            'scouts': entry.troop.scouts,
            'adults': entry.troop.adults
        })
    
    return schedule_grid


@app.route('/api/unscheduled')
def get_unscheduled_activities():
    """Get all activities that were not scheduled, sorted by priority, activity name, and troop."""
    week = request.args.get('week', current_week)
    if week not in WEEK_METADATA:
        week = current_week
    data = get_week_data(week)
    if not data:
        return {"error": "Week data not available"}, 404
    
    troops = data['troops']
    schedule = data['schedule']
    
    # ALWAYS use pre-calculated unscheduled data from scheduler
    # This ensures consistency with the scheduler's logic and prevents drift
    if 'unscheduled' in data and data['unscheduled']:
        unscheduled_list = []
        for troop_name, info in data['unscheduled'].items():
            # Add Top 5
            for item in info.get('top5', []):
                unscheduled_list.append({
                    'troop': troop_name,
                    'activity': item['name'],
                    'rank': item['rank'],
                    'priority': item['rank'],  # Top 5 = highest priority
                    'exempt': item.get('is_exempt', False)
                })
            # Add Top 10
            for item in info.get('top10', []):
                unscheduled_list.append({
                    'troop': troop_name,
                    'activity': item['name'],
                    'rank': item['rank'],
                    'priority': item['rank'],  # Top 10 = medium priority
                    'exempt': item.get('is_exempt', False)
                })
        
        # Sort by: 1) priority/rank (lower is better), 2) activity name, 3) troop name
        unscheduled_list.sort(key=lambda x: (x['priority'], x['activity'], x['troop']))
        
        return jsonify({
            'unscheduled': unscheduled_list,
            'total_count': len(unscheduled_list),
            'source': 'scheduler_calculated'
        })

    # ERROR: No unscheduled data available - this indicates a data consistency issue
    print(f"WARNING: No unscheduled data found for {week} - data inconsistency detected")
    
    # Emergency fallback: calculate minimal unscheduled data
    unscheduled_list = []
    
    for troop in troops:
        # Get all activities this troop has scheduled
        troop_schedule = schedule.get_troop_schedule(troop)
        scheduled_activities = {e.activity.name for e in troop_schedule}
        
        # Find preferences that weren't scheduled
        for idx, pref in enumerate(troop.preferences):
            if pref not in scheduled_activities:
                rank = idx + 1
                unscheduled_list.append({
                    'troop': troop.name,
                    'activity': pref,
                    'rank': rank,
                    'priority': rank,
                    'exempt': False  # Can't determine exemption status without scheduler logic
                })
    
    # Sort by: 1) priority/rank (lower is better), 2) activity name, 3) troop name
    unscheduled_list.sort(key=lambda x: (x['priority'], x['activity'], x['troop']))
    
    return jsonify({
        'unscheduled': unscheduled_list,
        'total_count': len(unscheduled_list),
        'source': 'emergency_fallback',
        'warning': 'Data inconsistency detected - results may be inaccurate'
    })

@app.route('/api/staff-requirements')
def get_staff_requirements():
    """Get ALL staff requirements per time slot across all areas."""
    week = request.args.get('week', current_week)
    if week not in WEEK_METADATA:
        week = current_week
    data = get_week_data(week)
    schedule = data['schedule']
    
    # Map activities to their staff director (and count)
    activity_to_staff = {
        # Beach Staff (2 staff each) - water activities at the beach
        'Aqua Trampoline': ('Beach Staff', 2),
        'Greased Watermelon': ('Beach Staff', 2),
        'Underwater Obstacle Course': ('Beach Staff', 2),
        'Troop Swim': ('Beach Staff', 2),
        'Water Polo': ('Beach Staff', 2),
        
        # Boats Staff (separate from Beach Staff) - boat activities
        'Troop Canoe': ('Boats Staff', 2),
        'Troop Kayak': ('Boats Staff', 2),
        'Canoe Snorkel': ('Boats Staff', 3),  # 3 staff required
        'Float for Floats': ('Boats Staff', 3),  # 3 staff required
        'Nature Canoe': ('Boats Staff', 2),
        
        # Assistant Aquatics Director (1 staff)
        'Sailing': ('Ass. Aquatics', 1),
        
        # Shooting Sports Director (1 staff)
        'Troop Rifle': ('Shooting Sports Director', 1),
        'Troop Shotgun': ('Shooting Sports Director', 1),
        
        # Archery Director (1 staff)
        'Archery': ('Archery Director', 1),
        
        # Tower Director (2 staff - director + assistant)
        'Climbing Tower': ('Tower Director', 2),
        
        # Outdoor Skills Director (1 staff)
        'Orienteering': ('Outdoor Skills Director', 1),
        'GPS & Geocaching': ('Outdoor Skills Director', 1),
        'Knots and Lashings': ('Outdoor Skills Director', 1),
        'Ultimate Survivor': ('Outdoor Skills Director', 1),
        'Back of the Moon': ('Outdoor Skills Director', 1),
        
        # Nature Director (1 staff)
        'Loon Lore': ('Nature Director', 1),
        'Dr. DNA': ('Nature Director', 1),
        'Nature Canoe': ('Nature Director', 1),
        
        # Handicrafts Director (1 staff)
        'Tie Dye': ('Handicrafts Director', 1),
        'Hemp Craft': ('Handicrafts Director', 1),
        "Woggle Neckerchief Slide": ('Handicrafts Director', 1),
        "Monkey's Fist": ('Handicrafts Director', 1),
        
        # Commissioner Activities (1 commissioner each)
        'Reflection': ('Commissioner', 1),
        'Delta': ('Commissioner', 1),
        'Super Troop': ('Commissioner', 1),
    }
    
    # Build requirements grid
    requirements = {}
    for day in Day:
        requirements[day.name] = {
            1: {'total_staff': 0, 'by_director': {}, 'scouts_by_activity': {}}, 
            2: {'total_staff': 0, 'by_director': {}, 'scouts_by_activity': {}}, 
            3: {'total_staff': 0, 'by_director': {}, 'scouts_by_activity': {}}
        }
    
    # Track scouts per activity type per slot for recommendations
    for entry in schedule.entries:
        if entry.activity.name in activity_to_staff:
            director, staff_count = activity_to_staff[entry.activity.name]
            day_name = entry.time_slot.day.name
            slot_num = entry.time_slot.slot_number
            
            # Track people per troop for ratio-based recommendations
            activity_type = None
            if entry.activity.name in ['Aqua Trampoline', 'Troop Canoe', 'Troop Kayak', 'Canoe Snorkel',
                                       'Float for Floats', 'Greased Watermelon', 'Underwater Obstacle Course',
                                       'Troop Swim', 'Water Polo']:
                activity_type = 'beach_troops'
            elif entry.activity.name == 'Climbing Tower':
                activity_type = 'tower_troops'
            
            if activity_type:
                if activity_type not in requirements[day_name][slot_num]['scouts_by_activity']:
                    requirements[day_name][slot_num]['scouts_by_activity'][activity_type] = []
                # Store each troop's people count separately for per-troop calculations
                requirements[day_name][slot_num]['scouts_by_activity'][activity_type].append(entry.troop.scouts + entry.troop.adults)
            
            # Special case: Water Polo can be shared by 2 small troops (< 8 scouts each)
            # Instead of 2 staff per troop (4 total), they share 2 staff
            if entry.activity.name == 'Water Polo':
                # Check if this slot already has a Water Polo entry
                day_slot_key = (day_name, slot_num)
                if day_slot_key not in requirements[day_name][slot_num].get('_water_polo_processed', set()):
                    # Get all Water Polo entries in this slot
                    polo_entries = [e for e in schedule.entries 
                                   if e.activity.name == 'Water Polo' 
                                   and e.time_slot.day.name == day_name 
                                   and e.time_slot.slot_number == slot_num]
                    
                    # Check if we can share (2 troops, both under 8 scouts)
                    if len(polo_entries) == 2 and all(e.troop.scouts < 8 for e in polo_entries):
                        # Shared Water Polo - only 2 staff total
                        staff_count = 2
                        requirements[day_name][slot_num]['total_staff'] += staff_count
                        if director not in requirements[day_name][slot_num]['by_director']:
                            requirements[day_name][slot_num]['by_director'][director] = 0
                        requirements[day_name][slot_num]['by_director'][director] += staff_count
                        
                        # Mark as processed so we don't count twice
                        if '_water_polo_processed' not in requirements[day_name][slot_num]:
                            requirements[day_name][slot_num]['_water_polo_processed'] = set()
                        requirements[day_name][slot_num]['_water_polo_processed'].add(day_slot_key)
                        continue  # Skip normal processing
            
            # Normal processing - add to total
            requirements[day_name][slot_num]['total_staff'] += staff_count
            
            # Track by director
            if director not in requirements[day_name][slot_num]['by_director']:
                requirements[day_name][slot_num]['by_director'][director] = 0
            requirements[day_name][slot_num]['by_director'][director] += staff_count
    
    # Calculate EXTRA staff recommended beyond base 2-per-activity
    # Beach: base 2 is good for 1-20 people, need +1 for each 10 people over 20
    # Tower: base 2 is good for 1-12 people, need +1 for each 6 people over 12
    for day in Day:
        for slot in [1, 2, 3]:
            scouts = requirements[day.name][slot]['scouts_by_activity']
            extra_recommended = 0
            
            # Beach: +1 staff for each 10 people over 20
            if 'beach_troops' in scouts:
                for troop_people in scouts['beach_troops']:
                    if troop_people > 20:
                        extra_recommended += (troop_people - 20 + 9) // 10  # +1 per 10 over 20
            
            # Tower: +1 staff for each 6 people over 12
            if 'tower_troops' in scouts:
                for troop_people in scouts['tower_troops']:
                    if troop_people > 12:
                        extra_recommended += (troop_people - 12 + 5) // 6  # +1 per 6 over 12
            
            requirements[day.name][slot]['recommended_staff'] = extra_recommended
    
    # Clean up temporary processing markers
    for day in Day:
        for slot in [1, 2, 3]:
            if '_water_polo_processed' in requirements[day.name][slot]:
                del requirements[day.name][slot]['_water_polo_processed']
            # Keep scouts_by_activity for potential future use, but could remove:
            del requirements[day.name][slot]['scouts_by_activity']
    
    return requirements


if __name__ == '__main__':
    print("\n" + "="*60)
    print("Summer Camp Scheduler - Web GUI")
    print("="*60)
    print("\nOpen your browser to: http://localhost:5000")
    print("\nPress Ctrl+C to stop the server")
    print("="*60 + "\n")
    
    app.run(debug=True, port=5000)
