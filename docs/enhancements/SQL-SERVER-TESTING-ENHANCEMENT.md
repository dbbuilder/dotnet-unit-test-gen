# SQL Server Testing Enhancement

## Current Capabilities (v1.3)

The T-SQL language handler currently supports:

✅ **File-based source detection**
- Scans `.sql` files for CREATE PROCEDURE, CREATE FUNCTION
- Extracts stored procedure and function definitions
- Parses parameters, return types, dependencies

✅ **tSQLt test generation**
- Creates comprehensive tSQLt test suites
- Tests with FakeTable for dependencies
- Covers NULL handling, edge cases, error scenarios
- Tests output parameters and return values
- Verifies data modifications

✅ **Object types supported**
- Stored procedures
- Scalar functions
- Table-valued functions
- Views (basic)
- Triggers (basic)

## Enhancement: Database-Direct Extraction

### Problem

Users want to generate tests directly from a SQL Server database without manually exporting SQL files.

### Solution: Integration with SQLExtract

**SQLExtract Location**: `/mnt/d/dev2/dbbuilder/SQLExtract`

**Capabilities**:
- Extracts 1000+ tables in <30 seconds
- Intelligent dependency ordering with topological sort
- Modular output format (numbered SQL files)
- Support for procedures, functions, views, triggers
- Production-tested on enterprise databases (4,000+ stored procedures)

### Implementation Plan

#### Phase 1: Add Database Connection Support

Add new options to `generate_tests_v2.py`:

```python
@click.option(
    '--db-server',
    type=str,
    help='SQL Server hostname (e.g., localhost or sqltest.schoolvision.net)'
)
@click.option(
    '--db-port',
    type=int,
    default=1433,
    help='SQL Server port (default: 1433)'
)
@click.option(
    '--db-name',
    type=str,
    help='Database name'
)
@click.option(
    '--db-user',
    type=str,
    help='Database username'
)
@click.option(
    '--db-password',
    type=str,
    help='Database password (or use --db-password-env)'
)
@click.option(
    '--db-password-env',
    type=str,
    help='Environment variable containing password'
)
@click.option(
    '--trust-cert',
    is_flag=True,
    help='Trust server certificate (for self-signed certs)'
)
```

#### Phase 2: Add Database Extractor Class

Create `languages/tsql_db_extractor.py`:

```python
"""
SQL Server Database Extractor

Connects to SQL Server and extracts stored procedures and functions
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
        self.server = server
        self.database = database
        self.username = username
        self.password = password
        self.port = port
        self.trust_cert = trust_cert
        self.connection = None

    def connect(self):
        """Establish database connection"""
        trust_param = 'TrustServerCertificate=Yes' if self.trust_cert else ''

        connection_string = (
            f'DRIVER={{ODBC Driver 18 for SQL Server}};'
            f'SERVER={self.server},{self.port};'
            f'DATABASE={self.database};'
            f'UID={self.username};'
            f'PWD={self.password};'
            f'{trust_param}'
        )

        self.connection = pyodbc.connect(connection_string)

    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None

    def extract_procedures(self, schema: Optional[str] = None) -> List[DatabaseObject]:
        """Extract all stored procedures"""
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
            query += f" AND s.name = '{schema}'"

        query += " ORDER BY s.name, p.name"

        cursor = self.connection.cursor()
        cursor.execute(query)

        procedures = []
        for row in cursor:
            procedures.append(DatabaseObject(
                name=row.object_name,
                schema=row.schema_name,
                object_type=row.object_type,
                definition=row.definition
            ))

        return procedures

    def extract_functions(self, schema: Optional[str] = None) -> List[DatabaseObject]:
        """Extract all functions (scalar, table-valued, inline)"""
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
            query += f" AND s.name = '{schema}'"

        query += " ORDER BY s.name, o.name"

        cursor = self.connection.cursor()
        cursor.execute(query)

        functions = []
        for row in cursor:
            functions.append(DatabaseObject(
                name=row.object_name,
                schema=row.schema_name,
                object_type=row.object_type,
                definition=row.definition
            ))

        return functions

    def extract_all_objects(self, schema: Optional[str] = None) -> List[DatabaseObject]:
        """Extract all procedures and functions"""
        return self.extract_procedures(schema) + self.extract_functions(schema)

    def save_to_files(self, objects: List[DatabaseObject], output_dir: Path):
        """Save extracted objects to .sql files"""
        output_dir.mkdir(parents=True, exist_ok=True)

        for obj in objects:
            filename = f"{obj.schema}.{obj.name}.sql"
            file_path = output_dir / filename

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(obj.definition)

        print(f"✓ Saved {len(objects)} objects to {output_dir}")
```

#### Phase 3: Update TSQLLanguageHandler

Add database extraction mode to `TSQLLanguageHandler`:

