"""
Web-based GUI for Summer Camp Scheduler using Flask.
This generates an HTML interface that properly displays 1.5-slot activities.
"""
from flask import Flask, render_template, send_from_directory, request, jsonify, Response
from pathlib import Path
import json
import sys
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from core.models import Day, TimeSlot, generate_time_slots, ScheduleEntry, Troop, Schedule
from core.activities import get_all_activities
from core.io_handler import load_troops_from_json, save_schedule_to_json
from core.constrained_scheduler import ConstrainedScheduler
from core.services.sailing_half_fills import build_sailing_half_fills, get_request_credit_fill_activities, make_sailing_fill_key
from core.services.unscheduled_source import build_unscheduled_data

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


def _preference_ui_weight(rank_index):
    """Continuous display weight: rank 1 = 5.0, rank 20 = 0.25."""
    return max(0.0, 5.0 - (rank_index * 0.25))


def _max_weighted_preference_score(preference_items, capacity_slots):
    """Knapsack max for troop preference display scores using half-slot units."""
    capacity_units = max(0, int(round(capacity_slots * 2)))
    dp = [0.0] * (capacity_units + 1)
    for slot_cost, weight in preference_items:
        units = max(1, int(round(slot_cost * 2)))
        if units > capacity_units:
            continue
        for cap in range(capacity_units, units - 1, -1):
            dp[cap] = max(dp[cap], dp[cap - units] + weight)
    return max(dp) if dp else 0.0


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
            if (
                time_slot is None
                and entry_data.get('day') == Day.THURSDAY.name
                and entry_data.get('slot') == 3
            ):
                # Scheduler may serialize a virtual Thu-3 for approved 3-hour
                # day-request opt-outs; it is not part of the visible grid.
                time_slot = TimeSlot(day=Day.THURSDAY, slot_number=3)
            
            if not troop or not activity or not time_slot:
                # If any data is invalid/missing, raise error to force regeneration
                # This handles cases where activities were renamed or removed
                missing = []
                if not troop: missing.append(f"Troop: {entry_data.get('troop_name')}")
                if not activity: missing.append(f"Activity: {entry_data.get('activity_name')}")
                if not time_slot: missing.append(f"Slot: {entry_data.get('day')}-{entry_data.get('slot')}")
                raise ValueError(f"Invalid schedule entry data: {', '.join(missing)}")
                
            entry = ScheduleEntry(time_slot=time_slot, activity=activity, troop=troop)
            schedule.entries.append(entry)
        except Exception as e:
            raise ValueError(f"Error processing schedule entry: {e}")
            
    sailing_half_fills = data.get('sailing_half_fills', {}) or {}
    if not sailing_half_fills:
        sailing_half_fills = build_sailing_half_fills(troops, schedule)
    # Rebuild authoritative unscheduled payload on load so cached schedules
    # always reflect the current request-credit semantics for Sailing half-fills.
    unscheduled = build_unscheduled_data(troops, schedule, sailing_half_fills)
    
    return troops, schedule, unscheduled, sailing_half_fills

