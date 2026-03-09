"""Split legacy mixins for ConstrainedScheduler."""

from .placement_and_state import LegacyPart01Mixin
from .top5_and_swaps import LegacyPart02Mixin
from .preference_and_limited import LegacyPart03Mixin
from .sequencing_and_constraints import LegacyPart04Mixin
from .gap_fill_and_stats import LegacyPart05Mixin
from .clustering_and_optimization import LegacyPart06Mixin
from .safety_and_export import LegacyPart07Mixin
from .compatibility_bridges import LegacyPart08Mixin

# Descriptive aliases for readability in composition sites.
PlacementAndStateMixin = LegacyPart01Mixin
Top5AndSwapsMixin = LegacyPart02Mixin
PreferenceAndLimitedMixin = LegacyPart03Mixin
SequencingAndConstraintsMixin = LegacyPart04Mixin
GapFillAndStatsMixin = LegacyPart05Mixin
ClusteringAndOptimizationMixin = LegacyPart06Mixin
SafetyAndExportMixin = LegacyPart07Mixin
CompatibilityBridgesMixin = LegacyPart08Mixin

__all__ = [
    "PlacementAndStateMixin",
    "Top5AndSwapsMixin",
    "PreferenceAndLimitedMixin",
    "SequencingAndConstraintsMixin",
    "GapFillAndStatsMixin",
    "ClusteringAndOptimizationMixin",
    "SafetyAndExportMixin",
    "CompatibilityBridgesMixin",
    "LegacyPart01Mixin",
    "LegacyPart02Mixin",
    "LegacyPart03Mixin",
    "LegacyPart04Mixin",
    "LegacyPart05Mixin",
    "LegacyPart06Mixin",
    "LegacyPart07Mixin",
    "LegacyPart08Mixin",
]
