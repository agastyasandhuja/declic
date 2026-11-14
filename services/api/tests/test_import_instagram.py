import base64

from app.core import collections as tables
from app.core.credential_vault import CredentialVault
from app.core.import_instagram import import_connection
from app.core.social_connections import SocialConnections


def test_explicit_handoff_encrypts_session_and_queues_only_bound_owner(database):
    vault = CredentialVault(base64.b64encode(b"a" * 32).decode())
    import_connection(
        database,
        vault,
        {
            "owner_user_id": "alice",
            "surface": "connected",
            "session": {"authorization_data": {"sessionid": "private-session"}},
        },
    )
    social = SocialConnections(database, vault)
    row = social.get("alice")
    assert social.public("alice")["status"] == "connected"
    assert social.public("bob")["status"] == "disconnected"
    assert "private-session" not in str(row)
    assert vault.open("alice", "instagram", row["sealed"])["surface"] == "connected"
    jobs = database.read(lambda tx: tx.find(tables.jobs, {"owner_user_id": "alice"}))
    assert len(jobs) == 1 and jobs[0]["job_type"] == "instagram.refresh"
    assert jobs[0]["input_ref"] == {"connection_id": row["connection_id"]}
    assert "private-session" not in str(jobs)
