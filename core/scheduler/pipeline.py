"""
Scheduling phase pipeline orchestration mixin.

This module contains the high-level A->D phase flow used by the scheduler.
"""

from ..models import Day, Schedule


class SchedulingPipelineMixin:
    """Coordinates the full scheduling lifecycle across all phases."""

    def _enforce_sailing_slot_exclusivity(self) -> None:
        """
        Normalize final Sailing occupancy to the BRAIN 90-minute capacity model.

        Final schedules allow the formal slot-2 overlap exception:
        - slot 1 max 1 Sailing occupancy
        - slot 2 max 2 Sailing occupancies
        - slot 3 max 1 Sailing occupancy
        """
        sailing_starts = []
        for entry in self.schedule.entries:
            if entry.activity.name != "Sailing":
                continue
            prev_slot_num = entry.time_slot.slot_number - 1
            has_prev = any(
                e.activity.name == "Sailing"
                and e.troop == entry.troop
                and e.time_slot.day == entry.time_slot.day
                and e.time_slot.slot_number == prev_slot_num
                for e in self.schedule.entries
            )
            if not has_prev:
                sailing_starts.append(entry)

        overlap_by_slot = {}
        for start in sailing_starts:
            occupied = [start.time_slot.slot_number]
            if start.time_slot.slot_number < 3:
                occupied.append(start.time_slot.slot_number + 1)
            for slot_num in occupied:
                key = (start.time_slot.day, slot_num)
                overlap_by_slot.setdefault(key, []).append(start)

        for (day, slot_num), starts in overlap_by_slot.items():
            if len(starts) <= 1:
                continue

            allowed = 2 if day != Day.THURSDAY and slot_num == 2 else 1
            if len(starts) <= allowed:
                continue

            ranked = sorted(
                starts,
                key=lambda e: e.troop.get_priority(e.activity.name),
            )
            keep = ranked[:allowed]
            for conflict_start in ranked[allowed:]:
                if conflict_start not in self.schedule.entries:
                    continue
                moved = False
                candidates = self._find_valid_slots_for_activity(conflict_start.activity, conflict_start.troop)
                for candidate in candidates:
                    if candidate == conflict_start.time_slot:
                        continue
                    if self._remove_from_schedule(conflict_start):
                        if self._add_to_schedule(candidate, conflict_start.activity, conflict_start.troop):
                            moved = True
                            break
                        # rollback to original placement when candidate fails
                        self._add_to_schedule(conflict_start.time_slot, conflict_start.activity, conflict_start.troop)
                if not moved:
                    # Keep the best allowed Sailing placements if no legal move exists.
                    if keep:
                        self._remove_from_schedule(conflict_start)

    def _immediate_gap_fix_if_needed(self, phase_name: str) -> None:
        """Immediately fix gaps if any troop-level empty slots are detected after a phase."""
        troop_gaps = self._count_troop_empty_slots()
        if troop_gaps > 0:
            print(f"  [IMMEDIATE FIX] Running emergency gap fill after {phase_name} ({troop_gaps} empty slots)")
            self._guarantee_no_gaps()

    def schedule_all(self) -> Schedule:
        """Run the constrained scheduling algorithm - TOP 5 FIRST approach.

        Aligned with SCHEDULING_PROCESS.md Phase Groups A-D.
        """
        self.current_pipeline_phase = "foundation"
        self.logger.section("CONSTRAINED SCHEDULER - PHASE A: FOUNDATION")

        # =================================================================
        # PHASE A: FOUNDATION & CLUSTERING
        # =================================================================

        # Phase A.0: Friday Reflection (FIRST - Mandatory, Reserve slots early!)
        # This prevents gap-fills from consuming Friday slots before Reflection runs
        self.logger.subsection("A.0 Friday Reflection (reserve Friday slots)")
        self._schedule_friday_reflection()

        # Phase A.0b: Super Troop (Mandatory for all troops)
        # Reserve slots early to ensure every troop gets Super Troop before preferences fill slots
        self.logger.subsection("A.0b Super Troop (mandatory)")
        self._schedule_super_troop()

        # Phase A.3: HC/DG Tuesday ONLY - Must run BEFORE 3hr/clustering (Spine order)
        # Tuesday is their only allowed day - reserve before other phases consume it
        self.logger.subsection("A.3 HC/DG Tuesday scheduling (Spine: early)")
        self._schedule_hc_dg_tuesday()

        # Phase A.5: Sailing Optimization (9-Slot Capacity, Priority)
        # Optimized logic based on user feedback (Sailing is High Priority)
        self.logger.subsection("A.5 Sailing Optimization (9-Slot)")
        self._schedule_sailing_optimize_all()
        # self._schedule_thursday_sailing_largest_troop() # REPLACED

        # Phase A.5b: Early Aqua Trampoline for Top 5 (Pattern: 67% of Top 5 misses are AT)
        # Reserve beach slots (1 or 3) before preferences consume them. Large troops first.
        self.logger.subsection("A.5b Early Aqua Trampoline for Top 5")
        self._schedule_early_aqua_trampoline_top5()

        # Phase A.5c: Guarantee Top 1 Beach (prevent missed top-1 beach)
        # Ensures top-1 beach activities are placed before other phases consume beach slots.
        self.logger.subsection("A.5c Guarantee Top 1 Beach (AT/WP/GM/etc.)")
        self._guarantee_top1_beach()

        # Phase A.1: 3-Hour Activities (Rocks - full day blocks)
        self.logger.subsection("A.1 Scheduling 3-Hour Activities")
        self._schedule_three_hour_activities()

        # Phase A.7: Delta + Sailing Pairing (reserve full day slots early)
        self.logger.subsection("A.7 Delta + Sailing pairing (reserve day)")
        self._schedule_delta_sailing_pairs()

        # Phase A.2: Top 10 2-Hour Activities (need consecutive slots)
        self.logger.subsection("A.2 Top 10 2-Hour Activities (Priority)")
        self._schedule_two_hour_activities_priority()

        # Phase A.4: Early Staff Area Clustering (Pre-schedule Tower, ODS, Rifle)
        self.logger.subsection("A.4 Early staff area clustering")
        self._early_staff_area_clustering()

        # Phase A.6: Priority Scheduling for Limited Activities
        self.logger.subsection("A.6 Priority scheduling for limited activities (Global Rank 0-4)")
        self._schedule_limited_activities_by_priority(max_rank=4)

        # Phase A.8: Sailing Pairs for Same-Day Bonus (Spine: AT sharing integration)
        # Runs after Delta+Sailing pairing - pairs troops for overlapping Sailing sessions
        self.logger.subsection("A.8 Sailing pairs for Same-Day bonus")
        self._schedule_sailing_pairs()

        # GAP CHECK: After Phase A - Foundation & Clustering
        self._immediate_gap_fix_if_needed("Phase A (Foundation & Clustering)")

        # =================================================================
        # PHASE B: CORE REQUESTS
        # =================================================================
        self.current_pipeline_phase = "core"
        self.logger.section("PHASE B: CORE REQUESTS")

        # Phase B.1: Preference Rank 1-5 (Top 5 Guarantee)
        # Force Top 1 first before ranks 2-5
        self.logger.subsection("B.1 Scheduling Top 1 (FIRST PRIORITY)")
        self._schedule_preferences_range(0, 1)
        self.logger.subsection("B.1b Forcing Top 1 (make space before Top 2-5)")
        self._force_top1_preferences()
        self.logger.subsection("B.1c Scheduling Top 2-5")
        self._schedule_preferences_range(1, 5)

        # Phase B.2: Guarantee 100% Top 5
        self.logger.subsection("B.2 Guaranteeing 100% Top 5 satisfaction")
        self._guarantee_all_top5()

        # Phase B.3: Mandatory Enforcement
        self.logger.subsection("B.3 Mandatory Top 5 enforcement")
        self._enforce_mandatory_top5()

        # Phase B.4: Friday Reflection (MOVED to A.0 - runs first to reserve slots)
        # self._schedule_friday_reflection()  # Now in Phase A.0

        # Phase B.6: Delta (Requested only, NO commissioner forcing)
        self._schedule_delta_early()

        # Phase B.6: Super Troop (MOVED to A.0b - runs first to reserve slots)
        # self._schedule_super_troop()  # Now in Phase A.0b

        # Phase B.7: Build commissioner busy map (informational)
        self._build_commissioner_busy_map()

        # Phase B.8: Early Sailing for Top 10 troops (pair with Delta if possible)
        self.logger.subsection("B.8 Early Sailing for Top 10 troops")
        self._schedule_early_sailing_top10()

        # Phase B.9: Enforce Delta + Sailing same-day pairing
        self.logger.subsection("B.9 Enforce Delta + Sailing same-day pairing")
        self._enforce_delta_sailing_pairing()

        # Phase B.10: Consolidate Sailing to cluster 2 per day (AGGRESSIVE)
        self.logger.subsection("B.10 Consolidate Sailing same-day clustering")
        self._consolidate_sailing_same_day()

        # GAP CHECK: After Phase B - Core Requests
        self._immediate_gap_fix_if_needed("Phase B (Core Requests)")

        # Phase B.11: Early Aqua Trampoline sharing (pair Top 5 AT wants before slots fill)
        self.logger.subsection("B.11 Early Aqua Trampoline sharing (Top 5)")
        self._aggressive_aqua_trampoline_sharing()

        # =================================================================
        # PHASE C: REMAINING & OPTIMIZATION
        # =================================================================
        self.current_pipeline_phase = "remaining"
        self.logger.section("PHASE C: REMAINING & OPTIMIZATION")

        # Phase C.1: Day Specific requests
        self._schedule_day_requests()
        # Limited activities moved to A.6

        # Phase C.2: Staff Optimization (Consecutive)
        self.logger.subsection("C.2 Staff Optimization (consecutive activities)")
        self._schedule_staff_optimized_areas()

        # Phase C.3: Balance Staff Loads
        self.logger.subsection("C.3 Balancing staff workload")
        # Skip - this is now handled in the enhanced staff variance optimization

        # Phase C.4: Remaining Preferences (Top 6-20)
        self.logger.subsection("C.4 Scheduling Remaining Preferences (Top 6-20)")
        self._schedule_preferences_range(5, 20)

        # Phase C.4.5: Guarantee Minimum Top 10 (2-3 per troop)
        self.logger.subsection("C.4.5 Guaranteeing Minimum Top 10 (2-3 per troop)")
        self._guarantee_minimum_top10()

        # Phase C.5: Guarantee Top 10
        self.logger.subsection("C.5 Guaranteeing Top 10 with exceptions")
        self._guarantee_top10_with_exceptions()

        # Phase C.6: Fill Slot Logic
        self.logger.subsection("C.6 Filling remaining slots")
        self._fill_all_remaining()
        self.logger.subsection("Scheduling balls activities during sailing")
        self._schedule_sailing_balls_fills()

        # GAP CHECK: After Phase C.6 - Fill Slot Logic
        self._immediate_gap_fix_if_needed("Phase C.6 (Fill Slot Logic)")

        # Phase C.7: Aggressive Aqua Trampoline Sharing
        self.logger.subsection("C.7 Aggressively pairing Aqua Trampoline sharing")
        self._aggressive_aqua_trampoline_sharing()

        # GAP CHECK: After Phase C.7 - Aqua Trampoline Sharing
        self._immediate_gap_fix_if_needed("Phase C.7 (Aqua Trampoline Sharing)")

        # Phase C.8: Removed - Early clustering was causing constraint violations
        # The existing D.3 clustering pass is sufficient

        # =================================================================
        # PHASE D: FINAL POLISH
        # =================================================================
        self.current_pipeline_phase = "polish"
        self.logger.section("PHASE D: FINAL POLISH & VERIFICATION")

        # Phase D.1: Optimizations (Consolidated)
        self.logger.subsection("D.1 Optimizing Friday Reflection slots")
        self._optimize_friday_reflections()

        self.logger.subsection("D.2 Comprehensive clustering & smart swaps")
        self._comprehensive_clustering_optimization()

        # GAP CHECK: After D.2 - Comprehensive Clustering
        self._immediate_gap_fix_if_needed("Phase D.2 (Comprehensive Clustering)")

        self.logger.subsection("D.3 Early forced clustering consolidation")
        self._force_clustering_consolidation()

        # GAP CHECK: After D.3 - Forced Clustering
        self._immediate_gap_fix_if_needed("Phase D.3 (Forced Clustering)")

        self.logger.subsection("D.3b Ultra-aggressive excess day reduction")
        self._ultra_aggressive_clustering()

        # GAP CHECK: After D.3b - Ultra Clustering
        self._immediate_gap_fix_if_needed("Phase D.3b (Ultra Clustering)")

        self.logger.subsection("D.4 Friday Super Troop optimization")
        self._optimize_friday_super_troop()

        self.logger.subsection("D.5 Flexible Reflection slot optimization")
        self._optimize_flexible_reflections()

        self.logger.subsection("D.6 Commissioner load balancing")
        self._optimize_commissioner_balance()

        self.logger.subsection("D.7 Setup Efficiency & Activity Clustering")
        self._optimize_setup_efficiency()
        self._optimize_activity_clustering()

        # GAP CHECK: After D.7 - Activity Clustering
        self._immediate_gap_fix_if_needed("Phase D.7 (Activity Clustering)")

        self.logger.subsection("D.8 Outlier Activity Optimization")
        self._optimize_outlier_activities()
        self._optimize_commissioner_day_ownership()

        self.logger.subsection("D.9 Post-Fill Cluster Gap Optimization")
        self._optimize_cluster_gaps_post_fill()

        # Phase D.8: Recovery & Gap Filling
        self.logger.subsection("D.8 Top 10 Recovery & Gap Filling")
        self._recover_top10_from_fills()
        # self._fill_gaps_with_valuable_moves() # DISABLED: Causes multi-slot corruption (found 1 slot expected N)

        # Phase D.9: Comprehensive Cleanup
        self.logger.subsection("D.9 Comprehensive final cleanup")
        self._comprehensive_final_cleanup()

        # GAP CHECK: After D.9 - Final Cleanup
        self._immediate_gap_fix_if_needed("Phase D.9 (Final Cleanup)")

        # =================================================================
        # FINAL VERIFICATION
        # =================================================================
        self.current_pipeline_phase = "final"
        self.logger.section("FINAL VERIFICATION")

        # Multi-slot Integrity Fix - Ensure all multi-slot activities have correct slots
        self.logger.subsection("Multi-Slot Integrity Check")
        self._fix_multislot_integrity()

        # Final comprehensive validation is the last mutating step.
        # Do not mutate the schedule after this call, or we can invalidate a "validated" output.
        self._final_comprehensive_validation()

        return self.schedule
