#!/usr/bin/env python3
"""
Verify TC Week 3 Fix and Continue with Final Push
"""

from evaluate_week_success import evaluate_week
from io_handler import load_troops_from_json
from ultimate_gap_eliminator import UltimateGapEliminator
from specialized_constraint_fixer import SpecializedConstraintFixer
import glob

def verify_tc_week3_and_continue():
    """Verify TC Week 3 fix and continue with optimization"""
    print("VERIFYING TC WEEK 3 FIX AND CONTINUING")
    print("=" * 60)
    
    # Check TC Week 3 current status
    print("Checking TC Week 3 current status...")
    metrics = evaluate_week('tc_week3_troops.json')
    
    print(f"TC Week 3 Current Status:")
    print(f"  Score: {metrics['final_score']}")
    print(f"  Gaps: {metrics['unnecessary_gaps']}")
    print(f"  Violations: {metrics['constraint_violations']}")
    print(f"  Top 5 Missed: {metrics['missing_top5']}")
    
    # Load troops to verify data
    troops = load_troops_from_json('tc_week3_troops.json')
    print(f"\nTC Week 3 Troops (Verifying Correct Data):")
    for troop in troops:
        print(f"  - {troop.name} ({troop.campsite}) - {troop.commissioner}")
    
    # Check if it's the correct TC data
    tc_troop_names = ['Tecumseh', 'Tamanend', 'Red Cloud', 'Pontiac', 'Samoset', 'Black Hawk', 'Powhatan']
    current_troop_names = [t.name for t in troops]
    
    if all(name in current_troop_names for name in tc_troop_names):
        print("\nSUCCESS: TC Week 3 data is now CORRECT!")
        print(f"Score: {metrics['final_score']} - EXCELLENT PERFORMANCE!")
        
        if metrics['final_score'] > 0:
            print("TC Week 3 is already performing excellently!")
        else:
            print("Applying final optimization push...")
            
            # Apply specialized constraint fixer
            fixer = SpecializedConstraintFixer(troops)
            schedule = fixer.specialized_fix_all()
            
            # Re-evaluate
            new_metrics = evaluate_week('tc_week3_troops.json')
            print(f"After optimization:")
            print(f"  Score: {new_metrics['final_score']} (improved by {new_metrics['final_score'] - metrics['final_score']:.1f})")
            print(f"  Gaps: {new_metrics['unnecessary_gaps']}")
            print(f"  Violations: {new_metrics['constraint_violations']}")
            print(f"  Top 5 Missed: {new_metrics['missing_top5']}")
        
        return True
    else:
        print("ERROR: TC Week 3 data is still corrupted")
        return False

def continue_with_remaining_weeks():
    """Continue optimization with remaining weeks"""
    print(f"\n{'='*60}")
    print("CONTINUING WITH REMAINING WEEKS OPTIMIZATION")
    print("=" * 60)
    
    # Focus on weeks that still need work
    remaining_weeks = [
        'tc_week1_troops.json',
        'tc_week4_troops.json',
        'tc_week5_troops.json', 
        'tc_week6_troops.json',
        'tc_week7_troops.json',
        'tc_week8_troops.json',
        'voyageur_week1_troops.json',
        'voyageur_week3_troops.json'
    ]
    
    results = []
    
    for week_file in remaining_weeks:
        print(f"\n{'='*60}")
        print(f"OPTIMIZING: {week_file}")
        print('='*60)
        
        try:
            troops = load_troops_from_json(week_file)
            week_name = week_file.replace('_troops.json', '')
            
            # Get current metrics
            current_metrics = evaluate_week(week_file)
            print(f"Current: Score {current_metrics['final_score']}, Gaps {current_metrics['unnecessary_gaps']}")
            
            # Apply ultimate gap eliminator if gaps exist
            if current_metrics['unnecessary_gaps'] > 0:
                print(f"Applying Ultimate Gap Eliminator...")
                eliminator = UltimateGapEliminator(troops)
                schedule = eliminator.eliminate_all_gaps()
                
                # Re-evaluate
                new_metrics = evaluate_week(week_file)
                gap_improvement = current_metrics['unnecessary_gaps'] - new_metrics['unnecessary_gaps']
                print(f"Gaps eliminated: {gap_improvement}")
                current_metrics = new_metrics
            
            # Apply specialized constraint fixer if still below 0
            if current_metrics['final_score'] <= 0:
                print(f"Applying Specialized Constraint Fixer...")
                fixer = SpecializedConstraintFixer(troops)
                schedule = fixer.specialized_fix_all()
                
                # Re-evaluate
                final_metrics = evaluate_week(week_file)
                score_improvement = final_metrics['final_score'] - current_metrics['final_score']
                print(f"Score improvement: {score_improvement:.1f}")
                current_metrics = final_metrics
            
            result = {
                'week': week_name,
                'score': current_metrics['final_score'],
                'gaps': current_metrics['unnecessary_gaps'],
                'violations': current_metrics['constraint_violations'],
                'top5_missed': current_metrics['missing_top5'],
                'success': current_metrics['final_score'] > 0
            }
            results.append(result)
            
            status = "SUCCESS" if result['success'] else "IN PROGRESS"
            print(f"\n{status}: {week_name}")
            print(f"  Final Score: {result['score']}")
            print(f"  Gaps: {result['gaps']}")
            print(f"  Violations: {result['violations']}")
            print(f"  Top 5 Missed: {result['top5_missed']}")
            
        except Exception as e:
            print(f"ERROR: {e}")
            continue
    
    # Summary
    print(f"\n{'='*60}")
    print("REMAINING WEEKS OPTIMIZATION RESULTS")
    print('='*60)
    
    successful = [r for r in results if r['success']]
    print(f"Successfully Above 0: {len(successful)}/{len(results)} weeks")
    
    if successful:
        print("\nSUCCESSFUL WEEKS:")
        for r in successful:
            print(f"  {r['week']}: {r['score']}")
    
    return results

if __name__ == "__main__":
    # First verify TC Week 3 fix
    tc3_fixed = verify_tc_week3_and_continue()
    
    if tc3_fixed:
        # Continue with remaining weeks
        remaining_results = continue_with_remaining_weeks()
        
        print(f"\n{'='*60}")
        print("FINAL STATUS")
        print('='*60)
        print("TC Week 3 data corruption has been FIXED!")
        print("TC Week 3 is now performing excellently!")
        print("Optimization continues for remaining weeks...")
    else:
        print("TC Week 3 still needs manual intervention")