def generate_schedule(troops_file):
    """Generate schedule from troops file (fallback)."""
    print(f"  Generating schedule from {troops_file.name}...")
    troops = load_troops_from_json(troops_file)
    voyageur_mode = "voyageur" in troops_file.name.lower()
    scheduler = ConstrainedScheduler(troops, activities, voyageur_mode=voyageur_mode)
    schedule = scheduler.schedule_all()
    
    sailing_half_fills = getattr(scheduler, 'sailing_balls_fills', {}) or {}
    if not sailing_half_fills:
        sailing_half_fills = build_sailing_half_fills(scheduler.troops, schedule)
    # Authoritative unscheduled payload for all Top-5/Top-10 miss reporting.
    unscheduled_data = build_unscheduled_data(scheduler.troops, schedule, sailing_half_fills)
            
    # vital: return scheduler.troops because they might have been split
    return scheduler.troops, schedule, unscheduled_data, sailing_half_fills

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
            troops, schedule, unscheduled_data, sailing_half_fills = load_schedule_from_json(schedule_file)
            schedule_mtime = schedule_file.stat().st_mtime
            print(f"  Loaded from cache")
        except Exception as e:
            print(f"  Cache failed: {e}, regenerating...")
            try:
                troops, schedule, unscheduled_data, sailing_half_fills = generate_schedule(troops_file)
            except Exception as e2:
                print(f"  Schedule generation failed: {e2}")
                # Return empty data rather than crashing
                return {
                    'troops': [],
                    'schedule': Schedule(),
                    'unscheduled': {},
                    'sailing_half_fills': {},
                    'week_number': meta['week_number'],
                    'file': troops_file.name,
                    '_mtime': 0,
                    'error': str(e2)
                }
    else:
        try:
            print(f"  Generating fresh schedule...")
            troops, schedule, unscheduled_data, sailing_half_fills = generate_schedule(troops_file)
        except Exception as e:
            print(f"  Schedule generation failed: {e}")
            # Return empty data rather than crashing
            return {
                'troops': [],
                'schedule': Schedule(),
                'unscheduled': {},
                'sailing_half_fills': {},
                'week_number': meta['week_number'],
                'file': troops_file.name,
                '_mtime': 0,
                'error': str(e)
            }
    
    WEEK_DATA[week_id] = {
        'troops': troops,
        'schedule': schedule,
        'unscheduled': unscheduled_data,
        'sailing_half_fills': sailing_half_fills,
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
    serialized_troops = [troop.model_dump(mode='json') for troop in data['troops']]
    
    return render_template('index.html', 
                         troops=serialized_troops,
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


def _build_soft_deductions(metrics, score_diagnostics):
    """Return user-facing deduction rows matching the scorer's point losses."""
    rows = []

    def add_row(label, points, reason, details=None):
        points = float(points or 0)
        if points <= 0:
            return
        rows.append({
            'label': label,
            'points': round(points, 1),
            'reason': reason,
            'details': details or [],
        })

    add_row(
        'Soft rule violations',
        int(metrics.get('soft_violations', 0)) * 10.0,
        'Each soft violation costs points because the schedule is workable but less comfortable.',
        metrics.get('soft_violation_details', []),
    )
    add_row(
        'Beach slot 2 usage',
        int(metrics.get('beach_slot_2_uses', 0)) * 3.0,
        'Beach activities in slot 2 are allowed in some cases, but slot 1 or 3 is preferred.',
    )
    add_row(
        'Delta timing',
        score_diagnostics.get('delta_timing_penalty', metrics.get('delta_timing_penalty', 0)),
        'Delta is compared to the earliest capacity window needed for this week. Later days lose more only when they extend beyond that window.',
        metrics.get('delta_timing_penalty_details', []),
    )
    add_row(
        'Delta/Sailing pairing',
        score_diagnostics.get('delta_sailing_pairing_penalty', metrics.get('delta_sailing_pairing_penalty', 0)),
        'Troops that receive both Delta and Sailing should have them on the same day when possible.',
    )
    add_row(
        'Aqua Trampoline sharing',
        score_diagnostics.get('at_sharing_penalty', metrics.get('at_sharing_penalty', 0)),
        'Small Aqua Trampoline troops are expected to share slots in pairs when capacity allows.',
    )
    add_row(
        'Activity batching',
        score_diagnostics.get('activity_batching_penalty', 0),
        'Repeat setup activities score better when grouped back-to-back on the same day.',
    )
    add_row(
        'Sailing day cleanliness',
        score_diagnostics.get('sailing_full_day_penalty', 0),
        'Sailing days score better when they avoid extra staffed activities for the same troop.',
    )
    add_row(
        'Sailing same-day grouping',
        score_diagnostics.get('sailing_same_day_penalty', 0),
        'Sailing setup scores better when multiple troops can share the same sailing day.',
    )

    return rows


@app.route('/api/evaluation/<week_id>')
def get_evaluation(week_id):
    """Return evaluation metrics for a week (score, violations, exclusive double-book, beach slot 2, schedule invalid)."""
    if week_id not in WEEK_METADATA:
        return jsonify({'error': 'Week not found'}), 404
    try:
        from utils.regression_checker import evaluate_week
        meta = WEEK_METADATA[week_id]
        troops_file = meta['file']
        # evaluate_week expects filename like tc_week5_troops.json (relative or absolute)
        week_file_path = str(troops_file)
        metrics = evaluate_week(week_file_path)
        score_components = metrics.get('score_components', {}) or {}
        score_diagnostics = metrics.get('score_component_diagnostics', {}) or {}
        soft_deductions = _build_soft_deductions(metrics, score_diagnostics)
        return jsonify({
            'final_score': metrics.get('final_score', 0),
            'constraint_violations': metrics.get('constraint_violations', 0),
            'exclusive_double_book': metrics.get('exclusive_double_book', 0),
            'beach_slot_2_uses': metrics.get('beach_slot_2_uses', 0),
            'schedule_invalid': metrics.get('schedule_invalid', False),
            'missing_top5': metrics.get('missing_top5', 0),
            'top5_pct': metrics.get('top5_pct', 0),
            'staff_variance': metrics.get('staff_variance', 0),
            'avg_staff_load': metrics.get('avg_staff_load', 0),
            'staff_load_by_slot': metrics.get('staff_load_by_slot', {}),
            'severe_underused_slots': metrics.get('severe_underused_slots', 0),
            'over_target_staff_slots': metrics.get('over_target_staff_slots', 0),
            'excessive_staff_slots': metrics.get('excessive_staff_slots', 0),
            'delta_required_latest_day': metrics.get('delta_required_latest_day'),
            'expectation_penalty': metrics.get('expectation_penalty', 0),
            'score_components': score_components,
            'score_component_diagnostics': score_diagnostics,
            'component_summary': {
                'preference_points': score_components.get('preference_points', 0),
                'cluster_efficiency_points': score_components.get('cluster_efficiency_points', 0),
                'soft_constraint_points': score_components.get('soft_constraint_points', 0),
                'staff_balance_points': score_components.get('staff_balance_points', 0),
                'expectation_penalties': score_diagnostics.get('total_expectation_penalties', 0),
            },
            'soft_deductions': soft_deductions,
            'hard_violation_details': metrics.get('hard_violation_details', []),
            'soft_violation_details': metrics.get('soft_violation_details', []),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/troop_scoring/<week_id>')
def get_troop_scoring(week_id):
    """Return detailed troop scoring for a week showing each troop's score out of possible activities."""
    if week_id not in WEEK_METADATA:
        return jsonify({'error': 'Week not found'}), 404
        
    try:
        from core.activities import get_activity_by_name, get_all_activities

        meta = WEEK_METADATA[week_id]
        data = get_week_data(week_id)
        if not data:
            return jsonify({'error': 'Week data not available'}), 404

        troops = data['troops']
        schedule = data['schedule']
        sailing_half_fills = data.get('sailing_half_fills', {}) or {}
        
        TOTAL_AVAILABLE_SLOTS = 14.0
        troop_scoring = []
        
        for troop in troops:
            troop_acts = set(e.activity.name for e in schedule.entries if e.troop == troop)
            troop_acts |= get_request_credit_fill_activities(troop, sailing_half_fills)
            
            # ---------------------------------------------------------
            # Part A: Calculate Actual Score (What they actually got)
            # ---------------------------------------------------------
            troop_score_hits = 0.0
            preferences_scheduled = 0
            preference_items = []
            
            for i, pref_name in enumerate(troop.preferences):
                if i >= 20: break  # Only score top 20

                pref_activity = get_activity_by_name(pref_name)
                pref_slots = schedule._get_effective_slots(pref_activity, troop) if pref_activity else 1.0
                weight = _preference_ui_weight(i)
                preference_items.append((pref_slots, weight))
                
                if pref_name in troop_acts:
                    troop_score_hits += weight
                    preferences_scheduled += 1

            # ---------------------------------------------------------
            # Part B: Calculate Max Possible Score (Theoretical Perfect Packing)
            # ---------------------------------------------------------
            max_possible_score = _max_weighted_preference_score(preference_items, TOTAL_AVAILABLE_SLOTS)
            # Defensive display guard: the actual scheduled subset should fit in
            # 14 slots, but never show a troop above its denominator.
            max_possible_score = max(max_possible_score, troop_score_hits)
            max_activities_fit = 0
            temp_capacity_units = int(TOTAL_AVAILABLE_SLOTS * 2)
            for pref_slots, _weight in sorted(preference_items, key=lambda item: item[0]):
                units = max(1, int(round(pref_slots * 2)))
                if temp_capacity_units - units < 0:
                    continue
                temp_capacity_units -= units
                max_activities_fit += 1
            
            # Calculate available slots (14 total minus mandatory spine activities)
            available_slots = TOTAL_AVAILABLE_SLOTS - (1.0 if "Reflection" in troop_acts else 0.0) - (1.0 if "Super Troop" in troop_acts else 0.0)
            
            # Append payload
            troop_scoring.append({
                'name': troop.name,
                'score': round(troop_score_hits, 1),
                'max_possible': round(max_possible_score, 1),
                'available_slots': available_slots,
                'activities_fit': max_activities_fit, # Fix: Now returns count of activities, not slot count
                'scheduled_prefs': preferences_scheduled
            })
        
        # Sort by score percentage (highest first)
        troop_scoring.sort(key=lambda x: x['score'] / max(x['max_possible'], 1), reverse=True)
        
        return jsonify({
            'troops': troop_scoring,
            'week_name': meta['week_number']
        })
        
    except Exception as e:
        print(f"Error getting troop scoring for {week_id}: {e}")
        return jsonify({'error': str(e)}), 500


def _determine_week_health(schedule_invalid, top5_pct, constraint_violations):
    """Return an easy-to-read health label for non-technical users."""
    if schedule_invalid:
        return "Needs Immediate Fix"
    if top5_pct >= 85 and constraint_violations == 0:
        return "Excellent"
    if top5_pct >= 75 and constraint_violations <= 2:
        return "Good"
    if top5_pct >= 65:
        return "Fair"
    return "Needs Improvement"


def _build_actions(metrics):
    """Generate plain-language action items from metric values."""
    actions = []
    if metrics.get('schedule_invalid', False):
        actions.append("Regenerate this week first: the schedule is marked invalid and should not be used as-is.")
    if metrics.get('exclusive_double_book', 0) > 0:
        actions.append("Fix exclusive-area conflicts (like Tower/Delta/Super Troop in the same slot for multiple troops).")
    if metrics.get('missing_top5', 0) > 0:
        actions.append("Improve Top 5 request coverage by moving flexible activities to protect high-priority choices.")
    if metrics.get('beach_slot_2_uses', 0) > 0:
        actions.append("Reduce beach activities in slot 2 when possible; slot 1 or 3 is preferred for flow and scoring.")
    if metrics.get('severe_underused_slots', 0) > 0 or metrics.get('staff_variance', 0.0) > 2.5:
        actions.append("Rebalance staff-heavy activities so workload is spread more evenly across the week.")
    if metrics.get('cluster_gaps', 0) > 0 or metrics.get('excess_cluster_days', 0) > 0:
        actions.append("Tighten clustering in Tower/Rifle/Outdoor Skills/Handicrafts to reduce travel and gaps.")
    if not actions:
        actions.append("No urgent changes needed. This week is balanced and can be shared confidently.")
    return actions


def _build_success_report(week_id, week_name, metrics, data):
    """Create a plain-English success report suitable for non-programmers."""
    troops = data.get('troops', []) or []
    unscheduled = data.get('unscheduled', {}) or {}
    cluster_area_details = metrics.get('cluster_area_details', {}) or {}
    cluster_gap_details = metrics.get('cluster_gap_details', []) or []
    cluster_targets = metrics.get('cluster_improvement_targets', {}) or {}
    total_scouts = sum(getattr(t, 'scouts', 0) for t in troops)
    total_adults = sum(getattr(t, 'adults', 0) for t in troops)

    exempt_top5 = 0
    exempt_top10 = 0
    for troop_data in unscheduled.values():
        exempt_top5 += sum(1 for item in troop_data.get('top5', []) if item.get('is_exempt'))
        exempt_top10 += sum(1 for item in troop_data.get('top10', []) if item.get('is_exempt'))

    top5_pct = float(metrics.get('top5_pct', 0.0))
    top10_pct = float(metrics.get('top10_pct', 0.0))
    top15_pct = float(metrics.get('top15_pct', 0.0))
    constraint_violations = int(metrics.get('constraint_violations', 0))
    schedule_invalid = bool(metrics.get('schedule_invalid', False))
    final_score = int(metrics.get('final_score', 0))

    health = _determine_week_health(schedule_invalid, top5_pct, constraint_violations)
    actions = _build_actions(metrics)

    scorecard = [
        {
            'metric': 'Overall Week Score',
            'value': final_score,
            'status': health,
            'why_it_matters': 'Single roll-up score that combines requests, efficiency, soft expectations, and staff balance.'
        },
        {
            'metric': 'Top 5 Request Success',
            'value': f"{top5_pct:.1f}%",
            'status': 'On Target' if top5_pct >= 80 else 'Below Target',
            'why_it_matters': 'Shows how often the most important troop requests were delivered.'
        },
        {
            'metric': 'Top 10 Request Success',
            'value': f"{top10_pct:.1f}%",
            'status': 'On Target' if top10_pct >= 85 else 'Watch',
            'why_it_matters': 'Measures broader request coverage beyond only the top 5 items.'
        },
        {
            'metric': 'Schedule Validity',
            'value': 'Invalid' if schedule_invalid else 'Valid',
            'status': 'Needs Fix' if schedule_invalid else 'Pass',
            'why_it_matters': 'Invalid schedules include hard-rule conflicts and should be corrected before use.'
        },
        {
            'metric': 'Total Constraint Violations',
            'value': constraint_violations,
            'status': 'Good' if constraint_violations == 0 else 'Needs Review',
            'why_it_matters': 'Counts both hard and soft rule breaks that can reduce quality or feasibility.'
        },
        {
            'metric': 'Exclusive Double-Book Conflicts',
            'value': int(metrics.get('exclusive_double_book', 0)),
            'status': 'Pass' if int(metrics.get('exclusive_double_book', 0)) == 0 else 'Fail',
            'why_it_matters': 'Tracks impossible collisions in one-troop-only activities (for example Tower).'
        },
        {
            'metric': 'Beach Slot 2 Uses',
            'value': int(metrics.get('beach_slot_2_uses', 0)),
            'status': 'Good' if int(metrics.get('beach_slot_2_uses', 0)) == 0 else 'Penalty Risk',
            'why_it_matters': 'Beach activities in slot 2 are allowed but typically reduce quality score.'
        },
        {
            'metric': 'Staff Balance Variance',
            'value': round(float(metrics.get('staff_variance', 0.0)), 2),
            'status': 'Balanced' if float(metrics.get('staff_variance', 0.0)) <= 2.5 else 'Uneven',
            'why_it_matters': 'Lower variance means staff workload is spread more evenly across time slots.'
        },
        {
            'metric': 'Cluster Efficiency Penalties',
            'value': int(metrics.get('excess_cluster_days', 0)) + int(metrics.get('cluster_gaps', 0)),
            'status': 'Good' if (int(metrics.get('excess_cluster_days', 0)) + int(metrics.get('cluster_gaps', 0))) == 0 else 'Needs Tuning',
            'why_it_matters': 'Highlights scattered scheduling in high-movement areas that can create friction.'
        },
        {
            'metric': 'Exempted Misses (Top 5 / Top 10)',
            'value': f"{exempt_top5} / {exempt_top10}",
            'status': 'Info',
            'why_it_matters': 'Shows misses that are intentionally exempt due to formal exemption rules (for example 3-hour duplication or Tuesday HC/DG saturation).'
        },
        {
            'metric': 'Top 15 Request Success',
            'value': f"{top15_pct:.1f}%",
            'status': 'Info',
            'why_it_matters': 'Useful secondary quality signal for deeper preference satisfaction.'
        },
    ]

    metric_definitions = [
        {'name': 'Top 5 Success', 'plain_language': 'How often each troop got activities from its five most important requests.'},
        {'name': 'Constraint Violations', 'plain_language': 'How many scheduling rules were broken. Hard breaks can invalidate a week.'},
        {'name': 'Exclusive Double-Book', 'plain_language': 'When two troops are scheduled in a one-troop-only activity at the same time.'},
        {'name': 'Staff Variance', 'plain_language': 'How uneven the staff load is from slot to slot; lower is better.'},
        {'name': 'Cluster Efficiency', 'plain_language': 'How tightly related activities are grouped to avoid unnecessary spread and gaps.'},
        {'name': 'Beach Slot 2 Uses', 'plain_language': 'Beach activities scheduled in slot 2. These are generally less preferred than slot 1 or 3.'},
    ]

    raw_metrics = {}
    for key, value in metrics.items():
        if isinstance(value, (int, float, bool, str)):
            raw_metrics[key] = value
    for key in ('cluster_area_details', 'cluster_gap_details', 'cluster_improvement_targets'):
        if key in metrics:
            raw_metrics[key] = metrics.get(key)

    top_excess_areas = sorted(
        [
            (area_name, details.get('excess_days', 0))
            for area_name, details in cluster_area_details.items()
            if details.get('excess_days', 0) > 0
        ],
        key=lambda item: item[1],
        reverse=True,
    )
    cluster_diagnostics = {
        'areas_with_excess_days': top_excess_areas,
        'gap_patterns': cluster_gap_details,
        'improvement_targets': cluster_targets,
    }

    generated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    report = {
        'week_id': week_id,
        'week_name': week_name,
        'generated_at': generated_at,
        'executive_summary': {
            'health': health,
            'overall_score': final_score,
            'schedule_valid': not schedule_invalid,
            'total_troops': len(troops),
            'total_people': total_scouts + total_adults,
            'scouts': total_scouts,
            'adults': total_adults,
            'top5_success': round(top5_pct, 1),
            'top10_success': round(top10_pct, 1),
            'top15_success': round(top15_pct, 1),
        },
        'scorecard': scorecard,
        'recommended_actions': actions,
        'metric_definitions': metric_definitions,
        'raw_metrics': raw_metrics,
        'cluster_diagnostics': cluster_diagnostics,
    }

    lines = [
        f"Camp Scheduler Success Report - {week_name}",
        f"Generated: {generated_at}",
        "",
        "Executive Summary",
        f"- Health: {health}",
        f"- Overall Score: {final_score}",
        f"- Schedule Valid: {'Yes' if not schedule_invalid else 'No'}",
        f"- Troops: {len(troops)}",
        f"- People Scheduled: {total_scouts + total_adults} ({total_scouts} scouts, {total_adults} adults)",
        f"- Top 5 Success: {top5_pct:.1f}%",
        f"- Top 10 Success: {top10_pct:.1f}%",
        f"- Top 15 Success: {top15_pct:.1f}%",
        "",
        "Scorecard",
    ]
    for item in scorecard:
        lines.append(f"- {item['metric']}: {item['value']} [{item['status']}]")
        lines.append(f"  Why it matters: {item['why_it_matters']}")

    lines.append("")
    lines.append("Recommended Actions")
    for action in actions:
        lines.append(f"- {action}")

    lines.append("")
    lines.append("Metric Definitions (Plain Language)")
    for item in metric_definitions:
        lines.append(f"- {item['name']}: {item['plain_language']}")

    if top_excess_areas or cluster_gap_details:
        lines.append("")
        lines.append("Cluster Diagnostics")
        if top_excess_areas:
            for area_name, excess_days in top_excess_areas[:4]:
                lines.append(f"- Excess days: {area_name} -> {excess_days}")
        if cluster_gap_details:
            for detail in cluster_gap_details[:5]:
                lines.append(f"- Gap pattern: {detail.get('day')} {detail.get('area')} {detail.get('pattern')}")

    report['plain_text'] = "\n".join(lines)
    return report


def _extract_week_number(week_id):
    """Extract numeric week value from an id like tc_week3_troops."""
    try:
        marker = "tc_week"
        start = week_id.index(marker) + len(marker)
        end = week_id.index("_troops")
        return int(week_id[start:end])
    except Exception:
        return 9999


def _build_tc_season_report(weekly_rows):
    """Create a plain-language season report for TC weeks only."""
    if not weekly_rows:
        return {
            'season_name': 'TC Season',
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'error': 'No TC week data available for reporting.'
        }

    week_count = len(weekly_rows)
    valid_count = sum(1 for w in weekly_rows if not w['schedule_invalid'])
    invalid_count = week_count - valid_count

    avg_score = sum(w['final_score'] for w in weekly_rows) / week_count
    avg_top5 = sum(w['top5_pct'] for w in weekly_rows) / week_count
    avg_top10 = sum(w['top10_pct'] for w in weekly_rows) / week_count

    total_violations = sum(w['constraint_violations'] for w in weekly_rows)
    total_exclusive_double_books = sum(w['exclusive_double_book'] for w in weekly_rows)
    total_beach_slot_2 = sum(w['beach_slot_2_uses'] for w in weekly_rows)
    total_missing_top5 = sum(w['missing_top5'] for w in weekly_rows)
    total_excess_cluster_days = sum(w['excess_cluster_days'] for w in weekly_rows)
    total_cluster_gaps = sum(w['cluster_gaps'] for w in weekly_rows)
    avg_staff_variance = sum(w['staff_variance'] for w in weekly_rows) / week_count

    avg_excess_cluster_days = total_excess_cluster_days / week_count
    avg_cluster_gaps = total_cluster_gaps / week_count

    season_health = "Excellent"
    if invalid_count > 0:
        season_health = "Needs Immediate Fix"
    elif avg_top5 < 75 or total_violations > week_count * 2:
        season_health = "Needs Improvement"
    elif avg_top5 < 85 or total_violations > week_count:
        season_health = "Good"

    actions = []
    if invalid_count > 0:
        actions.append(f"Fix invalid weeks first ({invalid_count} of {week_count}).")
    if total_exclusive_double_books > 0:
        actions.append("Remove exclusive double-books (Tower/Delta/Super Troop/Rifle/etc.) where two troops share one-only slots.")
    if total_excess_cluster_days > 0 or total_cluster_gaps > 0:
        actions.append("Improve cluster flow: reduce excess cluster days and same-day cluster gaps.")
    if total_beach_slot_2 > 0:
        actions.append("Shift beach activities out of slot 2 when possible to improve quality.")
    if total_missing_top5 > 0:
        actions.append("Protect top-priority requests earlier in each week build to reduce Top 5 misses.")
    if not actions:
        actions.append("Season is stable with no major quality risks detected.")

    metric_definitions = [
        {'name': 'Excess Cluster Days', 'plain_language': 'Extra days used in clustered areas beyond what is needed. Lower is better for smoother flow.'},
        {'name': 'Cluster Gaps', 'plain_language': 'When cluster activities are split with an unnecessary hole (for example slot 1 and 3 used, slot 2 empty).'},
        {'name': 'Top 5 Success', 'plain_language': 'How often troops received one of their five most important requests.'},
        {'name': 'Constraint Violations', 'plain_language': 'How many rules were broken. Hard-rule breaks can make a week invalid.'},
        {'name': 'Staff Variance', 'plain_language': 'How uneven staff workload is across slots. Lower is better.'},
    ]

    generated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    report = {
        'season_name': 'TC Season',
        'generated_at': generated_at,
        'weeks_included': [w['week_id'] for w in weekly_rows],
        'executive_summary': {
            'health': season_health,
            'weeks_count': week_count,
            'valid_weeks': valid_count,
            'invalid_weeks': invalid_count,
            'average_score': round(avg_score, 1),
            'average_top5_success': round(avg_top5, 1),
            'average_top10_success': round(avg_top10, 1),
            'total_constraint_violations': total_violations,
            'total_excess_cluster_days': total_excess_cluster_days,
            'total_cluster_gaps': total_cluster_gaps,
            'average_excess_cluster_days': round(avg_excess_cluster_days, 2),
            'average_cluster_gaps': round(avg_cluster_gaps, 2),
        },
        'season_scorecard': [
            {
                'metric': 'Average Week Score',
                'value': round(avg_score, 1),
                'why_it_matters': 'Overall quality trend across all TC weeks.'
            },
            {
                'metric': 'Average Top 5 Success',
                'value': f"{avg_top5:.1f}%",
                'why_it_matters': 'How well your highest-priority requests are met over the season.'
            },
            {
                'metric': 'Total Constraint Violations',
                'value': total_violations,
                'why_it_matters': 'Total amount of rule pressure/failures across TC weeks.'
            },
            {
                'metric': 'Excess Cluster Days (Total / Avg)',
                'value': f"{total_excess_cluster_days} / {avg_excess_cluster_days:.2f}",
                'why_it_matters': 'Too many cluster days can increase movement and reduce flow.'
            },
            {
                'metric': 'Cluster Gaps (Total / Avg)',
                'value': f"{total_cluster_gaps} / {avg_cluster_gaps:.2f}",
                'why_it_matters': 'Cluster gaps indicate avoidable holes in clustered scheduling.'
            },
            {
                'metric': 'Average Staff Variance',
                'value': round(avg_staff_variance, 2),
                'why_it_matters': 'Lower numbers mean more balanced staff demand.'
            },
        ],
        'weeks': weekly_rows,
        'recommended_actions': actions,
        'metric_definitions': metric_definitions,
    }

    lines = [
        "Camp Scheduler Success Report - TC Season",
        f"Generated: {generated_at}",
        "",
        "Executive Summary (Simple Terms)",
        f"- Season Health: {season_health}",
        f"- Weeks Included: {week_count}",
        f"- Valid Weeks: {valid_count}",
        f"- Invalid Weeks: {invalid_count}",
        f"- Average Week Score: {avg_score:.1f}",
        f"- Average Top 5 Success: {avg_top5:.1f}%",
        f"- Average Top 10 Success: {avg_top10:.1f}%",
        f"- Total Constraint Violations: {total_violations}",
        f"- Excess Cluster Days: total {total_excess_cluster_days}, average {avg_excess_cluster_days:.2f} per week",
        f"- Cluster Gaps: total {total_cluster_gaps}, average {avg_cluster_gaps:.2f} per week",
        "",
        "Week-by-Week (TC Only)",
    ]
    for w in weekly_rows:
        lines.append(
            f"- {w['week_name']}: Score {w['final_score']}, Top5 {w['top5_pct']:.1f}%, "
            f"Violations {w['constraint_violations']}, Excess Cluster Days {w['excess_cluster_days']}, "
            f"Cluster Gaps {w['cluster_gaps']}, Valid {'Yes' if not w['schedule_invalid'] else 'No'}"
        )

    lines.append("")
    lines.append("Recommended Actions")
    for action in actions:
        lines.append(f"- {action}")

    lines.append("")
    lines.append("Metric Definitions (Plain Language)")
    for item in metric_definitions:
        lines.append(f"- {item['name']}: {item['plain_language']}")

    report['plain_text'] = "\n".join(lines)
    return report


@app.route('/api/report/<week_id>')
def get_success_report(week_id):
    """Return a plain-language success report for one week."""
    if week_id not in WEEK_METADATA:
        return jsonify({'error': 'Week not found'}), 404

    try:
        from utils.regression_checker import evaluate_week

        meta = WEEK_METADATA[week_id]
        week_file_path = str(meta['file'])
        metrics = evaluate_week(week_file_path)
        data = get_week_data(week_id)
        report = _build_success_report(week_id, meta['week_number'], metrics, data)

        if request.args.get('download') == '1':
            filename = f"{week_id}_success_report.txt"
            return Response(
                report['plain_text'],
                mimetype='text/plain',
                headers={'Content-Disposition': f'attachment; filename="{filename}"'}
            )

        return jsonify(report)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/report/season')
def get_tc_season_report():
    """Return a season-level report for TC weeks only."""
    try:
        from utils.regression_checker import evaluate_week

        tc_week_ids = [week_id for week_id in WEEK_METADATA.keys() if week_id.startswith('tc_week') and week_id.endswith('_troops')]
        tc_week_ids = sorted(tc_week_ids, key=_extract_week_number)

        weekly_rows = []
        skipped_weeks = []
        for week_id in tc_week_ids:
            try:
                meta = WEEK_METADATA[week_id]
                metrics = evaluate_week(str(meta['file']))
                week_data = get_week_data(week_id)
                troops = week_data.get('troops', []) if week_data else []

                row = {
                    'week_id': week_id,
                    'week_name': meta['week_number'],
                    'health': _determine_week_health(
                        bool(metrics.get('schedule_invalid', False)),
                        float(metrics.get('top5_pct', 0.0)),
                        int(metrics.get('constraint_violations', 0))
                    ),
                    'final_score': int(metrics.get('final_score', 0)),
                    'top5_pct': float(metrics.get('top5_pct', 0.0)),
                    'top10_pct': float(metrics.get('top10_pct', 0.0)),
                    'constraint_violations': int(metrics.get('constraint_violations', 0)),
                    'schedule_invalid': bool(metrics.get('schedule_invalid', False)),
                    'exclusive_double_book': int(metrics.get('exclusive_double_book', 0)),
                    'beach_slot_2_uses': int(metrics.get('beach_slot_2_uses', 0)),
                    'missing_top5': int(metrics.get('missing_top5', 0)),
                    'excess_cluster_days': int(metrics.get('excess_cluster_days', 0)),
                    'cluster_gaps': int(metrics.get('cluster_gaps', 0)),
                    'staff_variance': float(metrics.get('staff_variance', 0.0)),
                    'troop_count': len(troops),
                }
                weekly_rows.append(row)
            except Exception:
                skipped_weeks.append(week_id)

        if not weekly_rows:
            return jsonify({'error': 'Could not generate TC season report for any week.'}), 500

        report = _build_tc_season_report(weekly_rows)
        if skipped_weeks:
            report['skipped_weeks'] = skipped_weeks

        if request.args.get('download') == '1':
            filename = "tc_season_success_report.txt"
            return Response(
                report['plain_text'],
                mimetype='text/plain',
                headers={'Content-Disposition': f'attachment; filename="{filename}"'}
            )

        return jsonify(report)
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
    troops, schedule, unscheduled_data, sailing_half_fills = generate_schedule(troops_file)
    
    # Save to cache using io_handler
    save_schedule_to_json(schedule, troops, str(schedule_file), unscheduled_data, sailing_half_fills)
    
    # Update memory cache
    WEEK_DATA[week_id] = {
        'troops': troops,
        'schedule': schedule,
        'unscheduled': unscheduled_data,
        'sailing_half_fills': sailing_half_fills,
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
        sailing_half_fills = data.get('sailing_half_fills', {}) or {}
        
        troop = next((t for t in troops if t.name == troop_name), None)
        if not troop:
            return {"error": "Troop not found"}, 404
        
        entries = schedule.get_troop_schedule(troop)
        
        # Group by day and slot
        schedule_grid = {}
        for day in Day:
            schedule_grid[day.name] = {1: None, 2: None, 3: None}
        
        def _half_slot_position(effective_slots, start_slot, cell_slot, day_name=None):
            """Layout helper for a 1.5-slot activity (Sailing).

            Session 1 (start_slot=1): slot 1 is full, slot 2 is a split cell
            with the activity in the TOP half (+30-min tail after slot 1).
            Session 2 (start_slot=2): slot 2 is a split cell with the activity
            in the BOTTOM half (30-min gap at the top), slot 3 is full.
            Thursday has only 2 slots and its single Sailing block is awarded
            to the biggest troop as a full 2-hour activity (no split).
            Returns 'top' / 'bottom' / None.
            """
            if effective_slots != 1.5:
                return None
            if day_name == 'THURSDAY':
                return None
            if start_slot == 1 and cell_slot == 2:
                return 'top'
            if start_slot == 2 and cell_slot == 2:
                return 'bottom'
            return None

        for entry in entries:
            day_name = entry.time_slot.day.name
            slot_num = entry.time_slot.slot_number

            # Start slot = earliest slot this activity occupies for this troop on this day.
            same_activity_slots = [
                e.time_slot.slot_number for e in entries
                if e.activity.name == entry.activity.name
                and e.time_slot.day == entry.time_slot.day
            ]
            start_slot = min(same_activity_slots) if same_activity_slots else slot_num
            is_continuation = slot_num > start_slot

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
            
            effective_slots = schedule._get_effective_slots(entry.activity, troop)
            # Thursday Sailing is awarded to the biggest troop as a full 2-hour
            # block occupying both Thursday slots (no 30-min buffer / fill).
            # Report 2.0 to the frontend so the duration shows "(2 hrs)".
            if entry.activity.name == 'Sailing' and day_name == 'THURSDAY':
                effective_slots = 2.0
            # Half-slot layout for 1.5-slot activities (Sailing). The 30-min
            # dead time in the split cell will eventually be filled by Phase
            # C.6b (balls during Sailing) via `half_slot_fill`.
            half_slot_position = _half_slot_position(effective_slots, start_slot, slot_num, day_name)
            half_slot_fill = None
            if half_slot_position is not None and entry.activity.name == 'Sailing':
                fill_key = make_sailing_fill_key(day_name, slot_num, troop.name)
                fill_info = sailing_half_fills.get(fill_key)
                if fill_info:
                    half_slot_fill = fill_info.get('activity_name')
            schedule_grid[day_name][slot_num] = {
                'activity': entry.activity.name,
                'is_continuation': is_continuation,
                'is_half_slot': half_slot_position is not None,
                'half_slot_position': half_slot_position,
                # Preserved for any older consumer: true iff the Sailing tail
                # sits in the TOP half of the cell (session 1 slot 2).
                'is_half_slot_continuation': half_slot_position == 'top',
                'half_slot_fill': half_slot_fill,
                'is_spillover': is_spillover,
                'priority': troop.get_priority(entry.activity.name),
                'zone': entry.activity.zone.name if entry.activity.zone else None,
                'slots': effective_slots  # Add slots information for multi-slot display
            }
            
            # Manually inject continuation slots for the frontend if they are missing
            slots_needed = int(effective_slots + 0.5)
            if slots_needed > 1 and not is_continuation:
                for offset in range(1, slots_needed):
                    next_slot_num = slot_num + offset
                    max_slot = 2 if day_name == 'THURSDAY' else 3
                    if next_slot_num <= max_slot:
                        if schedule_grid[day_name][next_slot_num] is None:
                            inj_half = _half_slot_position(effective_slots, start_slot, next_slot_num, day_name)
                            inj_fill = None
                            if inj_half is not None and entry.activity.name == 'Sailing':
                                fill_key = make_sailing_fill_key(day_name, next_slot_num, troop.name)
                                fill_info = sailing_half_fills.get(fill_key)
                                if fill_info:
                                    inj_fill = fill_info.get('activity_name')
                            schedule_grid[day_name][next_slot_num] = {
                                'activity': entry.activity.name,
                                'is_continuation': True,
                                'is_half_slot': inj_half is not None,
                                'half_slot_position': inj_half,
                                'is_half_slot_continuation': inj_half == 'top',
                                'half_slot_fill': inj_fill,
                                'is_spillover': is_spillover,
                                'priority': troop.get_priority(entry.activity.name),
                                'zone': entry.activity.zone.name if entry.activity.zone else None,
                                'slots': effective_slots
                            }
        
        return jsonify({
            'troop': troop_name,
            'commissioner': troop.commissioner,
            'scouts': troop.scouts,
            'adults': troop.adults,
            'schedule': schedule_grid,
            'credited_fill_activities': sorted(get_request_credit_fill_activities(troop, sailing_half_fills)),
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
    sailing_half_fills = data.get('sailing_half_fills', {}) or {}
    troops = data.get('troops', [])
    
    # Map area names to activity names
    area_to_activities = {
        'Boats': ['Troop Canoe', 'Troop Kayak', 'Canoe Snorkel', 'Nature Canoe', 'Float for Floats'],
        'Balls': ['Gaga Ball', '9 Square'],
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
    
    credited_fill_activities_by_troop = {
        troop.name: get_request_credit_fill_activities(troop, sailing_half_fills)
        for troop in troops
    }

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
        scheduled_activities |= credited_fill_activities_by_troop.get(troop.name, set())
        prefs_achieved = sum(1 for p in troop.preferences if p in scheduled_activities)
        prefs_total = len(troop.preferences)
        
        effective_slots = schedule._get_effective_slots(entry.activity, troop)
        slots_needed = int(effective_slots + 0.5)
        
        item_data = {
            'troop': entry.troop.name,
            'activity': entry.activity.name,
            'priority': entry.troop.get_priority(entry.activity.name),
            'scouts': entry.troop.scouts,
            'adults': entry.troop.adults,
            'prefs_achieved': prefs_achieved,
            'prefs_total': prefs_total
        }
        
        existing = [item for item in schedule_grid[day_name][slot_num] if item['troop'] == troop.name and item['activity'] == entry.activity.name]
        if not existing:
            schedule_grid[day_name][slot_num].append(item_data)
            
        if slots_needed > 1:
            is_start = not any(
                e.activity.name == entry.activity.name and e.time_slot.day == entry.time_slot.day and e.time_slot.slot_number < slot_num
                for e in area_entries if e.troop == troop
            )
            if is_start:
                for offset in range(1, slots_needed):
                    next_slot_num = slot_num + offset
                    max_slot = 2 if day_name == 'THURSDAY' else 3
                    if next_slot_num <= max_slot:
                        next_existing = [item for item in schedule_grid[day_name][next_slot_num] if item['troop'] == troop.name and item['activity'] == entry.activity.name]
                        if not next_existing:
                            schedule_grid[day_name][next_slot_num].append(item_data)

    troop_lookup = {troop.name: troop for troop in troops}
    for fill in sailing_half_fills.values():
        activity_name = fill.get('activity_name')
        if activity_name not in area_activities:
            continue
        day_name = fill.get('day')
        slot_num = fill.get('slot')
        troop_name = fill.get('troop_name')
        troop = troop_lookup.get(troop_name)
        if not day_name or slot_num is None or troop is None:
            continue

        troop_entries = [e for e in schedule.entries if e.troop == troop]
        scheduled_activities = {e.activity.name for e in troop_entries}
        scheduled_activities |= credited_fill_activities_by_troop.get(troop.name, set())
        prefs_achieved = sum(1 for p in troop.preferences if p in scheduled_activities)
        prefs_total = len(troop.preferences)

        schedule_grid[day_name][slot_num].append({
            'troop': troop.name,
            'activity': activity_name,
            'priority': troop.get_priority(activity_name),
            'scouts': troop.scouts,
            'adults': troop.adults,
            'prefs_achieved': prefs_achieved,
            'prefs_total': prefs_total,
            'fill_half': fill.get('fill_half'),
            'is_half_fill': True,
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
    """Get Balls (Gaga Ball, 9 Square) schedule, including Sailing half-fills."""
    week = request.args.get('week', current_week)
    if week not in WEEK_METADATA:
        week = current_week
    data = get_week_data(week)
    schedule = data['schedule']
    troops = data['troops']
    sailing_half_fills = data.get('sailing_half_fills', {}) or {}
    
    balls_activities = ['Gaga Ball', '9 Square']
    
    # Create grid structure:
    # {activity: {day: {slot: [item, ...]}}}
    # where each item is either a full scheduled occupancy or a 30-minute
    # Sailing half-fill occupancy.
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
        
        balls_grid[activity_name][day_name][slot_num].append({
            'troop': troop_name,
            'is_half_fill': False,
            'fill_half': None,
        })

    troop_lookup = {troop.name: troop for troop in troops}
    for fill in sailing_half_fills.values():
        activity_name = fill.get('activity_name')
        if activity_name not in balls_activities:
            continue

        day_name = fill.get('day')
        slot_num = fill.get('slot')
        troop_name = fill.get('troop_name')
        troop = troop_lookup.get(troop_name)
        if not day_name or slot_num is None or troop is None:
            continue

        balls_grid[activity_name][day_name][slot_num].append({
            'troop': troop_name,
            'is_half_fill': True,
            'fill_half': fill.get('fill_half'),
        })
    
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
        
        effective_slots = schedule._get_effective_slots(entry.activity, entry.troop)
        slots_needed = int(effective_slots + 0.5)
        
        item_data = {
            'troop': entry.troop.name,
            'activity': entry.activity.name,
            'priority': entry.troop.get_priority(entry.activity.name),
            'scouts': entry.troop.scouts,
            'adults': entry.troop.adults
        }
        
        existing = [item for item in schedule_grid[day_name][slot_num] if item['troop'] == entry.troop.name and item['activity'] == entry.activity.name]
        if not existing:
            schedule_grid[day_name][slot_num].append(item_data)
            
        if slots_needed > 1:
            is_start = not any(
                e.activity.name == entry.activity.name and e.time_slot.day == entry.time_slot.day and e.time_slot.slot_number < slot_num
                for e in staff_entries if e.troop == entry.troop
            )
            if is_start:
                for offset in range(1, slots_needed):
                    next_slot_num = slot_num + offset
                    max_slot = 2 if day_name == 'THURSDAY' else 3
                    if next_slot_num <= max_slot:
                        next_existing = [item for item in schedule_grid[day_name][next_slot_num] if item['troop'] == entry.troop.name and item['activity'] == entry.activity.name]
                        if not next_existing:
                            schedule_grid[day_name][next_slot_num].append(item_data)
    
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
    
    # ALWAYS use pre-calculated unscheduled data from scheduler
    # This ensures consistency with the scheduler's logic and prevents drift
    if 'unscheduled' in data and data['unscheduled'] is not None:
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

    # No fallback by design: inaccurate reconstruction is forbidden.
    return jsonify({
        'error': 'Authoritative unscheduled data missing from schedule JSON.',
        'required_source': 'schedule_json.unscheduled.{troop}.top5/top10',
        'week': week
    }), 409

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
