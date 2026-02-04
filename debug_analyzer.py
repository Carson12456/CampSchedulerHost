#!/usr/bin/env python3
"""
Debug the unscheduled analyzer to see what it's actually calculating
"""

from core.services.unscheduled_analyzer import UnscheduledAnalyzer

def debug_analyzer():
    """Debug what the unscheduled analyzer is calculating."""
    print("DEBUGGING UNSCHEDULED ANALYZER")
    print("=" * 60)
    
    analyzer = UnscheduledAnalyzer()
    analyzer.analyze_all_weeks('schedules')
    results = analyzer.get_season_summary()
    
    print('ANALYZER RESULTS:')
    print(f'Total weeks: {results.get("total_weeks", 0)}')
    print(f'Total Top5 slots: {results.get("total_top5_slots", 0)}')
    print(f'Total counted misses: {results.get("total_counted_misses", 0)}')
    print(f'Success rate: {results.get("season_success_rate", 0):.1f}%')
    print(f'Weeks with issues: {results.get("weeks_with_issues", 0)}')
    
    print()
    print('WEEK DETAILS:')
    week_details = results.get('week_details', {})
    for week_name, details in week_details.items():
        print(f'{week_name}:')
        print(f'  Total troops: {details.get("total_troops", 0)}')
        print(f'  Top5 slots: {details.get("total_top5_slots", 0)}')
        print(f'  Counted misses: {details.get("counted_misses", 0)}')
        print(f'  Success rate: {details.get("success_rate", 0):.1f}%')
        print(f'  Exempt misses: {details.get("exempt_misses", 0)}')
        print(f'  Non-exempt misses: {details.get("non_exempt_misses", 0)}')

if __name__ == "__main__":
    debug_analyzer()