```python
def detect_files(
    self,
    project_dir: Path,
    pattern: Optional[str] = None,
    db_config: Optional[Dict[str, Any]] = None
) -> List[Path]:
    """
    Find all T-SQL stored procedures and functions

    Args:
        project_dir: Project directory to search (or temp dir for DB extraction)
        pattern: Optional regex pattern to filter
        db_config: Optional database connection config for direct extraction

    Returns:
        List of SQL file paths
    """
    # If database config provided, extract from database
    if db_config:
        return self._extract_from_database(project_dir, pattern, db_config)

    # Otherwise, scan for .sql files (existing behavior)
    return self._scan_sql_files(project_dir, pattern)

def _extract_from_database(
    self,
    project_dir: Path,
    pattern: Optional[str],
    db_config: Dict[str, Any]
) -> List[Path]:
    """Extract objects from database and save to temp files"""
    from .tsql_db_extractor import TSQLDatabaseExtractor

    extractor = TSQLDatabaseExtractor(
        server=db_config['server'],
        database=db_config['database'],
        username=db_config['username'],
        password=db_config['password'],
        port=db_config.get('port', 1433),
        trust_cert=db_config.get('trust_cert', False)
    )

    try:
        extractor.connect()
        objects = extractor.extract_all_objects(schema=db_config.get('schema'))

        # Save to temp directory
        temp_dir = project_dir / '.temp_db_extract'
        extractor.save_to_files(objects, temp_dir)

        # Return file paths
        return list(temp_dir.glob('*.sql'))

    finally:
        extractor.disconnect()
```

### Usage Examples

#### File-based (Current)

```bash
python generate_tests_v2.py /path/to/sql/files \
    --language tsql \
    -o /path/to/tests \
    -p "usp_.*"  # Only test procedures starting with usp_
```

#### Database-direct (Enhanced)

```bash
# Extract from SQL Server and generate tests
python generate_tests_v2.py /path/to/output \
    --language tsql \
    --db-server sqltest.schoolvision.net \
    --db-port 14333 \
    --db-name DEV_SVDB_POS \
    --db-user sv \
    --db-password 'Gv51076!' \
    --trust-cert \
    -p "usp_.*" \
    -o /path/to/tests

# Using environment variable for password
export DB_PASSWORD='Gv51076!'
python generate_tests_v2.py /path/to/output \
    --language tsql \
    --db-server sqltest.schoolvision.net \
    --db-port 14333 \
    --db-name DEV_SVDB_POS \
    --db-user sv \
    --db-password-env DB_PASSWORD \
    --trust-cert
```

#### SQLExtract Integration (Alternative)

If user prefers to use SQLExtract separately:

```bash
# Step 1: Extract with SQLExtract
cd /mnt/d/dev2/dbbuilder/SQLExtract
source venv/bin/activate
python sqlextract.py \
    --server sqltest.schoolvision.net \
    --port 14333 \
    --database DEV_SVDB_POS \
    --user sv \
    --password 'Gv51076!' \
    --trust-cert \
    --output ./extracted_sql

# Step 2: Generate tests from extracted files
cd /mnt/d/Dev2/dotnet-unit-test-gen
source venv/bin/activate
python generate_tests_v2.py ./extracted_sql/06_CREATE_PROCEDURES.sql \
    --language tsql \
    -o ./tests \
    --force
```

## Enhanced Test Coverage

### Current Test Generation

The current prompt generates:
- Basic execution tests
- NULL handling
- Error scenarios
- Output parameter verification
- Data modification verification

### Enhancement: Comprehensive Coverage

Add these test scenarios to the prompt:

#### 1. Transaction Handling

```sql
CREATE PROCEDURE [dbo.Tests].[test usp_UpdateOrder handles transaction rollback]
AS
BEGIN
    -- Arrange
    EXEC tSQLt.FakeTable 'dbo.Orders';
    EXEC tSQLt.FakeTable 'dbo.OrderItems';

    INSERT INTO dbo.Orders (OrderId, Status) VALUES (1, 'Pending');

    -- Simulate constraint violation
    EXEC tSQLt.ApplyConstraint 'dbo.OrderItems', 'FK_OrderItems_Orders';

    -- Act & Assert
    EXEC tSQLt.ExpectException;

    BEGIN TRANSACTION
        EXEC dbo.usp_UpdateOrder @OrderId = 1, @NewStatus = 'Invalid';
    ROLLBACK TRANSACTION

    -- Verify rollback
    DECLARE @Status VARCHAR(50);
    SELECT @Status = Status FROM dbo.Orders WHERE OrderId = 1;
    EXEC tSQLt.AssertEquals 'Pending', @Status;
END;
GO
```

#### 2. Concurrency Testing

```sql
CREATE PROCEDURE [dbo.Tests].[test usp_UpdateInventory handles concurrent updates]
AS
BEGIN
    -- Test optimistic concurrency control
    -- Test row-level locking
    -- Test deadlock scenarios
END;
GO
```

