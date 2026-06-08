from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


SQLITE_COLUMN_MIGRATIONS = {
    "stores": {
        "location_text": "ALTER TABLE stores ADD COLUMN location_text VARCHAR(500)",
        "phone": "ALTER TABLE stores ADD COLUMN phone VARCHAR(80)",
    },
    "receipts": {
        "image_path": "ALTER TABLE receipts ADD COLUMN image_path VARCHAR(500)",
    },
}


def run_lightweight_migrations(engine: Engine) -> None:
    """Additive SQLite migrations for local development.

    This project does not use Alembic yet. These migrations keep existing local
    databases usable when new nullable columns are added during early prototyping.
    """
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as connection:
        for table_name, migrations in SQLITE_COLUMN_MIGRATIONS.items():
            if table_name not in existing_tables:
                continue

            existing_columns = {
                column["name"] for column in inspector.get_columns(table_name)
            }
            for column_name, statement in migrations.items():
                if column_name not in existing_columns:
                    connection.execute(text(statement))
