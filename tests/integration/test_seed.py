"""Phase 5: seeds are idempotent and reset+seed reproduces one world (live DB)."""

from sqlalchemy import text

from database.seeds import loader
from database.seeds.check import HELD_OUT_MIN, check_seeded, check_static


def _ticket_total(conn) -> int:
    return conn.execute(text("SELECT count(*) FROM biz.tickets")).scalar()


def test_static_checks_clean():
    """Catalogue shape, ranges, references, and varieties (no DB needed)."""
    assert check_static() == []


def test_seed_idempotent(admin_conn):
    """Seeding twice changes nothing: same hash, same row counts."""
    loader.seed()
    with loader.admin_engine().connect() as conn:
        hash_before = loader.compute_world_hash(conn)
        tickets_before = _ticket_total(conn)
    loader.seed()
    with loader.admin_engine().connect() as conn:
        assert loader.compute_world_hash(conn) == hash_before
        assert _ticket_total(conn) == tickets_before


def test_reset_seed_reproduces_identical_world(admin_conn):
    """Definition of done: reset && seed twice gives one identical hash."""
    loader.reset()
    loader.seed()
    with loader.admin_engine().connect() as conn:
        first = loader.compute_world_hash(conn)
    loader.reset()
    loader.seed()
    with loader.admin_engine().connect() as conn:
        assert loader.compute_world_hash(conn) == first


def test_about_forty_tickets_seeded(admin_conn):
    """40 scenario tickets plus 5 backstory tickets."""
    loader.seed()
    total = _ticket_total(admin_conn)
    scenario = admin_conn.execute(
        text("SELECT count(*) FROM biz.tickets WHERE category <> 'history'")
    ).scalar()
    assert scenario == 40
    assert total == 45


def test_seeded_checks_clean(admin_conn):
    """Every scenario ticket/order exists; history facts match the DB."""
    loader.seed()
    assert check_seeded(admin_conn) == []


def test_held_out_range_reserved():
    """Seeded ids stay below the held-out range (Phase 28 seals S901+)."""
    assert HELD_OUT_MIN == 901
