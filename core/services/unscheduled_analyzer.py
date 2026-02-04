"""
Unscheduled Activities Analyzer - Core Service

Robust analysis of unscheduled activities from schedule JSON files.
Provides detailed top 5 detection, exemption analysis, and placement suggestions.
This is the authoritative source for top 5 missed detection using unscheduled JSON.
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import json
from pathlib import Path


@dataclass
class MissedTop5:
    """Represents a missed Top 5 activity with detailed analysis."""
    troop_name: str
    activity_name: str
    rank: int
    is_exempt: bool
    exemption_reason: Optional[str] = None
    placement_suggestions: List[str] = None
    constraint_conflicts: List[str] = None
    
    def __post_init__(self):
        if self.placement_suggestions is None:
            self.placement_suggestions = []
        if self.constraint_conflicts is None:
            self.constraint_conflicts = []


@dataclass
class WeekAnalysis:
    """Complete analysis for a week's unscheduled activities."""
    week_name: str
    total_troops: int
    total_top5_slots: int
    missed_top5: List[MissedTop5]
    exempt_misses: int
    counted_misses: int
    success_rate: float
    
    @property
    def non_exempt_misses(self) -> List[MissedTop5]:
        """Get only non-exempt missed Top 5 activities."""
        return [miss for miss in self.missed_top5 if not miss.is_exempt]