#### 3. Performance Testing

```sql
CREATE PROCEDURE [dbo.Tests].[test usp_GetCustomers performance with large dataset]
AS
BEGIN
    -- Arrange: Insert 10,000 test rows
    EXEC tSQLt.FakeTable 'dbo.Customers';

    DECLARE @i INT = 1;
    WHILE @i <= 10000
    BEGIN
        INSERT INTO dbo.Customers (CustomerId, Name, IsActive)
        VALUES (@i, 'Customer ' + CAST(@i AS VARCHAR), 1);
        SET @i = @i + 1;
    END

    -- Act & Assert: Should complete in <1 second
    DECLARE @StartTime DATETIME = GETDATE();

    EXEC dbo.usp_GetCustomers @IsActive = 1;

    DECLARE @Duration INT = DATEDIFF(MILLISECOND, @StartTime, GETDATE());

    IF @Duration > 1000
    BEGIN
        DECLARE @Msg VARCHAR(100) = 'Performance issue: ' + CAST(@Duration AS VARCHAR) + 'ms';
        RAISERROR(@Msg, 16, 1);
    END
END;
GO
```

#### 4. Data Validation

```sql
CREATE PROCEDURE [dbo.Tests].[test usp_CreateOrder validates business rules]
AS
BEGIN
    -- Test: Cannot create order with negative total
    -- Test: Cannot create order without line items
    -- Test: Cannot create order for inactive customer
    -- Test: Cannot exceed credit limit
END;
GO
```

#### 5. Edge Cases

```sql
CREATE PROCEDURE [dbo.Tests].[test usp_CalculateDiscount handles boundary conditions]
AS
BEGIN
    -- Test: 0% discount
    -- Test: 100% discount
    -- Test: Discount > order total
    -- Test: Negative amounts
    -- Test: Very large amounts (overflow)
    -- Test: Floating point precision
END;
GO
```

### Updated Prompt Template

Enhance the existing prompt with:

```python
**Test Requirements:**
1. Use tSQLt framework
2. Create test class: [{schema}Tests].[test {class_info.name}]
3. Use FakeTable to mock dependencies
4. Test all execution paths (success, errors, edge cases)
5. Test with various parameter combinations
6. Test NULL handling
7. Test output parameters if present
8. Test return value for functions
9. Verify data changes for stored procedures
10. Test transaction handling (COMMIT/ROLLBACK)
11. **NEW**: Test concurrent execution scenarios
12. **NEW**: Test business rule validation
13. **NEW**: Test boundary conditions (min/max values, overflow)
14. **NEW**: Test performance with realistic data volumes
15. **NEW**: Test referential integrity constraints
16. **NEW**: Test trigger interactions (if applicable)
```

## Implementation Priority

### Phase 1: Critical (Implement First)
✅ Current file-based testing (DONE)
🔲 Database connection support (add pyodbc dependency)
🔲 Database extractor class
🔲 Integration with TSQLLanguageHandler

### Phase 2: Enhanced Coverage (Next)
🔲 Transaction handling tests
🔲 Business rule validation tests
🔲 Edge case/boundary tests

### Phase 3: Advanced (Future)
🔲 Concurrency tests
🔲 Performance tests
🔲 Trigger interaction tests

## Dependencies

Add to `requirements.txt`:

```txt
pyodbc>=4.0.39        # SQL Server connectivity
```

## Testing the Implementation

### Test Case 1: Extract and Generate from Database

```bash
# Should extract all procedures from dbo schema and generate tests
python generate_tests_v2.py /tmp/sql_tests \
    --language tsql \
    --db-server localhost \
    --db-name TestDB \
    --db-user sa \
    --db-password 'Password123!' \
    --trust-cert \
    -o ./tests/sql
```

Expected:
- Connects to database
- Extracts all stored procedures and functions
- Saves to temp directory
- Generates tSQLt tests for each object
- Reports success/failure counts

### Test Case 2: Pattern Filtering

```bash
# Should only test objects matching pattern
python generate_tests_v2.py /tmp/sql_tests \
    --language tsql \
    --db-server localhost \
    --db-name TestDB \
    --db-user sa \
    --db-password 'Password123!' \
    -p "^usp_.*"
```

Expected:
- Only generates tests for procedures starting with "usp_"

## Documentation Updates

Update these files:
- `README.md` - Add SQL Server database extraction examples
- `docs/guides/SQL-TESTING.md` - Comprehensive SQL testing guide
- `TESTME_TEMPLATE.md` - Add SQL test execution instructions

## Success Metrics

- ✅ Can extract 100+ procedures in <60 seconds
- ✅ Generates comprehensive tSQLt tests (8-12 tests per object)
- ✅ Tests cover 95%+ of execution paths
- ✅ Cost: <$0.05 per stored procedure
- ✅ Zero manual SQL file export required
