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

    def _count_top10_in_schedule(self) -> int:
        """Count how many Top-10 preferences are currently placed in the schedule."""
        count = 0
        for troop in self.troops:
            if not troop.preferences:
                continue
            for i in range(min(10, len(troop.preferences))):
                activity_name = troop.preferences[i]
                if any(e.activity.name == activity_name and e.troop == troop
                       for e in self.schedule.entries):
                    count += 1
        return count

    def _safe_phase_d_step(self, step_name: str, step_fn) -> None:
        """Run a Phase D optimization step with Top-5/Top-10 rollback protection.

        The step runs, then any resulting gaps are filled within the same
        transactional boundary.  If the combined result increases non-exempt
        Top-5 misses or loses more than 2 Top-10 placements globally, the
        entire operation (including gap fills) is rolled back.
        """
        snapshot = self._snapshot_scheduler_state()
        before_top5, _ = self._count_non_exempt_top5_misses()
        before_top10 = self._count_top10_in_schedule()

        step_fn()

        # Fill any gaps the step created — inside the safety boundary so
        # destructive fills are rolled back together with the step.
        self._immediate_gap_fix_if_needed(f"{step_name} (post-step)")

        after_top5, _ = self._count_non_exempt_top5_misses()
        after_top10 = self._count_top10_in_schedule()
        top10_lost = before_top10 - after_top10

        if after_top5 > before_top5:
            print(f"  [{step_name}] ROLLED BACK — Top-5 misses increased ({before_top5} -> {after_top5})")
            self._restore_scheduler_state(snapshot)
        elif top10_lost > 2:
            print(f"  [{step_name}] ROLLED BACK — lost {top10_lost} Top-10 placements ({before_top10} -> {after_top10})")
            self._restore_scheduler_state(snapshot)
        else:
            delta_label = f"Top10: {before_top10}->{after_top10}" if top10_lost != 0 else "Top10: stable"
            print(f"  [{step_name}] OK ({delta_label})")

    def schedule_all(self) -> Schedule:
        """Run the constrained scheduling algorithm - TOP 5 FIRST approach.

        Aligned with SCHEDULING_PROCESS.md Phase Groups A-D.
        """
        self.current_pipeline_phase = "foundation"
        self.logger.section("CONSTRAINED SCHEDULER - PHASE A: FOUNDATION")

        # =================================================================
        # PHASE A: FOUNDATION (Rocks, Pebbles, Sand)
        # Order: Mandatory anchors -> Multi-slot rocks -> Sailing/Delta
        #        -> Beach protection -> Staff clustering -> Limited activities
        # =================================================================

        # A.1: Friday Reflection — mandatory anchor, reserve Friday slots first
        self.logger.subsection("A.1 Friday Reflection (reserve Friday slots)")
        self._schedule_friday_reflection()

        # A.2: Super Troop — mandatory anchor for all troops
        self.logger.subsection("A.2 Super Troop (mandatory)")
        self._schedule_super_troop()

        # A.3: HC/DG Tuesday — mandatory anchor, Tuesday is the only allowed day
        self.logger.subsection("A.3 HC/DG Tuesday scheduling")
        self._schedule_hc_dg_tuesday()

        # A.4: 3-Hour Activities — ROCKS: full-day blocks, biggest contiguous constraint
        self.logger.subsection("A.4 3-Hour Activities (Rocks)")
        self._schedule_three_hour_activities()

        # A.5: 2-Hour Activities — ROCKS: consecutive multi-slot requirements
        self.logger.subsection("A.5 Top-10 2-Hour Activities (Rocks)")
        self._schedule_two_hour_activities_priority()

        # A.6: Sailing Optimization — 2-slot capacity, high priority
        self.logger.subsection("A.6 Sailing Optimization (9-Slot)")
        self._schedule_sailing_optimize_all()

        # A.7: Delta + Sailing Pairing — full-day synchronization
        self.logger.subsection("A.7 Delta + Sailing pairing (reserve day)")
        self._schedule_delta_sailing_pairs()

        # A.8: Early Sailing Top 10 — multi-slot structural placement (from Phase B)
        self.logger.subsection("A.8 Early Sailing for Top 10 troops")
        self._schedule_early_sailing_top10()

        # A.9: Consolidate Sailing — cluster sailing groups to 2 per day (from Phase B)
        self.logger.subsection("A.9 Consolidate Sailing same-day clustering")
        self._consolidate_sailing_same_day()

        # A.10: Early Aqua Trampoline for Top 5 — beach slot protection
        self.logger.subsection("A.10 Early Aqua Trampoline for Top 5")
        self._schedule_early_aqua_trampoline_top5()

        # A.11: Guarantee Top 1 Beach — prevent missed top-1 beach preferences
        self.logger.subsection("A.11 Guarantee Top 1 Beach (AT/WP/GM/etc.)")
        self._guarantee_top1_beach()

        # A.12: Early Staff Area Clustering — pre-schedule Tower, ODS, Rifle
        self.logger.subsection("A.12 Early staff area clustering")
        self._early_staff_area_clustering()

        # A.13: Priority Limited Activities — Global Rank 0-4 constrained activities
        self.logger.subsection("A.13 Priority limited activities (Global Rank 0-4)")
        self._schedule_limited_activities_by_priority(max_rank=4)

        # A.14: Sailing Pairs Same-Day Bonus — sync overlapping sessions
        self.logger.subsection("A.14 Sailing pairs for Same-Day bonus")
        self._schedule_sailing_pairs()

        # Exit Gate A: Immediate gap repair
        self._immediate_gap_fix_if_needed("Phase A (Foundation)")

        # =================================================================
        # PHASE B: CORE REQUESTS
        # =================================================================
        self.current_pipeline_phase = "core"
        self.logger.section("PHASE B: CORE REQUESTS")

        # B.1: Top 1 (First Priority)
        self.logger.subsection("B.1 Scheduling Top 1 (FIRST PRIORITY)")
        self._schedule_preferences_range(0, 1)

        # B.1b: Force Top 1 — make space before Top 2-5
        self.logger.subsection("B.1b Forcing Top 1 (make space before Top 2-5)")
        self._force_top1_preferences()

        # B.1c: Top 2-5
        self.logger.subsection("B.1c Scheduling Top 2-5")
        self._schedule_preferences_range(1, 5)

        # B.2: Guarantee 100% Top 5
        self.logger.subsection("B.2 Guaranteeing 100% Top 5 satisfaction")
        self._guarantee_all_top5()

        # B.3: Mandatory Top 5 Enforcement
        self.logger.subsection("B.3 Mandatory Top 5 enforcement")
        self._enforce_mandatory_top5()

        # B.4: Delta Scheduling (requested only, no commissioner forcing)
        self._schedule_delta_early()

        # B.5: Commissioner Busy Map (diagnostic/tracking)
        self._build_commissioner_busy_map()

        # B.6: Enforce Delta + Sailing Same-Day Pairing
        self.logger.subsection("B.6 Enforce Delta + Sailing same-day pairing")
        self._enforce_delta_sailing_pairing()

        # Exit Gate B: Immediate gap check and repair
        self._immediate_gap_fix_if_needed("Phase B (Core Requests)")

        # B.7: Aqua Trampoline Sharing (consolidated single pass)
        self.logger.subsection("B.7 Aqua Trampoline sharing (Top 5)")
        self._aggressive_aqua_trampoline_sharing()

        # =================================================================
        # PHASE C: REMAINING & OPTIMIZATION
        # =================================================================
        self.current_pipeline_phase = "remaining"
        self.logger.section("PHASE C: REMAINING & OPTIMIZATION")

        # C.1: Day Specific Requests
        self._schedule_day_requests()

        # C.2: Staff Optimization (consecutive activities)
        self.logger.subsection("C.2 Staff Optimization (consecutive activities)")
        self._schedule_staff_optimized_areas()

        # C.3: Remaining Preferences (Top 6-20)
        self.logger.subsection("C.3 Scheduling Remaining Preferences (Top 6-20)")
        self._schedule_preferences_range(5, 20)

        # C.4: Guarantee Minimum Top 10 (2-3 per troop)
        self.logger.subsection("C.4 Guaranteeing Minimum Top 10 (2-3 per troop)")
        self._guarantee_minimum_top10()

        # C.5: Guarantee Top 10 with Exceptions
        self.logger.subsection("C.5 Guaranteeing Top 10 with exceptions")
        self._guarantee_top10_with_exceptions()

        # C.6: Fill All Remaining Slots
        self.logger.subsection("C.6 Filling remaining slots")
        self._fill_all_remaining()
        self.logger.subsection("C.6b Scheduling balls activities during sailing")
        self._schedule_sailing_balls_fills()

        # Exit Gate C: Safety checks, ensure schedule is 100% populated
        self._immediate_gap_fix_if_needed("Phase C (Remaining & Optimization)")

        # =================================================================
        # PHASE D: FINAL POLISH (Guarded Swap Phase)
        # The schedule is 100% full entering Phase D. Destructive
        # clustering steps (D.2-D.4, D.8-D.9) are wrapped in Top-5/
        # Top-10 safety harnesses that roll back the step AND its
        # gap fill together if preferences are degraded.
        # =================================================================
        self.current_pipeline_phase = "polish"
        self.logger.section("PHASE D: FINAL POLISH & VERIFICATION")

        # D.1: Friday Reflection Optimization
        self.logger.subsection("D.1 Friday Reflection optimization")
        self._optimize_friday_reflections()

        # D.2: Comprehensive Clustering & Smart Swaps (guarded with gap fill)
        self.logger.subsection("D.2 Comprehensive clustering & smart swaps")
        self._safe_phase_d_step("D.2 Clustering", self._comprehensive_clustering_optimization)

        # D.3: Forced Clustering Consolidation (guarded with gap fill)
        self.logger.subsection("D.3 Forced clustering consolidation")
        self._safe_phase_d_step("D.3 Forced Clustering", self._force_clustering_consolidation)

        # D.4: Ultra-Aggressive Excess Day Reduction (guarded with gap fill)
        self.logger.subsection("D.4 Ultra-aggressive excess day reduction")
        self._safe_phase_d_step("D.4 Ultra Clustering", self._ultra_aggressive_clustering)

        # D.5: Friday Super Troop Optimization
        self.logger.subsection("D.5 Friday Super Troop optimization")
        self._optimize_friday_super_troop()

        # D.6: Flexible Reflection Slot Optimization
        self.logger.subsection("D.6 Flexible Reflection slot optimization")
        self._optimize_flexible_reflections()

        # D.7: Commissioner Load Balancing
        self.logger.subsection("D.7 Commissioner load balancing")
        self._optimize_commissioner_balance()

        # D.8: Setup Efficiency & Activity Clustering (guarded with gap fill)
        self.logger.subsection("D.8 Setup Efficiency & Activity Clustering")
        self._safe_phase_d_step("D.8 Setup/Activity Clustering", lambda: (
            self._optimize_setup_efficiency(),
            self._optimize_activity_clustering(),
        ))

        # D.9: Outlier Activity Optimization + Commissioner Day Ownership (guarded with gap fill)
        self.logger.subsection("D.9 Outlier Activity & Commissioner Day Ownership")
        self._safe_phase_d_step("D.9 Outlier/Commissioner", lambda: (
            self._optimize_outlier_activities(),
            self._optimize_commissioner_day_ownership(),
        ))

        # D.10: Post-Fill Cluster Gap Optimization
        self.logger.subsection("D.10 Post-Fill Cluster Gap Optimization")
        self._optimize_cluster_gaps_post_fill()

        # D.11: Comprehensive Final Cleanup
        self.logger.subsection("D.11 Comprehensive final cleanup")
        self._comprehensive_final_cleanup()

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
