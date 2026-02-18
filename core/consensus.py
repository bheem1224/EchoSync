from enum import Enum, auto
from typing import List, Optional, Union

# System Flags
SYSTEM_DELETE = 0.1
SYSTEM_UPGRADE = 2.1
SYSTEM_LOCK = 3.1

class ConsensusAction(Enum):
    DELETE = auto()
    KEEP = auto()
    UPGRADE = auto()

class ConsensusEngine:
    @staticmethod
    def determine_action(ratings: List[Optional[Union[int, float]]]) -> ConsensusAction:
        """
        Determine the consensus action based on a list of user ratings.

        Logic:
        - SYSTEM_LOCK (3.1): Returns KEEP immediately if present.
        - SYSTEM_DELETE (0.1): Returns DELETE immediately if present (unless Locked).
        - SYSTEM_UPGRADE (2.1): Returns UPGRADE immediately if present (unless Locked or Deleted).
        - DELETE: All valid ratings are 1.
        - UPGRADE: Any valid rating is 2, AND all valid ratings are >= 2.
        - KEEP: All other cases (mixed ratings, empty, or all > 2 but no 2s).
        """
        valid_ratings = [r for r in ratings if r is not None]

        if not valid_ratings:
            return ConsensusAction.KEEP

        # 1. System Lock Check (Highest Priority)
        if SYSTEM_LOCK in valid_ratings:
            return ConsensusAction.KEEP

        # 2. System Delete Check
        if SYSTEM_DELETE in valid_ratings:
            return ConsensusAction.DELETE

        # 3. System Upgrade Check
        if SYSTEM_UPGRADE in valid_ratings:
            return ConsensusAction.UPGRADE

        # Standard User Consensus Logic

        # Check for DELETE (User Vote 1)
        if all(r == 1 for r in valid_ratings):
            return ConsensusAction.DELETE

        # Check for UPGRADE (User Vote 2)
        has_two = any(r == 2 for r in valid_ratings)
        all_ge_two = all(r >= 2 for r in valid_ratings)

        if has_two and all_ge_two:
            return ConsensusAction.UPGRADE

        return ConsensusAction.KEEP

    @staticmethod
    def filter_user_ratings(ratings: List[Optional[Union[int, float]]]) -> List[Union[int, float]]:
        """
        Filter out system flags (0.1, 2.1, 3.1) from ratings list.
        Useful for calculating average ratings for analytics.
        """
        system_flags = {SYSTEM_DELETE, SYSTEM_UPGRADE, SYSTEM_LOCK}
        return [r for r in ratings if r is not None and r not in system_flags]
