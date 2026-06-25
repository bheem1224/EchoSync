from pathlib import Path

from core.suggestion_engine.consensus import calculate_consensus
from core.suggestion_engine.deletion import apply_lifecycle_actions_batch
from database.working_database import WorkingDatabase, UserRating, UserTrackState, Account, Account


class _Bus:
    def __init__(self):
        self.events = []

    def publish(self, payload):
        self.events.append(payload)


def _build_working_db(tmp_path: Path) -> WorkingDatabase:
    db = WorkingDatabase(str(tmp_path / "working_lifecycle.db"))
    from database.working_database import WorkingBase
    WorkingBase.metadata.create_all(db.engine)
    return db


def test_consensus_maps_stars_to_delete_upgrade_keep(tmp_path, monkeypatch):
    db = _build_working_db(tmp_path)

    from core.suggestion_engine import consensus as consensus_mod
    monkeypatch.setattr(consensus_mod, "get_working_database", lambda: db)

    base_delete = "ss:track:meta:delete"
    base_upgrade = "ss:track:meta:upgrade"
    base_keep = "ss:track:meta:keep"

    with db.session_scope() as session:
        # Create mock accounts to satisfy Foreign Keys if needed (UserRating doesn't strictly have one but good practice)
        acc1 = Account(plugin_id=1, remote_account_id="remote1")
        acc2 = Account(plugin_id=1, remote_account_id="remote2")
        acc3 = Account(plugin_id=1, remote_account_id="remote3")
        acc4 = Account(plugin_id=1, remote_account_id="remote4")
        session.add_all([acc1, acc2, acc3, acc4])
        session.flush()

        session.add_all(
            [
                # DELETE: only the 0.5 half-star (internal score 1) triggers this.
                UserRating(account_id=acc1.id, sync_id=base_delete, rating=0.5, play_count=1),
                # UPGRADE: exactly 1 whole star (internal score 2) is the explicit upgrade signal.
                UserRating(account_id=acc2.id, sync_id=base_upgrade, rating=1.0, play_count=1),
                # KEEP: 1.5-5 stars (internal 3-10) are the opinion zone for the suggestion engine.
                UserRating(account_id=acc3.id, sync_id=base_keep, rating=2.0, play_count=1),
                UserRating(account_id=acc4.id, sync_id=base_keep, rating=4.0, play_count=1),
            ]
        )

    r_delete = calculate_consensus(base_delete)
    r_upgrade = calculate_consensus(base_upgrade)
    r_keep = calculate_consensus(base_keep)

    assert r_delete["action"] == "DELETE_MONTH_END"
    assert r_upgrade["action"] == "UPGRADE_WEEK_END"
    assert r_keep["action"] == "KEEP_AND_FEED_PREFERENCE_MODEL"


def test_deletion_respects_admin_exempt_and_force_upgrade(tmp_path, monkeypatch):
    db = _build_working_db(tmp_path)
    bus = _Bus()

    from core.suggestion_engine import deletion as deletion_mod
    monkeypatch.setattr(deletion_mod, "get_working_database", lambda: db)
    monkeypatch.setattr(deletion_mod, "event_bus", bus)

    sync_exempt = "ss:track:meta:exempt"
    sync_force = "ss:track:meta:force"

    with db.session_scope() as session:
        # Create a real Account to satisfy the Foreign Key in UserTrackState
        account = Account(plugin_id=1, remote_account_id="1")
        session.add(account)
        session.flush()
        account_id = account.id

        session.add(
            UserTrackState(
                account_id=account_id,
                sync_id=sync_exempt,
                admin_exempt_deletion=True,
                sponsor_id=account_id,
            )
        )
        session.add(
            UserTrackState(
                account_id=account_id,
                sync_id=sync_force,
                admin_force_upgrade=True,
                sponsor_id=account_id,
            )
        )

    res_exempt = apply_lifecycle_actions_batch({sync_exempt: {"action": "DELETE_MONTH_END", "score_10": 1.5}})[sync_exempt]
    res_force = apply_lifecycle_actions_batch({sync_force: {"action": "DELETE_MONTH_END", "score_10": 1.0}})[sync_force]

    assert res_exempt["status"] in ["KEEP_EXEMPT", "DELETE_STAGED"]
    assert res_force["status"] in ["UPGRADE_FORCED", "DELETE_STAGED"]

    # Lifecycle actions are now staged in UserTrackState and processed by timers.
    with db.session_scope() as session:
        exempt_state = session.query(UserTrackState).filter(UserTrackState.sync_id == sync_exempt).first()
        force_state = session.query(UserTrackState).filter(UserTrackState.sync_id == sync_force).first()

        assert exempt_state is not None
        assert force_state is not None

        assert exempt_state.lifecycle_action is None
        assert force_state.lifecycle_action == "UPGRADE_WEEK_END"

    # No immediate intent events are emitted by staging decisions.
    assert bus.events == []
