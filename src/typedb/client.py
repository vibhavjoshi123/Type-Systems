"""TypeDB 3.x client wrapper with connection management.

Provides async context-manager based access to TypeDB 3.x, with support
for both TypeDB Core (local) and TypeDB Cloud connections.

TypeDB 3.x changes from 2.x:
- Sessions are removed; transactions are opened directly on the driver
- TransactionType.SCHEMA replaces SessionType.SCHEMA + TransactionType.WRITE
- All queries use tx.query("...").resolve()
- Results use .as_concept_rows() or .as_concept_documents()
"""

from __future__ import annotations

import logging
from typing import Any

from src.config import TypeDBSettings, get_settings

logger = logging.getLogger(__name__)


class TypeDBClient:
    """Async TypeDB 3.x client with connection lifecycle management.

    Usage:
        async with TypeDBClient() as client:
            results = await client.query("match $x isa customer;")
    """

    def __init__(self, settings: TypeDBSettings | None = None) -> None:
        self.settings = settings or get_settings().typedb
        self._driver: Any = None
        self._connected = False

    async def connect(self) -> None:
        """Establish connection to TypeDB 3.x server."""
        try:
            from typedb.driver import Credentials, DriverOptions, TypeDB

            creds = Credentials(self.settings.username, self.settings.password)
            opts_kwargs: dict[str, Any] = {
                "is_tls_enabled": self.settings.tls_enabled,
            }
            if self.settings.tls_root_ca:
                opts_kwargs["tls_root_ca_path"] = self.settings.tls_root_ca
            opts = DriverOptions(**opts_kwargs)

            self._driver = TypeDB.driver(self.settings.address, creds, opts)
            self._connected = True
            logger.info("Connected to TypeDB at %s", self.settings.address)
        except ImportError:
            logger.warning(
                "typedb-driver not installed. Using in-memory fallback. "
                "Install with: pip install typedb-driver"
            )
            self._driver = None
            self._connected = False
        except Exception:
            logger.exception("Failed to connect to TypeDB at %s", self.settings.address)
            self._driver = None
            self._connected = False

    async def disconnect(self) -> None:
        """Close the TypeDB connection."""
        if self._driver is not None:
            try:
                self._driver.close()
            except Exception:
                logger.exception("Error closing TypeDB connection")
            finally:
                self._driver = None
                self._connected = False
                logger.info("Disconnected from TypeDB")

    @property
    def is_connected(self) -> bool:
        """Whether the client has an active TypeDB connection."""
        return self._connected

    async def ensure_database(self) -> bool:
        """Create the database if it doesn't exist. Returns True if created."""
        if not self._driver:
            logger.warning("No TypeDB driver available; skipping database creation")
            return False

        db_name = self.settings.database
        if not self._driver.databases.contains(db_name):
            self._driver.databases.create(db_name)
            logger.info("Created database: %s", db_name)
            return True
        logger.info("Database already exists: %s", db_name)
        return False

    async def load_schema(self, schema: str) -> None:
        """Load a TypeQL schema definition into the database.

        TypeDB 3.x: uses TransactionType.SCHEMA directly (no sessions).
        """
        if not self._driver:
            logger.warning("No TypeDB driver available; skipping schema load")
            return

        from typedb.driver import TransactionType

        db_name = self.settings.database
        with self._driver.transaction(db_name, TransactionType.SCHEMA) as tx:
            tx.query(schema).resolve()
            tx.commit()
            logger.info("Schema loaded into database: %s", db_name)

    async def query(self, typeql: str) -> list[dict[str, Any]]:
        """Execute a TypeQL read query and return results.

        TypeDB 3.x: transactions opened directly on driver, results via
        .as_concept_documents() (for fetch) or .as_concept_rows() (for match).
        """
        if not self._driver:
            logger.warning("No TypeDB driver; returning empty results")
            return []

        from typedb.driver import TransactionType

        db_name = self.settings.database
        results: list[dict[str, Any]] = []
        with self._driver.transaction(db_name, TransactionType.READ) as tx:
            answer = tx.query(typeql).resolve()
            # fetch queries return concept documents (JSON-like)
            try:
                for doc in answer.as_concept_documents():
                    results.append(dict(doc) if not isinstance(doc, dict) else doc)
            except Exception:
                # match queries return concept rows
                try:
                    for row in answer.as_concept_rows():
                        row_dict: dict[str, Any] = {}
                        for col in row.column_names():
                            concept = row.get(col)
                            row_dict[col] = _concept_to_value(concept)
                        results.append(row_dict)
                except Exception:
                    logger.debug("Query returned no iterable results")
        return results

    async def write(self, typeql: str) -> None:
        """Execute a TypeQL write query (insert/delete/update)."""
        if not self._driver:
            logger.warning("No TypeDB driver; skipping write operation")
            return

        from typedb.driver import TransactionType

        db_name = self.settings.database
        with self._driver.transaction(db_name, TransactionType.WRITE) as tx:
            tx.query(typeql).resolve()
            tx.commit()

    async def __aenter__(self) -> TypeDBClient:
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.disconnect()


def _concept_to_value(concept: Any) -> Any:
    """Extract a Python value from a TypeDB 3.x concept."""
    try:
        if hasattr(concept, "get_value"):
            return concept.get_value()
        if hasattr(concept, "get_iid"):
            return str(concept.get_iid())
        return str(concept)
    except Exception:
        return str(concept)
