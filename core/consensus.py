from enum import Enum, auto
from typing import List, Optional

class ConsensusAction(Enum):
    DELETE = auto()
    KEEP = auto()
    UPGRADE = auto()

class ConsensusEngine:
    @staticmethod
    def determine_action(ratings: List[Optional[int]]) -> ConsensusAction:
        """
        Determine the consensus action based on a list of user ratings.

        Logic:
        - DELETE: All valid ratings are 1.
        - UPGRADE: Any valid rating is 2, AND all valid ratings are >= 2.
        - KEEP: All other cases (mixed ratings, empty, or all > 2 but no 2s).
        """
        valid_ratings = [r for r in ratings if r is not None]

        if not valid_ratings:
            return ConsensusAction.KEEP

        # Check for DELETE
        if all(r == 1 for r in valid_ratings):
            return ConsensusAction.DELETE

        # Check for UPGRADE
        has_two = any(r == 2 for r in valid_ratings)
        all_ge_two = all(r >= 2 for r in valid_ratings)

        if has_two and all_ge_two:
            return ConsensusAction.UPGRADE

        return ConsensusAction.KEEP