class UnscheduledAnalyzer:
    """
    Analyzes unscheduled activities from schedule JSON files.
    
    This is the authoritative source for top 5 detection using the unscheduled
    section of schedule JSON files, as specified in .cursorrules.
    """
    
    # Exemption rule definitions (from .cursorrules)
    THREE_HOUR_ACTIVITIES = {"Tamarac Wildlife Refuge", "Itasca State Park", "Back of the Moon"}
    HC_DG_ACTIVITIES = {"History Center", "Disc Golf"}
    
    def __init__(self):
        self.week_analyses: Dict[str, WeekAnalysis] = {}
    
    def analyze_week_from_schedule_json(self, schedule_path: str) -> WeekAnalysis:
        """
        Analyze a single week from its schedule JSON file.
        
        Args:
            schedule_path: Path to the schedule JSON file
            
        Returns:
            WeekAnalysis with complete top 5 analysis
        """
        schedule_path = Path(schedule_path)
        if not schedule_path.exists():
            raise FileNotFoundError(f"Schedule file not found: {schedule_path}")
        
        with open(schedule_path, 'r', encoding='utf-8') as f:
            schedule_data = json.load(f)
        
        week_name = schedule_path.stem.replace("_schedule", "")
        unscheduled = schedule_data.get('unscheduled', {})
        
        return self._analyze_week_unscheduled(week_name, unscheduled)
    
    def analyze_all_weeks(self, schedules_dir: str = "schedules") -> Dict[str, WeekAnalysis]:
        """
        Analyze all weeks in the schedules directory.
        
        Args:
            schedules_dir: Directory containing schedule JSON files
            
        Returns:
            Dictionary mapping week names to WeekAnalysis objects
        """
        schedules_path = Path(schedules_dir)
        if not schedules_path.exists():
            raise FileNotFoundError(f"Schedules directory not found: {schedules_dir}")
        
        schedule_files = list(schedules_path.glob("*_schedule.json"))
        
        for schedule_file in schedule_files:
            try:
                analysis = self.analyze_week_from_schedule_json(schedule_file)
                self.week_analyses[analysis.week_name] = analysis
            except Exception as e:
                print(f"Error analyzing {schedule_file}: {e}")
                continue
        
        return self.week_analyses
    
    def _analyze_week_unscheduled(self, week_name: str, unscheduled: Dict) -> WeekAnalysis:
        """Analyze unscheduled activities for a single week."""
        missed_top5 = []
        total_troops = len(unscheduled)
        total_top5_slots = 0
        
        # Analyze each troop's unscheduled activities
        for troop_name, troop_data in unscheduled.items():
            top5_data = troop_data.get('top5', [])
            # Each troop has 5 Top 5 slots, regardless of how many they missed
            total_top5_slots += 5
            
            for activity_data in top5_data:
                missed = self._create_missed_top5(
                    troop_name, activity_data, week_name
                )
                if missed:
                    missed_top5.append(missed)
        
        # Calculate statistics
        exempt_misses = sum(1 for miss in missed_top5 if miss.is_exempt)
        counted_misses = len(missed_top5) - exempt_misses
        success_rate = 100.0 * (total_top5_slots - counted_misses) / max(1, total_top5_slots)
        
        return WeekAnalysis(
            week_name=week_name,
            total_troops=total_troops,
            total_top5_slots=total_top5_slots,
            missed_top5=missed_top5,
            exempt_misses=exempt_misses,
            counted_misses=counted_misses,
            success_rate=success_rate
        )
    
    def _create_missed_top5(self, troop_name: str, activity_data: Dict, week_name: str) -> Optional[MissedTop5]:
        """Create a MissedTop5 object with exemption analysis."""
        activity_name = activity_data.get('name', '')
        rank = activity_data.get('rank', 0)
        is_exempt = activity_data.get('is_exempt', False)
        
        if not activity_name or rank == 0:
            return None
        
        missed = MissedTop5(
            troop_name=troop_name,
            activity_name=activity_name,
            rank=rank,
            is_exempt=is_exempt
        )
        
        # Analyze exemption reason and provide placement suggestions
        if is_exempt:
            missed.exemption_reason = self._determine_exemption_reason(activity_name)
        else:
            missed.placement_suggestions = self._generate_placement_suggestions(activity_name, rank)
            missed.constraint_conflicts = self._identify_constraint_conflicts(activity_name)
        
        return missed
    
    def _determine_exemption_reason(self, activity_name: str) -> str:
        """Determine why an activity is exempt based on .cursorrules."""
        if activity_name in self.THREE_HOUR_ACTIVITIES:
            return "2nd+ 3-hour activity (troop already has one)"
        elif activity_name in self.HC_DG_ACTIVITIES:
            return "HC/DG when all Tuesday slots allocated to higher-priority troops"
        elif "capacity" in activity_name.lower():
            return "Capacity-constrained activity"
        else:
            return "Exemption specified in schedule data"
    
    def _generate_placement_suggestions(self, activity_name: str, rank: int) -> List[str]:
        """Generate placement suggestions for non-exempt missed activities."""
        suggestions = []
        
        # General suggestions based on activity type
        if "Beach" in activity_name or activity_name in ["Aqua Trampoline", "Water Polo", "Greased Watermelon", "Troop Swim"]:
            suggestions.append("Try beach slots 1 or 3 (or slot 2 on Thursday)")
            suggestions.append("Consider sharing Aqua Trampoline if troop size ≤ 16")
        elif activity_name in ["Climbing Tower", "Rifle Range", "Archery"]:
            suggestions.append("Check exclusive area availability")
            suggestions.append("Consider commissioner day assignments")
        elif activity_name in self.THREE_HOUR_ACTIVITIES:
            suggestions.append("Requires full day (3 consecutive slots)")
            suggestions.append("Schedule early in the week")
        elif activity_name in self.HC_DG_ACTIVITIES:
            suggestions.append("Tuesday only - check Tuesday slot availability")
        
        # Priority-based suggestions
        if rank <= 2:
            suggestions.append("High priority - consider swapping lower priority activities")
            suggestions.append("Check for constraint-aware displacement opportunities")
        
        # Add Delta-specific suggestions
        if activity_name == "Delta":
            suggestions.append("Should pair with Sailing on same day")
            suggestions.append("Schedule in slot 1 or 3 when paired with Sailing")
        
        return suggestions
    
    def _identify_constraint_conflicts(self, activity_name: str) -> List[str]:
        """Identify potential constraint conflicts for missed activities."""
        conflicts = []
        
        # Check for common constraint conflicts
        if activity_name in ["Troop Rifle", "Troop Shotgun"]:
            conflicts.append("Cannot be same day as other accuracy activities")
        elif activity_name == "Delta":
            conflicts.append("Cannot be adjacent to Tower or Outdoor Skills")
            conflicts.append("Should pair with Sailing on same day")
        elif activity_name == "Sailing":
            conflicts.append("1.5 slots (2.0 on Thursday)")
            conflicts.append("Should pair with Delta on same day")
        elif "Beach" in activity_name or activity_name in ["Aqua Trampoline", "Water Polo", "Greased Watermelon"]:
            conflicts.append("Beach activities prefer slots 1 or 3")
            conflicts.append("Cannot pair with other beach activities same day")
        
        return conflicts
    
    def get_season_summary(self) -> Dict[str, Any]:
        """Generate comprehensive season summary across all analyzed weeks."""
        if not self.week_analyses:
            return {"error": "No weeks analyzed. Call analyze_all_weeks() first."}
        
        total_top5_slots = sum(week.total_top5_slots for week in self.week_analyses.values())
        total_exempt_misses = sum(week.exempt_misses for week in self.week_analyses.values())
        total_counted_misses = sum(week.counted_misses for week in self.week_analyses.values())
        
        season_success_rate = 100.0 * (total_top5_slots - total_counted_misses) / max(1, total_top5_slots)
        
        # Find weeks with issues
        weeks_with_issues = {
            name: analysis for name, analysis in self.week_analyses.items()
            if analysis.counted_misses > 0
        }
        
        return {
            "total_weeks": len(self.week_analyses),
            "total_top5_slots": total_top5_slots,
            "total_exempt_misses": total_exempt_misses,
            "total_counted_misses": total_counted_misses,
            "season_success_rate": season_success_rate,
            "weeks_with_issues": len(weeks_with_issues),
            "problem_weeks": {name: {
                "counted_misses": analysis.counted_misses,
                "success_rate": analysis.success_rate
            } for name, analysis in weeks_with_issues.items()},
            "week_details": {
                name: {
                    "total_troops": analysis.total_troops,
                    "total_top5_slots": analysis.total_top5_slots,
                    "exempt_misses": analysis.exempt_misses,
                    "counted_misses": analysis.counted_misses,
                    "success_rate": analysis.success_rate,
                    "non_exempt_misses": len(analysis.non_exempt_misses)
                } for name, analysis in self.week_analyses.items()
            }
        }
    
    def get_detailed_miss_report(self, week_name: str = None) -> Dict[str, Any]:
        """Get detailed report of missed Top 5 activities with suggestions."""
        if week_name:
            if week_name not in self.week_analyses:
                return {"error": f"Week {week_name} not analyzed"}
            weeks_to_report = {week_name: self.week_analyses[week_name]}
        else:
            weeks_to_report = self.week_analyses
        
        report = {}
        for name, analysis in weeks_to_report.items():
            missed_details = []
            for miss in analysis.non_exempt_misses:
                missed_details.append({
                    "troop": miss.troop_name,
                    "activity": miss.activity_name,
                    "rank": miss.rank,
                    "placement_suggestions": miss.placement_suggestions,
                    "constraint_conflicts": miss.constraint_conflicts
                })
            
            report[name] = {
                "week_success_rate": analysis.success_rate,
                "counted_misses": analysis.counted_misses,
                "missed_activities": missed_details
            }
        
        return report
    
    def validate_against_schedule_entries(self, week_name: str, schedule_path: str) -> Dict[str, Any]:
        """
        Cross-validate unscheduled analysis against scheduled entries.
        This helps detect discrepancies in the unscheduled JSON data.
        """
        if week_name not in self.week_analyses:
            return {"error": f"Week {week_name} not analyzed"}
        
        schedule_path = Path(schedule_path)
        if not schedule_path.exists():
            return {"error": f"Schedule file not found: {schedule_path}"}
        
        with open(schedule_path, 'r', encoding='utf-8') as f:
            schedule_data = json.load(f)
        
        entries = schedule_data.get('entries', [])
        scheduled_activities = {}
        
        # Build scheduled activities lookup
        for entry in entries:
            troop = entry.get('troop_name', '')
            activity = entry.get('activity_name', '')
            if troop and activity:
                scheduled_activities.setdefault(troop, set()).add(activity)
        
        # Validate unscheduled data against scheduled entries
        analysis = self.week_analyses[week_name]
        validation_results = {
            "week_name": week_name,
            "total_unscheduled_top5": len(analysis.missed_top5),
            "validation_errors": [],
            "discrepancies": []
        }
        
        for miss in analysis.missed_top5:
            troop_scheduled = scheduled_activities.get(miss.troop_name, set())
            if miss.activity_name in troop_scheduled:
                validation_results["discrepancies"].append({
                    "troop": miss.troop_name,
                    "activity": miss.activity_name,
                    "issue": "Activity marked as unscheduled but found in scheduled entries"
                })
        
        return validation_results
