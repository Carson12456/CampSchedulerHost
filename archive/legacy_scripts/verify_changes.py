
import unittest
from unittest.mock import MagicMock
from models import Troop, Activity, TimeSlot, Day, Zone, Schedule, ScheduleEntry
from evaluate_week_success import evaluate_week, DEFAULT_WEIGHTS
from constrained_scheduler import ConstrainedScheduler, EXCLUSIVE_AREAS

class TestSpineUpdates(unittest.TestCase):
    def setUp(self):
        # Create dummy data
        self.troop = Troop(name="Troop 1", campsite="Campsite A", preferences=["Act1", "Act2", "Act3", "Act4", "Act5", "Act6"])
        self.troops = [self.troop]
        
        # Create activities with correct zones for exclusive area checks
        # Rifle Range activities must be in correct exclusive area group
        self.act1 = Activity(name="Act1", slots=1, zone=Zone.BEACH)
        self.act2 = Activity(name="Act2", slots=1, zone=Zone.TOWER)
        self.act_rifle = Activity(name="Troop Rifle", slots=1, zone=Zone.OFF_CAMP)  
        self.act_shotgun = Activity(name="Troop Shotgun", slots=1, zone=Zone.OFF_CAMP)
        
        self.activities = [self.act1, self.act2, self.act_rifle, self.act_shotgun]
        
        self.scheduler = ConstrainedScheduler(self.troops, self.activities)

    def test_rifle_shotgun_soft_constraint(self):
        """Verify Rifle and Shotgun can be scheduled on same day if constraints are relaxed."""
        day = Day.MONDAY
        slot1 = TimeSlot(day, 1)
        slot2 = TimeSlot(day, 2)
        
        # Schedule Rifle
        self.scheduler.schedule.add_entry(slot1, self.act_rifle, self.troop)
        
        # Check if Shotgun is strictly forbidden (Hard Constraint behavior)
        can_schedule_hard = self.scheduler._can_schedule(self.troop, self.act_shotgun, slot2, day, relax_constraints=False)
        can_schedule_soft = self.scheduler._can_schedule(self.troop, self.act_shotgun, slot2, day, relax_constraints=True)
        
        print(f"\nRifle+Shotgun Hard Check: {can_schedule_hard}")
        print(f"Rifle+Shotgun Soft Check: {can_schedule_soft}")
        
        if hasattr(self.scheduler, 'SAME_DAY_CONFLICTS'):
            print("SAME_DAY_CONFLICTS:", self.scheduler.SAME_DAY_CONFLICTS)
            
        print("EXCLUSIVE_AREAS['Rifle Range']:", EXCLUSIVE_AREAS.get("Rifle Range"))

        self.assertFalse(can_schedule_hard, "Should fail with strict constraints")
        self.assertTrue(can_schedule_soft, "Should pass with relaxed constraints (Soft Constraint)")

    def test_scoring_weights(self):
        """Verify the scoring weights match the new exponential decay model."""
        self.assertEqual(DEFAULT_WEIGHTS["preference_points"]["top5"][0], 80.0, "Rank 1 should be 80 pts")
        
if __name__ == '__main__':
    unittest.main()
