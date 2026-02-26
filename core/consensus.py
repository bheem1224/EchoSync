from enum import Enum, auto
from typing import List, Optional, Union
from core.settings import config_manager

# System Flags
SYSTEM_DELETE = 0.1
SYSTEM_UPGRADE = 2.1
SYSTEM_LOCK = 3.1

class ConsensusAction(Enum):
    DELETE = auto()
    KEEP = auto()
    UPGRADE = auto()
    SKIP = auto() # No valid user votes

class ConsensusEngine:
    @staticmethod
    def determine_action(ratings: List[Optional[Union[int, float]]]) -> ConsensusAction:
        """
        Determine the consensus action based on a list of user ratings.
        Respects strict order of operations: System Flags > Global Switch > User Votes.
        """
        valid_ratings = [r for r in ratings if r is not None]

        # 1. System Flags (Decimal First)
        # 3.1 (Lock/Pardon) -> Return "KEEP". Wins against everything.
        if SYSTEM_LOCK in valid_ratings:
            return ConsensusAction.KEEP

        # 0.1 (Force Delete) -> Return "DELETE".
        if SYSTEM_DELETE in valid_ratings:
            return ConsensusAction.DELETE

        # 2.1 (Force Upgrade) -> Return "UPGRADE".
        if SYSTEM_UPGRADE in valid_ratings:
            return ConsensusAction.UPGRADE

        # 2. Global Switch
        # Ideally, we inject settings, but for static method we fetch from config_manager or defaults
        # We'll assume a 'manager' section in config
        manager_config = config_manager.get('manager', {})
        manager_enabled = manager_config.get('enabled', True)

        if not manager_enabled:
            return ConsensusAction.KEEP

        # 3. Check User Votes (Integers Only)
        user_votes = [r for r in valid_ratings if isinstance(r, int) or (isinstance(r, float) and r.is_integer())]
        user_votes = [int(r) for r in user_votes] # Cast to int to be safe

        if not user_votes:
            return ConsensusAction.SKIP

        delete_threshold = manager_config.get('delete_threshold', 1)
        upgrade_threshold = manager_config.get('upgrade_threshold', 2)

        max_vote = max(user_votes)

        if max_vote <= delete_threshold:
            return ConsensusAction.DELETE

        if max_vote <= upgrade_threshold:
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
