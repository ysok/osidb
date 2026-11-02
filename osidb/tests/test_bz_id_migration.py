import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from osidb.models import Flaw
from osidb.tests.factories import FlawFactory


@pytest.mark.unit
@pytest.mark.django_db(transaction=True)
def test_backfill_preserves_legacy_metadata():
    """Migrate real legacy rows and retain their metadata, including invalid IDs."""
    values = ["12345", "", None, "invalid", "9223372036854775808"]
    flaws = [
        FlawFactory(bz_id=None, meta_attr={"bz_id": value, "other": "keep"})
        for value in values
    ]
    targets = MigrationExecutor(connection).loader.graph.leaf_nodes()
    try:
        MigrationExecutor(connection).migrate(
            [("osidb", "0278_affect_resolved_dt_delegated_backfill")]
        )
        MigrationExecutor(connection).migrate(targets)
        for flaw, value in zip(flaws, values):
            flaw.refresh_from_db()
            assert flaw.bz_id == (12345 if value == "12345" else None)
            assert flaw.meta_attr == {"bz_id": value, "other": "keep"}
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT indisvalid FROM pg_index "
                "WHERE indexrelid = 'osidb_flaw_bz_id_idx'::regclass"
            )
            assert cursor.fetchone() == (True,)
    finally:
        MigrationExecutor(connection).migrate(targets)
        Flaw.objects.all().delete()
