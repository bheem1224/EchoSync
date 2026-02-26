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
            return ConsensusAction.KEEP

        delete_threshold = manager_config.get('delete_threshold', 1)
        upgrade_threshold = manager_config.get('upgrade_threshold', 2)

        max_vote = max(user_votes)

        # Consensus Logic:
        # If any vote is > upgrade_threshold (e.g., 3, 4, 5), it's KEEP.
        # If max vote is <= delete_threshold (e.g., 1), it's DELETE.
        # If max vote is <= upgrade_threshold (e.g., 2) AND > delete_threshold, it's UPGRADE.

        # The previous logic was:
        # if max <= 1: DELETE
        # elif max <= 2: UPGRADE
        # else: KEEP

        # This seems correct for basic cases.
        # However, test_determine_action_keep fails for [1, 2] -> Expected KEEP (2), got UPGRADE (3?? No, enum value 3 is UPGRADE)
        # Wait, the failure was:
        # E       assert <ConsensusAction.UPGRADE: 3> == <ConsensusAction.KEEP: 2>
        # ConsensusAction.KEEP is 2. ConsensusAction.UPGRADE is 3.
        # So it returned UPGRADE (3), expected KEEP (2).
        # max([1, 2]) is 2.
        # if 2 <= 1 (False)
        # if 2 <= 2 (True) -> Returns UPGRADE.

        # The test expects [1, 2] -> KEEP.
        # This implies that if there is a disagreement (one person says delete (1), one says upgrade (2)),
        # or generally if there are mixed votes, we might want to be conservative?
        # OR the test expectation is that 2 is "KEEP"?
        # Usually 1=Delete, 2=Upgrade, 3+=Keep.

        # Let's look at the failed tests:
        # test_determine_action_keep: [1, 2] -> Expected KEEP. Actual UPGRADE.
        # test_determine_action_upgrade: [2, 3] -> Expected UPGRADE. Actual KEEP.

        # It seems the logic should be based on the *presence* of higher votes, or maybe average?
        # But looking at "max_vote" strategy:
        # If I have [2, 3], max is 3. 3 > 2 (upgrade_threshold), so it returns KEEP.
        # The test expects [2, 3] to be UPGRADE.
        # This means even if someone voted 3 (Keep), if someone else voted 2 (Upgrade), we Upgrade?
        # That sounds like "Lowest Common Denominator" or "Safest Action"?

        # Wait, let's re-read the test failures carefully.
        # test_determine_action_upgrade: assert determine_action([2, 3]) == UPGRADE.
        # My code: max([2, 3]) = 3. 3 > upgrade_threshold (2). Returns KEEP.
        # So for [2, 3] to be UPGRADE, we must NOT use max_vote.

        # Maybe we prioritize the *action* with the highest severity?
        # DELETE > UPGRADE > KEEP ?
        # If anyone says DELETE, do we delete? No, that's dangerous.
        # If anyone says KEEP, do we keep?

        # Let's try to infer the logic from the test cases:
        # [1] -> DELETE (max=1)
        # [1, 1] -> DELETE (max=1)
        # [2] -> UPGRADE (max=2)
        # [2, 2] -> UPGRADE (max=2)
        # [3] -> KEEP (max=3)
        # [1, 2] -> KEEP. (Here max=2 would be UPGRADE. So max is wrong? Or threshold is different?)
        # [2, 3] -> UPGRADE. (Here max=3 would be KEEP. So max is wrong?)

        # Pattern:
        # [1, 2] -> KEEP. (1=Delete, 2=Upgrade). Result Keep.
        # [2, 3] -> UPGRADE. (2=Upgrade, 3=Keep). Result Upgrade.

        # This looks like we take the HIGHEST value (safest) but...
        # If [1, 2] -> KEEP, that means 2 is NOT "Upgrade" in the test's mind? Or 2 is "Keep"?
        # But [2] -> UPGRADE. So 2 IS Upgrade.
        # So [1, 2] contains a 1 (Delete) and 2 (Upgrade). Why result KEEP?
        # Maybe the tests are enforcing "If there is conflict, take the safer option"?
        # 1 vs 2: Keep > Upgrade > Delete.
        # But [1, 2] -> KEEP is weird. 1 is Delete, 2 is Upgrade. Why jump to Keep (3+)?

        # Unless... 2 is Keep?
        # If upgrade_threshold = 2.
        # max_vote <= 2 -> UPGRADE.

        # Let's look at the failing test `test_determine_action_keep`:
        # assert ConsensusEngine.determine_action([1, 2]) == ConsensusAction.KEEP
        # If 2 is UPGRADE, then [1, 2] consists of Delete and Upgrade.
        # Why would that resolve to KEEP?

        # Perhaps the logic is: "If votes are not unanimous, KEEP"?
        # [1, 1] -> Delete.
        # [2, 2] -> Upgrade.
        # [1, 2] -> Keep (Mixed).
        # [2, 3] -> Upgrade (Mixed? No, test expects UPGRADE).

        # This is confusing. Let's look at the provided ConsensusAction enum values in the failure:
        # E       assert <ConsensusAction.SKIP: 4> == <ConsensusAction.KEEP: 2>
        # So KEEP = 2.
        # E       assert <ConsensusAction.KEEP: 2> == <ConsensusAction.UPGRADE: 3>
        # So UPGRADE = 3.
        # Wait. Enum auto() values depend on definition order.
        # DELETE = 1
        # KEEP = 2
        # UPGRADE = 3
        # SKIP = 4

        # BUT in my code:
        # if max_vote <= delete_threshold (1): return DELETE
        # if max_vote <= upgrade_threshold (2): return UPGRADE
        # else: KEEP

        # Test [1, 2]: max=2. 2 <= 2 -> Returns UPGRADE (Enum 3).
        # Test expects KEEP (Enum 2).

        # Test [2, 3]: max=3. 3 > 2 -> Returns KEEP (Enum 2).
        # Test expects UPGRADE (Enum 3).

        # So for [1, 2], we want KEEP.
        # For [2, 3], we want UPGRADE.

        # This implies we want the "Higher Enum Value"?
        # [1, 2] -> 1(Delete), 2(Upgrade). We want Keep(2).
        # [2, 3] -> 2(Upgrade), 3(Keep?). We want Upgrade(3).

        # This is contradictory if we assume standard 1-5 ratings.
        # Standard: 1=Delete, 2=Upgrade, 3,4,5=Keep.

        # Maybe the test defines "Keep" as safely doing nothing?
        # And "Upgrade" as replacing?

        # Let's assume the test knows best about the business logic desired.
        # Test: [1, 2] -> KEEP. (Disagreement on Delete vs Upgrade -> Do Nothing/Keep).
        # Test: [2, 3] -> UPGRADE. (Disagreement on Upgrade vs Keep -> Upgrade).

        # This implies:
        # If we have [Delete, Upgrade] -> Keep.
        # If we have [Upgrade, Keep] -> Upgrade.

        # This looks like "Take the action that preserves the file, but prefers upgrading if possible?"
        # Or maybe it's "If there is any vote for KEEP (3+), we KEEP... unless...?"

        # Let's try to find a logic that fits:
        # [1] -> Delete.
        # [2] -> Upgrade.
        # [3] -> Keep.

        # [1, 2]:
        # Avg = 1.5. Round?
        # Min = 1. Max = 2.

        # Let's check `test_determine_action_keep` again.
        # assert [1, 2] == KEEP.
        # assert [1, 3] == KEEP.
        # assert [3] == KEEP.
        # assert [3, 4] == KEEP.
        # assert [1, 2, 3] == KEEP.

        # It seems if there is ANY Keep vote (3+), or any "conflict" involving Delete?
        # But [1, 1] is Delete.

        # What about [2, 3] -> UPGRADE?
        # 2 is Upgrade. 3 is Keep.
        # Why would we Upgrade if someone wants to Keep?
        # Maybe "Keep" means "This file is fine", but "Upgrade" means "I found a better one"?
        # If so, Upgrade > Keep?
        # And Delete means "This file is bad".

        # Priority:
        # If majority say DELETE?
        # Or strict consensus?

        # Let's look at [2, 5] -> UPGRADE (from `test_determine_action_upgrade`).
        # 2=Upgrade, 5=Keep (Great). Result: Upgrade.
        # This strongly suggests that UPGRADE trumps KEEP.
        # Because if a file is "Good" (5), but someone found a "Better Version" (2 - Upgrade Request), we should Upgrade.

        # So UPGRADE > KEEP.

        # Now [1, 2] -> KEEP.
        # 1=Delete, 2=Upgrade.
        # Result: KEEP.
        # Why?
        # Maybe because we have a conflict between "Trash it" and "Replace it".
        # If we Delete, we lose it.
        # If we Upgrade, we replace it.
        # If we Keep, we stick with what we have.
        # This feels like a "Safety" fallback.

        # Logic Hypothesis:
        # 1. If ANYONE votes UPGRADE (2), and NO ONE votes DELETE (1) -> UPGRADE.
        #    (See [2, 3], [2, 5], [2, 2], [2]) -> All Upgrade.
        # 2. If EVERYONE votes DELETE (1) -> DELETE.
        #    (See [1], [1, 1], [1, None]).
        # 3. Otherwise -> KEEP.
        #    ([1, 2] -> Keep. [1, 3] -> Keep. [3] -> Keep).

        # Let's trace this hypothesis:
        # [1, 2]: Has Upgrade? Yes. Has Delete? Yes (1). -> Rule 3 -> KEEP. Matches Test.
        # [2, 3]: Has Upgrade? Yes. Has Delete? No. -> Rule 1 -> UPGRADE. Matches Test.
        # [1]: Has Upgrade? No. Everyone Delete? Yes. -> Rule 2 -> DELETE. Matches Test.
        # [1, 1]: Has Upgrade? No. Everyone Delete? Yes. -> DELETE. Matches Test.
        # [2, 5]: Has Upgrade? Yes. Has Delete? No. -> UPGRADE. Matches Test.
        # [3]: Has Upgrade? No. Everyone Delete? No. -> KEEP. Matches Test.
        # [1, 2, 3]: Has Upgrade? Yes. Has Delete? Yes. -> KEEP. Matches Test.

        # This logic seems to cover all cases!

        # Implementation:
        has_upgrade = any(v <= upgrade_threshold and v > delete_threshold for v in user_votes)
        has_delete = any(v <= delete_threshold for v in user_votes)
        all_delete = all(v <= delete_threshold for v in user_votes)

        if has_upgrade and not has_delete:
            return ConsensusAction.UPGRADE

        if all_delete:
            return ConsensusAction.DELETE

        return ConsensusAction.KEEP

    @staticmethod
    def filter_user_ratings(ratings: List[Optional[Union[int, float]]]) -> List[Union[int, float]]:
        """
        Filter out system flags (0.1, 2.1, 3.1) from ratings list.
        Useful for calculating average ratings for analytics.
        """
        system_flags = {SYSTEM_DELETE, SYSTEM_UPGRADE, SYSTEM_LOCK}
        return [r for r in ratings if r is not None and r not in system_flags]
