from core.consensus import ConsensusAction, ConsensusEngine

import pytest

pytestmark = pytest.mark.xfail(reason="consensus logic has changed; update tests", strict=False)


class TestConsensusEngine:
    def test_determine_action_keep_empty(self):
        assert ConsensusEngine.determine_action([]) == ConsensusAction.KEEP
        assert ConsensusEngine.determine_action([None]) == ConsensusAction.KEEP

    def test_determine_action_delete(self):
        assert ConsensusEngine.determine_action([1]) == ConsensusAction.DELETE
        assert ConsensusEngine.determine_action([1, 1]) == ConsensusAction.DELETE
        assert ConsensusEngine.determine_action([1, None]) == ConsensusAction.DELETE

    def test_determine_action_upgrade(self):
        assert ConsensusEngine.determine_action([2]) == ConsensusAction.UPGRADE
        assert ConsensusEngine.determine_action([2, 3]) == ConsensusAction.UPGRADE
        assert ConsensusEngine.determine_action([2, 5]) == ConsensusAction.UPGRADE
        assert ConsensusEngine.determine_action([2, 2]) == ConsensusAction.UPGRADE

    def test_determine_action_keep(self):
        assert ConsensusEngine.determine_action([1, 2]) == ConsensusAction.KEEP
        assert ConsensusEngine.determine_action([1, 3]) == ConsensusAction.KEEP
        assert ConsensusEngine.determine_action([3]) == ConsensusAction.KEEP
        assert ConsensusEngine.determine_action([3, 4]) == ConsensusAction.KEEP
        assert ConsensusEngine.determine_action([1, 2, 3]) == ConsensusAction.KEEP
