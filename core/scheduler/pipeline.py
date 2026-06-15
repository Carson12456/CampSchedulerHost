"""
Scheduling phase pipeline orchestration mixin.

This module contains the high-level A->D phase flow used by the scheduler.
"""

from ..models import Day, Schedule


class SchedulingPipelineMixin:
    """Coordinates the full scheduling lifecycle across all phases."""

    # F-17: run-wide Top-10 budget. Each guarded Phase-D step may lose at most
    # ``top10_lost > 2`` on its own, but without a run-level cap the per-step
    # tolerance compounds across D.2/D.3/D.4/D.8/D.9 (up to ~10 Top-10
    # placements can erode the 450 bucket with no rollback). This budget bounds
    # the *cumulative* Top-10 loss attributable to guarded steps over the whole
    # run; once exhausted, any further guarded step that loses Top-10 is rolled
    # back.
    PHASE_D_TOP10_RUN_BUDGET = 2

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
        # #region agent log
        if hasattr(self, "_debug_log"):
            self._debug_log(
                "H3",
                "pipeline.py:_immediate_gap_fix_if_needed:81",
                "Immediate gap check",
                {
                    "phaseName": phase_name,
                    "pipelinePhase": getattr(self, "current_pipeline_phase", "unknown"),
                    "troopGaps": troop_gaps,
                },
            )
        # #endregion
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

    def _count_sailing_same_day_misses(self) -> int:
        """Count Sailing days that hold only one troop (judge §cluster metric).

        Mirrors ``regression_checker`` ``sailing_same_day_misses``: every day
        that has at least one Sailing start but fewer than two troops sailing is
        a missed "2 sails per day" consolidation opportunity. Used to guard the
        F-18 consolidation pass so it only commits when it strictly reduces the
        penalty.
        """
        sailing_day_troops = {}
        for entry in self.schedule.entries:
            if entry.activity.name != "Sailing":
                continue
            sailing_day_troops.setdefault(entry.time_slot.day, set()).add(entry.troop.name)
        total = len(sailing_day_troops)
        paired = sum(1 for troops in sailing_day_troops.values() if len(troops) >= 2)
        return max(0, total - paired)

    def _safe_phase_d_step(
        self,
        step_name: str,
        step_fn,
        *,
        guard_top10: bool = True,
        guard_soft_metrics: bool = True,
        guard_staff_variance: bool = False,
        guard_sailing_same_day: bool = False,
    ) -> None:
        """Run a Phase D optimization step with Top-5/Top-10 rollback protection.

        The step runs, then any resulting gaps are filled within the same
        transactional boundary.  If the combined result increases non-exempt
        Top-5 misses or loses more than 2 Top-10 placements globally, the
        entire operation (including gap fills) is rolled back.

        ``guard_staff_variance`` (F-16): additionally roll back unless the step
        strictly *reduces* staffed-slot load variance — used for the staff
        balancing pass, whose moves are otherwise invisible to the guard.

        ``guard_sailing_same_day`` (F-18): additionally roll back unless the
        step strictly *reduces* the Sailing same-day miss count, and never let
        it drift a Delta/Sailing pair apart (BRAIN §11) — used for the Sailing
        consolidation pass, whose benefit is otherwise invisible to the guard.

        F-17: Top-10 loss is bounded both per-step (``top10_lost > 2``) and
        run-wide via ``self._phase_d_top10_budget_remaining``; once the run
        budget is exhausted, any guarded step that loses Top-10 is rolled back.
        """
        self._rebuild_staff_tracking()
        snapshot = self._snapshot_scheduler_state()
        before_top5, _ = self._count_non_exempt_top5_misses()
        before_top10 = self._count_top10_in_schedule()
        before_excess = self._count_excess_cluster_days()
        before_gaps = self._count_area_cluster_gaps()
        before_variance = self._compute_staff_load_variance() if guard_staff_variance else 0.0
        before_sailing = self._count_sailing_same_day_misses() if guard_sailing_same_day else 0
        before_delta_pair = self._count_delta_sailing_pairing_misses() if guard_sailing_same_day else 0

        step_fn()
        self._rebuild_staff_tracking()

        # Fill any gaps the step created — inside the safety boundary so
        # destructive fills are rolled back together with the step.
        self._immediate_gap_fix_if_needed(f"{step_name} (post-step)")
        self._rebuild_staff_tracking()

        after_top5, _ = self._count_non_exempt_top5_misses()
        after_top10 = self._count_top10_in_schedule()
        after_excess = self._count_excess_cluster_days()
        after_gaps = self._count_area_cluster_gaps()
        after_variance = self._compute_staff_load_variance() if guard_staff_variance else 0.0
        after_sailing = self._count_sailing_same_day_misses() if guard_sailing_same_day else 0
        after_delta_pair = self._count_delta_sailing_pairing_misses() if guard_sailing_same_day else 0
        top10_lost = before_top10 - after_top10

        # F-17: run-wide Top-10 budget (cumulative loss attributable to guarded
        # steps). Defensive getattr keeps the method usable outside schedule_all.
        budget_remaining = getattr(self, "_phase_d_top10_budget_remaining", self.PHASE_D_TOP10_RUN_BUDGET)

        if after_top5 > before_top5:
            print(f"  [{step_name}] ROLLED BACK — Top-5 misses increased ({before_top5} -> {after_top5})")
            self._restore_scheduler_state(snapshot)
            status = "rolled-back-top5"
        elif guard_top10 and top10_lost > 2:
            print(f"  [{step_name}] ROLLED BACK — lost {top10_lost} Top-10 placements ({before_top10} -> {after_top10})")
            self._restore_scheduler_state(snapshot)
            status = "rolled-back-top10"
        elif guard_top10 and top10_lost > budget_remaining:
            print(f"  [{step_name}] ROLLED BACK — run-wide Top-10 budget exhausted "
                  f"(step lost {top10_lost}, budget {budget_remaining} remaining)")
            self._restore_scheduler_state(snapshot)
            status = "rolled-back-top10-budget"
        elif guard_soft_metrics and after_excess > before_excess:
            print(f"  [{step_name}] ROLLED BACK — excess cluster days increased ({before_excess} -> {after_excess})")
            self._restore_scheduler_state(snapshot)
            status = "rolled-back-excess"
        elif guard_soft_metrics and after_gaps > before_gaps:
            print(f"  [{step_name}] ROLLED BACK — cluster gaps increased ({before_gaps} -> {after_gaps})")
            self._restore_scheduler_state(snapshot)
            status = "rolled-back-gaps"
        elif guard_staff_variance and after_variance > before_variance + 1e-9:
            print(f"  [{step_name}] ROLLED BACK — staff variance increased ({before_variance:.2f} -> {after_variance:.2f})")
            self._restore_scheduler_state(snapshot)
            status = "rolled-back-staff-variance"
        elif guard_sailing_same_day and after_delta_pair > before_delta_pair:
            print(f"  [{step_name}] ROLLED BACK — Delta/Sailing pairing worsened ({before_delta_pair} -> {after_delta_pair})")
            self._restore_scheduler_state(snapshot)
            status = "rolled-back-delta-pair"
        elif guard_sailing_same_day and after_sailing >= before_sailing:
            print(f"  [{step_name}] ROLLED BACK — Sailing same-day misses not improved ({before_sailing} -> {after_sailing})")
            self._restore_scheduler_state(snapshot)
            status = "rolled-back-sailing-same-day"
        else:
            # Step committed: charge the run-wide Top-10 budget (gains refund it,
            # capped at the initial budget so they can't bank extra headroom).
            if guard_top10 and hasattr(self, "_phase_d_top10_budget_remaining"):
                self._phase_d_top10_budget_remaining = min(
                    self.PHASE_D_TOP10_RUN_BUDGET,
                    self._phase_d_top10_budget_remaining - top10_lost,
                )
            delta_label = f"Top10: {before_top10}->{after_top10}" if top10_lost != 0 else "Top10: stable"
            cluster_label = f"Excess: {before_excess}->{after_excess}, Gaps: {before_gaps}->{after_gaps}"
            print(f"  [{step_name}] OK ({delta_label}; {cluster_label})")
            status = "ok"
        self._record_schedule_snapshot(
            f"{step_name} complete",
            reason="phase-step",
            metadata={
                "status": status,
                "before_top5": before_top5,
                "after_top5": after_top5,
                "before_top10": before_top10,
                "after_top10": after_top10,
                "before_excess": before_excess,
                "after_excess": after_excess,
                "before_gaps": before_gaps,
                "after_gaps": after_gaps,
            },
            force=True,
        )

    def schedule_all(self) -> Schedule:
        """Run the constrained scheduling algorithm - TOP 5 FIRST approach.

        Aligned with SCHEDULING_PROCESS.md Phase Groups A-D.
        """
        self.current_pipeline_phase = "foundation"
        self._record_schedule_snapshot("run start", reason="run-start", force=True)
        self.logger.section("CONSTRAINED SCHEDULER - PHASE A: FOUNDATION")

        # Phase A structure notes:
        #   * A.2 (Super Troop) relocated post-A.7 so it doesn't fragment multi-slot rocks.
        #   * A.6/A.7 (Sailing + Delta/Sailing) relocated above A.5 — A.5 was otherwise
        #     grabbing Sailing (slots>=1.5) with generic first-fit, defeating A.6's
        #     9-slot capacity matrix and A.7's same-day pairing.
        # Cut/not invoked: A.8–A.11, A.14, B.4 (bodies remain in legacy_parts).
        # Empirical reverts: C.1 must not run at A.0; B.7 stays in Phase B.

        # A.1: Friday Reflection — mandatory anchor, reserve Friday slots first
        self.logger.subsection("A.1 Friday Reflection (reserve Friday slots)")
        self._schedule_friday_reflection()
        self._record_schedule_snapshot("A.1 Friday Reflection complete", reason="phase-step")

        # A.3: HC/DG Tuesday — mandatory anchor, Tuesday is the only allowed day
        self.logger.subsection("A.3 HC/DG Tuesday scheduling")
        self._schedule_hc_dg_tuesday()
        self._record_schedule_snapshot("A.3 HC/DG Tuesday complete", reason="phase-step")

        # A.4: 3-Hour Activities — ROCKS: full-day blocks, biggest contiguous constraint
        self.logger.subsection("A.4 3-Hour Activities (Rocks)")
        self._schedule_three_hour_activities()
        self._record_schedule_snapshot("A.4 3-Hour Activities complete", reason="phase-step")

        # A.6 (relocated pre-A.5): Sailing Optimization — 2-slot (90-min) capacity.
        # Must run BEFORE A.5 so the specialized 9-slot Sailing matrix owns its
        # placements; otherwise A.5's generic first-fit pass grabs Sailing
        # (slots>=1.5) and A.6 skips those troops entirely.
        self.logger.subsection("A.6 Sailing Optimization (9-Slot) [relocated pre-A.5]")
        self._schedule_sailing_optimize_all()
        self._record_schedule_snapshot("A.6 Sailing Optimization complete", reason="phase-step")

        # A.7 (relocated pre-A.5): Delta + Sailing Pairing — pair Delta with Sailing
        # immediately after Sailing is placed so Delta seeks the same commissioner
        # day as Sailing, building a full-day block before 2-hour rocks land.
        self.logger.subsection("A.7 Delta + Sailing pairing (reserve day) [relocated pre-A.5]")
        self._schedule_delta_sailing_pairs()
        self._record_schedule_snapshot("A.7 Delta + Sailing pairing complete", reason="phase-step")

        # A.5: 2-Hour Activities — ROCKS: consecutive multi-slot requirements.
        # Runs after Sailing (A.6) and Delta-Sailing pairing (A.7) so those
        # structural blocks are locked in first.
        self.logger.subsection("A.5 Top-10 2-Hour Activities (Rocks)")
        self._schedule_two_hour_activities_priority()
        self._record_schedule_snapshot("A.5 2-Hour Activities complete", reason="phase-step")

        # A.2 (relocated): Super Troop — mandatory anchor for all troops.
        # Moved below multi-slot rocks so Super Troop no longer fragments 3hr/2hr/Sailing blocks.
        self.logger.subsection("A.2 Super Troop (mandatory) [relocated post-A.7]")
        self._schedule_super_troop()
        self._record_schedule_snapshot("A.2 Super Troop complete", reason="phase-step")

        # A.12: Early Staff Area Clustering — pre-schedule Tower, ODS, Rifle
        self.logger.subsection("A.12 Early staff area clustering")
        self._early_staff_area_clustering()
        self._record_schedule_snapshot("A.12 Early staff clustering complete", reason="phase-step")

        # Exit Gate A: Immediate gap repair
        self._immediate_gap_fix_if_needed("Phase A (Foundation)")
        self._record_schedule_snapshot("Phase A exit gate complete", reason="phase-exit")

        # =================================================================
        # PHASE B: CORE REQUESTS
        # =================================================================
        self.current_pipeline_phase = "core"
        self.logger.section("PHASE B: CORE REQUESTS")

        # B.1: Top 1 (First Priority)
        self.logger.subsection("B.1 Scheduling Top 1 (FIRST PRIORITY)")
        self._schedule_preferences_range(0, 1)
        self._record_schedule_snapshot("B.1 Top 1 complete", reason="phase-step")

        # B.1b: Force Top 1 — make space before Top 2-5
        self.logger.subsection("B.1b Forcing Top 1 (make space before Top 2-5)")
        self._force_top1_preferences()
        self._record_schedule_snapshot("B.1b Force Top 1 complete", reason="phase-step")

        # B.1c: Top 2-5
        self.logger.subsection("B.1c Scheduling Top 2-5")
        self._schedule_preferences_range(1, 5)
        self._record_schedule_snapshot("B.1c Top 2-5 complete", reason="phase-step")

        # B.2: Guarantee 100% Top 5
        self.logger.subsection("B.2 Guaranteeing 100% Top 5 satisfaction")
        self._guarantee_all_top5()
        self._record_schedule_snapshot("B.2 Top 5 guarantee complete", reason="phase-step")

        # B.3: Mandatory Top 5 Enforcement
        self.logger.subsection("B.3 Mandatory Top 5 enforcement")
        self._enforce_mandatory_top5()
        self._record_schedule_snapshot("B.3 Mandatory Top 5 complete", reason="phase-step")

        # B.5: Commissioner Busy Map (diagnostic/tracking)
        self._build_commissioner_busy_map()

        # B.6: Safety net after Top 1–5; Phase D + pair-protected Delta reduce drift.
        self.logger.subsection("B.6 Enforce Delta + Sailing same-day pairing")
        self._enforce_delta_sailing_pairing()
        self._record_schedule_snapshot("B.6 Delta + Sailing pairing complete", reason="phase-step")

        # Exit Gate B: Immediate gap check and repair
        self._immediate_gap_fix_if_needed("Phase B (Core Requests)")
        self._record_schedule_snapshot("Phase B exit gate complete", reason="phase-exit")

        # B.7: Aqua Trampoline sharing (must run after B.1/B.1c so AT rows exist)
        self.logger.subsection("B.7 Aqua Trampoline sharing (Top 5)")
        self._aggressive_aqua_trampoline_sharing()
        self._record_schedule_snapshot("B.7 Aqua Trampoline sharing complete", reason="phase-step")

        self.current_pipeline_phase = "remaining"
        self.logger.section("PHASE C: REMAINING & OPTIMIZATION")

        # C.1: Day-requests — first pass (non-aggressive). Needs anchors/rocks first;
        # relocating to Phase A caused regressions. MUST-HONOR aggressive seal runs
        # at end of _final_comprehensive_validation.
        self._schedule_day_requests()
        self._record_schedule_snapshot("C.1 Day requests complete", reason="phase-step")

        # C.2: Staff Optimization (consecutive activities)
        self.logger.subsection("C.2 Staff Optimization (consecutive activities)")
        self._schedule_staff_optimized_areas()
        self._record_schedule_snapshot("C.2 Staff optimization complete", reason="phase-step")

        # C.3: Remaining Preferences (Top 6-20)
        self.logger.subsection("C.3 Scheduling Remaining Preferences (Top 6-20)")
        self._schedule_preferences_range(5, 20)
        self._record_schedule_snapshot("C.3 Remaining preferences complete", reason="phase-step")

        # C.4: Guarantee Minimum Top 10 — FLOOR pass.
        # Stops when a troop has >=3 Top 10. Only displaces non-Top-5 for
        # Top 6-10 recovery. Intentionally complementary to C.5.
        self.logger.subsection("C.4 Guaranteeing Minimum Top 10 (floor: 3 per troop)")
        self._guarantee_minimum_top10()
        self._record_schedule_snapshot("C.4 Minimum Top 10 complete", reason="phase-step")

        # C.5: Guarantee Top 10 with Exceptions — MAXIMIZE pass.
        # Tries to fill ALL missing Top 10 (not just 3), skipping the
        # structural exceptions (3-hour off-camp, Sailing). Runs after C.4
        # so the floor is already met and this pass only pushes higher.
        self.logger.subsection("C.5 Guaranteeing Top 10 with exceptions (maximize)")
        self._guarantee_top10_with_exceptions()
        self._record_schedule_snapshot("C.5 Top 10 maximize complete", reason="phase-step")

        # C.6: Fill All Remaining Slots.
        # Three-tier preference-first ordering is already in place:
        #   PASS 1a: Top 10 globally rank-ordered
        #   PASS 1b: Top 11+ troop-by-troop
        #   PASS 2:  remaining_prefs THEN DEFAULT_FILL_PRIORITY
        self.logger.subsection("C.6 Filling remaining slots")
        self._fill_all_remaining()
        self._record_schedule_snapshot("C.6 Fill remaining complete", reason="phase-step")
        # C.6b moved to FINAL VERIFICATION: sailing half-slot fills must be
        # computed against the *final* schedule, since Phase D re-arranges
        # activities and can change which balls activities are adjacent /
        # already scheduled. Running C.6b here captured stale decisions.

        # Exit Gate C: Safety checks, ensure schedule is 100% populated
        self._immediate_gap_fix_if_needed("Phase C (Remaining & Optimization)")
        self._record_schedule_snapshot("Phase C exit gate complete", reason="phase-exit")

        # =================================================================
        # PHASE D: FINAL POLISH (Guarded Swap Phase)
        # The schedule is 100% full entering Phase D. All mutating steps
        # are wrapped in Top-5/Top-10 safety harnesses (_safe_phase_d_step)
        # that roll back the step AND its gap fill together if preferences
        # are degraded.
        # Review notes (2026-04-20):
        #   * D.1 and D.6 have opposing goals: D.1 CLUSTERS reflections
        #     (pack commissioner's troops together when it improves Tower/
        #     ODS/Archery adjacency); D.6 SPREADS reflections (so each
        #     commissioner can visit each troop). They are intentionally
        #     adversarial — D.1 tightens on clustering axes, D.6 tightens
        #     on visitation axes. Running both lets the guards keep only
        #     swaps that don't degrade Top 5/Top 10.
        #   * D.3 (_force_clustering_consolidation) validates every move via
        #     _can_schedule(relax)+add_entry, so it does NOT create hard
        #     violations and does not depend on D.11 to "repair" anything.
        #     (The only true constraint-bypassing forced mover was D.8's
        #     _force_cluster_consolidation; F-10 now routes it through
        #     _can_schedule(relax) too.) The authoritative safety net for any
        #     residual hard issue is _final_comprehensive_validation, not D.11
        #     (which runs guard_top10=False and is itself rolled back on Top-5).
        #   * D.7 is a DIAGNOSTIC (no mutations); moved to Final Verification.
        #   * D.10 is self-guarded (internal non-exempt/gap baselines).
        # =================================================================
        self.current_pipeline_phase = "polish"
        # F-17: reset the run-wide Top-10 loss budget entering the guarded
        # Phase-D swap phase. Guarded steps draw down this budget so their
        # individually-tolerated (<=2) Top-10 losses cannot compound run-wide.
        self._phase_d_top10_budget_remaining = self.PHASE_D_TOP10_RUN_BUDGET
        self.logger.section("PHASE D: FINAL POLISH & VERIFICATION")

        # D.1: Friday Reflection Optimization (self-contained safe-swap)
        self.logger.subsection("D.1 Friday Reflection optimization")
        self._optimize_friday_reflections()
        self._record_schedule_snapshot("D.1 Friday Reflection optimization complete", reason="phase-step")

        # D.2: Comprehensive Clustering & Smart Swaps (guarded)
        self.logger.subsection("D.2 Comprehensive clustering & smart swaps")
        self._safe_phase_d_step("D.2 Clustering", self._comprehensive_clustering_optimization)

        # D.3: Forced Clustering Consolidation (guarded; validates moves via _can_schedule(relax))
        self.logger.subsection("D.3 Forced clustering consolidation")
        self._safe_phase_d_step("D.3 Forced Clustering", self._force_clustering_consolidation)

        # D.4: Ultra-Aggressive Excess Day Reduction (guarded)
        self.logger.subsection("D.4 Ultra-aggressive excess day reduction")
        self._safe_phase_d_step("D.4 Ultra Clustering", self._ultra_aggressive_clustering)

        # D.5: Friday Super Troop Optimization.
        # Despite the name, this swaps exclusive activities (Super Troop,
        # Delta, Tower, Rifle, Shotgun, Archery) with fill activities across
        # ALL days to improve clustering. Intentionally left UNGUARDED:
        # the whole purpose of this pass is clustering, and wrapping it in a
        # Top-5/Top-10 guard rolled back legitimate clustering swaps, raising
        # average excess cluster days (3.90 -> 4.20) with no observable
        # Top-5 benefit (Top-5 remains 100% in empirical testing either way).
        # Each swap inside is a same-troop slot exchange (same activities,
        # different slots) so it cannot remove a preferred activity.
        self.logger.subsection("D.5 Friday Super Troop optimization")
        self._optimize_friday_super_troop()
        self._record_schedule_snapshot("D.5 Friday Super Troop optimization complete", reason="phase-step")

        # D.6: Flexible Reflection Slot Optimization.
        # Spreads commissioner's troops across Friday slots (opposite goal
        # to D.1's clustering). Intentionally left UNGUARDED: wrapping it
        # in _safe_phase_d_step deterministically rolled back moves that
        # have an incidental positive effect on excess cluster days
        # (3.90 -> 4.20 average when guarded), with no observable Top-5
        # benefit (Top-5 remains 100% across all tested weeks either way).
        # If future weeks show Top-5 drift from D.6, re-wrap with
        # _safe_phase_d_step("D.6 Reflection Spread", ...).
        self.logger.subsection("D.6 Flexible Reflection slot optimization")
        self._optimize_flexible_reflections()
        self._record_schedule_snapshot("D.6 Flexible Reflection optimization complete", reason="phase-step")

        # --- D.7 MOVED to Final Verification section. ---
        # _optimize_commissioner_balance is a pure diagnostic print (no
        # schedule mutations). Keeping it here was misleading.

        # D.8: Setup Efficiency & Activity Clustering (guarded)
        self.logger.subsection("D.8 Setup Efficiency & Activity Clustering")
        self._safe_phase_d_step("D.8 Setup/Activity Clustering", lambda: (
            self._optimize_setup_efficiency(),
            self._optimize_activity_clustering(),
        ))

        # D.9: Outlier Activity Optimization + Commissioner Day Ownership (guarded)
        self.logger.subsection("D.9 Outlier Activity & Commissioner Day Ownership")
        self._safe_phase_d_step("D.9 Outlier/Commissioner", lambda: (
            self._optimize_outlier_activities(),
            self._optimize_commissioner_day_ownership(),
        ))

        # D.9b: Staff Variance Optimization (F-16). Previously dead code; now wired
        # as a guarded step that only commits if it strictly reduces staffed-slot
        # load variance without losing Top-5/Top-10 or worsening clustering.
        self.logger.subsection("D.9b Staff Variance Optimization")
        self._safe_phase_d_step(
            "D.9b Staff Variance",
            self._optimize_staff_variance,
            guard_staff_variance=True,
        )

        # D.9c: Sailing Same-Day Consolidation (F-18). Previously orphaned (cut
        # A.9); now wired as a guarded step that only commits if it strictly
        # reduces Sailing same-day misses (the judge's "2 sails per day"
        # cluster metric) without losing Top-5/Top-10, worsening clustering, or
        # drifting a Delta/Sailing pair apart (BRAIN §11).
        self.logger.subsection("D.9c Sailing Same-Day Consolidation")
        self._safe_phase_d_step(
            "D.9c Sailing Consolidation",
            self._consolidate_sailing_same_day,
            guard_sailing_same_day=True,
        )

        # D.10: Post-Fill Cluster Gap Optimization (self-guarded internally)
        self.logger.subsection("D.10 Post-Fill Cluster Gap Optimization")
        self._optimize_cluster_gaps_post_fill()
        self._record_schedule_snapshot("D.10 Cluster gap optimization complete", reason="phase-step")

        # D.11: Comprehensive Final Cleanup (must run last in Phase D).
        # Guard it like the other destructive Phase D steps: cleanup must not
        # hand final validation a schedule with new non-exempt Top-5 misses.
        # Soft clustering metrics must not roll back hard overlap cleanup.
        self.logger.subsection("D.11 Comprehensive final cleanup")
        self._safe_phase_d_step(
            "D.11 Final Cleanup",
            self._comprehensive_final_cleanup,
            guard_top10=False,
            guard_soft_metrics=False,
        )

        # =================================================================
        # FINAL VERIFICATION
        # =================================================================
        self.current_pipeline_phase = "final"
        self.logger.section("FINAL VERIFICATION")

        # Multi-slot Integrity Fix - Ensure all multi-slot activities have correct slots
        self.logger.subsection("Multi-Slot Integrity Check")
        self._fix_multislot_integrity()
        self._record_schedule_snapshot("Final multi-slot integrity complete", reason="final-step")

        # MUST-HONOR aggressive day-requests run inside _final_comprehensive_validation
        # after all repairs (final seal), not here — otherwise gap fill / Top-5 repair
        # undoes them.

        # D.7 (relocated): Commissioner Load Balancing — diagnostic report only.
        # Prints per-commissioner Reflection slot loads; does not mutate schedule.
        self.logger.subsection("Diagnostic: Commissioner load balancing report [was D.7]")
        self._optimize_commissioner_balance()

        # Last mutating step (includes MUST-HONOR seal, multi-slot, gap fill, Top-5 gate).
        self._final_comprehensive_validation()
        self._record_schedule_snapshot("Final comprehensive validation complete", reason="final-step")

        self.logger.subsection("Late guarded soft-constraint cleanup")
        self._final_soft_constraint_cleanup()
        self._fix_multislot_integrity()
        self._guarantee_no_gaps()
        self._record_schedule_snapshot("Late soft-constraint cleanup complete", reason="final-step")

        # Final Filler -> Preference Audit (safe-swap, post everything).
        # After every phase and final verification have run, inspect any
        # surviving generic filler activities and swap them with an
        # unscheduled preference ONLY when every guard passes:
        #   * Top-5 misses unchanged
        #   * Top-10 count not reduced
        #   * requested replacements outrank the current fill when the fill
        #     was itself requested
        # Otherwise the filler is preserved. Empirical measurement lives in
        # _finalize_filler_replacement_audit.
        self.logger.subsection("Final Filler -> Preference Audit (safe-swap)")
        self._finalize_filler_replacement_audit()
        self._rebuild_staff_tracking()
        self._fix_multislot_integrity()
        self._guarantee_no_gaps()
        self._record_schedule_snapshot("Final filler audit complete", reason="final-step")
        final_cluster_snapshot = self._snapshot_scheduler_state()
        final_cluster_top5, _ = self._count_non_exempt_top5_misses()
        final_cluster_top10 = self._count_top10_in_schedule()
        final_cluster_excess = self._count_excess_cluster_days()
        final_cluster_gaps = self._count_area_cluster_gaps()
        if final_cluster_top5 == 0 and (final_cluster_excess > 0 or final_cluster_gaps > 0):
            self.logger.subsection("Final post-fill cluster repair")
            self._aggressive_excess_day_reduction_swaps()
            self._optimize_cluster_gaps_post_fill()
            self._fix_multislot_integrity()
            self._guarantee_no_gaps()
            after_cluster_top5, _ = self._count_non_exempt_top5_misses()
            after_cluster_top10 = self._count_top10_in_schedule()
            after_cluster_excess = self._count_excess_cluster_days()
            after_cluster_gaps = self._count_area_cluster_gaps()
            # F-17: terminal cluster repair must not erode the Top-10 (450)
            # bucket — roll back if Top-10 placements drop.
            if (
                after_cluster_top5 > final_cluster_top5
                or after_cluster_top10 < final_cluster_top10
                or after_cluster_excess > final_cluster_excess
                or after_cluster_gaps > final_cluster_gaps
            ):
                self._restore_scheduler_state(final_cluster_snapshot)
        self.logger.subsection("Terminal Filler -> Preference Audit")
        self._finalize_filler_replacement_audit()
        self._fix_multislot_integrity()
        self._guarantee_no_gaps()
        self._record_schedule_snapshot("Terminal filler audit complete", reason="final-step")
        terminal_cluster_snapshot = self._snapshot_scheduler_state()
        terminal_cluster_top5, _ = self._count_non_exempt_top5_misses()
        terminal_cluster_top10 = self._count_top10_in_schedule()
        terminal_cluster_excess = self._count_excess_cluster_days()
        terminal_cluster_gaps = self._count_area_cluster_gaps()
        if terminal_cluster_top5 == 0 and (terminal_cluster_excess > 0 or terminal_cluster_gaps > 0):
            self.logger.subsection("Terminal post-audit cluster repair")
            self._aggressive_excess_day_reduction_swaps()
            self._optimize_cluster_gaps_post_fill()
            self._fix_multislot_integrity()
            self._guarantee_no_gaps()
            after_terminal_top5, _ = self._count_non_exempt_top5_misses()
            after_terminal_top10 = self._count_top10_in_schedule()
            after_terminal_excess = self._count_excess_cluster_days()
            after_terminal_gaps = self._count_area_cluster_gaps()
            # F-17: terminal cluster repair must not erode the Top-10 (450)
            # bucket — roll back if Top-10 placements drop.
            if (
                after_terminal_top5 > terminal_cluster_top5
                or after_terminal_top10 < terminal_cluster_top10
                or after_terminal_excess > terminal_cluster_excess
                or after_terminal_gaps > terminal_cluster_gaps
            ):
                self._restore_scheduler_state(terminal_cluster_snapshot)
            else:
                self.logger.subsection("Terminal post-cluster filler audit")
                self._finalize_filler_replacement_audit()
                self._fix_multislot_integrity()
                self._guarantee_no_gaps()

        # Guarded preference upgrade (Thread 1). Runs on the near-final, fully
        # populated schedule: trades a low-rank entry (genuine preference or
        # filler) for a higher-ranked unscheduled preference, with an optional
        # single same-troop cross-slot relocation. Self-guarded so it cannot
        # raise excess/gaps/soft, drop Top-10, or break Top-5; it only commits
        # when realized preference value strictly improves.
        self.logger.subsection("Terminal guarded preference upgrade")
        self._preference_upgrade_pass()
        self._fix_multislot_integrity()
        self._guarantee_no_gaps()
        self._record_schedule_snapshot("Terminal preference upgrade complete", reason="final-step")

        # Universal Campsite Free Time coverage (Thread 2 / BRAIN §1a). Gives each
        # troop without a Campsite Free Time block one by replacing its worst
        # non-anchor occupant, committing only when score-neutral-or-better and
        # Top-5/Top-10 safe.
        self.logger.subsection("Terminal Campsite Free Time coverage")
        self._ensure_campsite_free_time_coverage()
        self._fix_multislot_integrity()
        self._guarantee_no_gaps()
        self._record_schedule_snapshot("Terminal CFT coverage complete", reason="final-step")

        self.logger.subsection("Terminal guarded soft-constraint cleanup")
        self._final_soft_constraint_cleanup()
        self._fix_multislot_integrity()
        self._guarantee_no_gaps()
        self._record_schedule_snapshot("Terminal soft-constraint cleanup complete", reason="final-step")
        self._validate_critical_constraints()
        # F-04A: fail closed if any post-seal mutator (filler audit, beach
        # saturation, cluster repair) dropped a honored MUST-HONOR day request.
        self._revalidate_sealed_day_requests()
        final_top5, final_details = self._count_non_exempt_top5_misses()
        if final_top5 > 0:
            preview = ", ".join(
                f"{troop}/{activity}#{rank}"
                for troop, activity, rank in final_details[:5]
            )
            raise ValueError(
                f"Final acceptance failed after filler audit: "
                f"{final_top5} non-exempt Top 5 misses remain. Examples: {preview}"
            )

        # C.6b (relocated): Compute Sailing half-slot fills against the FINAL
        # schedule. Sidecar metadata (self.sailing_balls_fills); does NOT
        # mutate self.schedule.entries.
        self.logger.subsection("Scheduling half-slot fills during Sailing (final)")
        self._schedule_sailing_balls_fills()
        self._record_schedule_snapshot("run complete", reason="run-complete", force=True)

        return self.schedule
