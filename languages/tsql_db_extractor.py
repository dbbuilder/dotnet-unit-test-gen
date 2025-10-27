"""
SQL Server Database Extractor

Connects to SQL Server and extracts stored procedures and functions for test generation
"""

import pyodbc
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class DatabaseObject:
    """Represents a SQL Server database object"""
    name: str
    schema: str
    object_type: str  # 'P' = procedure, 'FN' = scalar function, 'TF' = table function
    definition: str
    full_name: str  # schema.name

    def __post_init__(self):
        """Set full_name after initialization"""
        if not self.full_name:
            self.full_name = f"{self.schema}.{self.name}"


class TSQLDatabaseExtractor:
    """Extract stored procedures and functions from SQL Server"""

    def __init__(
        self,
        server: str,
        database: str,
        username: str,
        password: str,
        port: int = 1433,
        trust_cert: bool = False
    ):
        """
        Initialize database extractor

        Args:
            server: SQL Server hostname
            database: Database name
            username: Database username
            password: Database password
            port: SQL Server port (default: 1433)
            trust_cert: Trust server certificate for self-signed certs
        """
        self.server = server
        self.database = database
        self.username = username
        self.password = password
        self.port = port
        self.trust_cert = trust_cert
        self.connection = None

    def connect(self):
        """Establish database connection"""
        trust_param = 'TrustServerCertificate=Yes;' if self.trust_cert else ''

        # Try ODBC Driver 18 (newer)
        try:
            connection_string = (
                f'DRIVER={{ODBC Driver 18 for SQL Server}};'
                f'SERVER={self.server},{self.port};'
                f'DATABASE={self.database};'
                f'UID={self.username};'
                f'PWD={self.password};'
                f'{trust_param}'
            )
            self.connection = pyodbc.connect(connection_string)
            print(f"✓ Connected to {self.server}/{self.database} (ODBC Driver 18)")
            return
        except pyodbc.Error:
            pass  # Try ODBC Driver 17

        # Try ODBC Driver 17 (older, more common)
        try:
            connection_string = (
                f'DRIVER={{ODBC Driver 17 for SQL Server}};'
                f'SERVER={self.server},{self.port};'
                f'DATABASE={self.database};'
                f'UID={self.username};'
                f'PWD={self.password};'
                f'{trust_param}'
            )
            self.connection = pyodbc.connect(connection_string)
            print(f"✓ Connected to {self.server}/{self.database} (ODBC Driver 17)")
            return
        except pyodbc.Error:
            pass  # Try SQL Server

        # Try older SQL Server driver
        connection_string = (
            f'DRIVER={{SQL Server}};'
            f'SERVER={self.server},{self.port};'
            f'DATABASE={self.database};'
            f'UID={self.username};'
            f'PWD={self.password};'
            f'{trust_param}'
        )
        self.connection = pyodbc.connect(connection_string)
        print(f"✓ Connected to {self.server}/{self.database} (SQL Server driver)")

    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
            print("✓ Disconnected from database")

    def extract_procedures(self, schema: Optional[str] = None, pattern: Optional[str] = None) -> List[DatabaseObject]:
        """
        Extract all stored procedures

        Args:
            schema: Filter by schema name (optional)
            pattern: Filter by name pattern (regex, optional)

        Returns:
            List of DatabaseObject instances
        """
        query = """
        SELECT
            s.name AS schema_name,
            p.name AS object_name,
            p.type AS object_type,
            m.definition
        FROM sys.procedures p
        INNER JOIN sys.schemas s ON p.schema_id = s.schema_id
        INNER JOIN sys.sql_modules m ON p.object_id = m.object_id
        WHERE 1=1
        """

        if schema:
            query += f" AND s.name = ?"

        query += " ORDER BY s.name, p.name"

        cursor = self.connection.cursor()
        if schema:
            cursor.execute(query, schema)
        else:
            cursor.execute(query)

        procedures = []
        for row in cursor:
            obj = DatabaseObject(
                name=row.object_name,
                schema=row.schema_name,
                object_type=row.object_type,
                definition=row.definition,
                full_name=f"{row.schema_name}.{row.object_name}"
            )

            # Apply pattern filter if specified
            if pattern:
                import re
                if not re.search(pattern, obj.name, re.IGNORECASE):
                    continue

            procedures.append(obj)

        return procedures

    def extract_functions(self, schema: Optional[str] = None, pattern: Optional[str] = None) -> List[DatabaseObject]:
        """
        Extract all functions (scalar, table-valued, inline)

        Args:
            schema: Filter by schema name (optional)
            pattern: Filter by name pattern (regex, optional)

        Returns:
            List of DatabaseObject instances
        """
        query = """
        SELECT
            s.name AS schema_name,
            o.name AS object_name,
            o.type AS object_type,
            m.definition
        FROM sys.objects o
        INNER JOIN sys.schemas s ON o.schema_id = s.schema_id
        INNER JOIN sys.sql_modules m ON o.object_id = m.object_id
        WHERE o.type IN ('FN', 'IF', 'TF')  -- Scalar, Inline Table, Table-Valued
        """

        if schema:
            query += f" AND s.name = ?"

        query += " ORDER BY s.name, o.name"

        cursor = self.connection.cursor()
        if schema:
            cursor.execute(query, schema)
        else:
            cursor.execute(query)

        functions = []
        for row in cursor:
            obj = DatabaseObject(
                name=row.object_name,
                schema=row.schema_name,
                object_type=row.object_type,
                definition=row.definition,
                full_name=f"{row.schema_name}.{row.object_name}"
            )

            # Apply pattern filter if specified
            if pattern:
                import re
                if not re.search(pattern, obj.name, re.IGNORECASE):
                    continue

            functions.append(obj)

        return functions

    def extract_all_objects(self, schema: Optional[str] = None, pattern: Optional[str] = None) -> List[DatabaseObject]:
        """
        Extract all procedures and functions

        Args:
            schema: Filter by schema name (optional)
            pattern: Filter by name pattern (regex, optional)

        Returns:
            List of DatabaseObject instances
        """
        procedures = self.extract_procedures(schema, pattern)
        functions = self.extract_functions(schema, pattern)
        return procedures + functions

    def save_to_files(self, objects: List[DatabaseObject], output_dir: Path) -> List[Path]:
        """
        Save extracted objects to .sql files

        Args:
            objects: List of database objects to save
            output_dir: Directory to save files

        Returns:
            List of created file paths
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        file_paths = []
        for obj in objects:
            filename = f"{obj.schema}.{obj.name}.sql"
            file_path = output_dir / filename

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(obj.definition)

            file_paths.append(file_path)

        print(f"✓ Saved {len(objects)} objects to {output_dir}")
        return file_paths

    def get_database_stats(self) -> dict:
        """
        Get database statistics

        Returns:
            Dictionary with counts of different object types
        """
        cursor = self.connection.cursor()

        # Count procedures
        cursor.execute("SELECT COUNT(*) FROM sys.procedures")
        proc_count = cursor.fetchone()[0]

        # Count functions
        cursor.execute("SELECT COUNT(*) FROM sys.objects WHERE type IN ('FN', 'IF', 'TF')")
        func_count = cursor.fetchone()[0]

        # Count schemas
        cursor.execute("SELECT COUNT(*) FROM sys.schemas WHERE schema_id > 4")  # Exclude system schemas
        schema_count = cursor.fetchone()[0]

        return {
            'procedures': proc_count,
            'functions': func_count,
            'schemas': schema_count,
            'total_objects': proc_count + func_count
        }


# Example usage
if __name__ == '__main__':
    # Example: Extract from local SQL Server
    extractor = TSQLDatabaseExtractor(
        server='localhost',
        database='TestDB',
        username='sa',
        password='YourPassword123!',
        trust_cert=True
    )

    try:
        extractor.connect()

        # Get stats
        stats = extractor.get_database_stats()
        print(f"\nDatabase Statistics:")
        print(f"  Procedures: {stats['procedures']}")
        print(f"  Functions: {stats['functions']}")
        print(f"  Schemas: {stats['schemas']}")
        print(f"  Total Objects: {stats['total_objects']}")

        # Extract all objects from 'dbo' schema
        objects = extractor.extract_all_objects(schema='dbo')
        print(f"\nExtracted {len(objects)} objects from dbo schema")

        # Save to files
        output_dir = Path('./extracted_sql')
        file_paths = extractor.save_to_files(objects, output_dir)
        print(f"Files saved: {len(file_paths)}")

    finally:
        extractor.disconnect()
