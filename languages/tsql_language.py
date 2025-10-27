"""
T-SQL Language Handler

Provides T-SQL stored procedure testing with tSQLt framework
"""

import re
from pathlib import Path
from typing import Optional, List, Dict, Any

from .base_language import (
    BaseLanguageHandler,
    ClassInfo,
    MethodInfo
)


class TSQLLanguageHandler(BaseLanguageHandler):
    """
    T-SQL language handler with tSQLt testing framework

    Supports:
    - Stored procedure testing
    - Function testing
    - Table-valued functions
    - Scalar functions
    - View testing
    - Trigger testing
    """

    def get_file_extensions(self) -> List[str]:
        """Return T-SQL file extensions"""
        return ['.sql']

    def get_test_file_extension(self) -> str:
        """Return test file extension"""
        return '.test.sql'

    def get_test_framework_default(self) -> str:
        """Return default test framework (tSQLt)"""
        return 'tsqlt'

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
                      Format: {
                          'server': 'hostname',
                          'port': 1433,
                          'database': 'dbname',
                          'username': 'user',
                          'password': 'pass',
                          'trust_cert': True,
                          'schema': 'dbo' (optional)
                      }

        Returns:
            List of SQL file paths
        """
        # If database config provided, extract from database
        if db_config:
            return self._extract_from_database(project_dir, pattern, db_config)

        # Otherwise, scan for .sql files (existing behavior)
        sql_files = []

        # Find .sql files
        for sql_file in project_dir.rglob('*.sql'):
            # Skip test files, migrations
            if any(exclude in str(sql_file).lower() for exclude in ['test', 'migration', 'seed', 'backup']):
                continue

            # Read file to check if it's a stored procedure or function
            try:
                content = sql_file.read_text(encoding='utf-8', errors='ignore').upper()

                # Check for stored procedure or function definitions
                if any(keyword in content for keyword in ['CREATE PROCEDURE', 'CREATE PROC', 'ALTER PROCEDURE', 'CREATE FUNCTION', 'ALTER FUNCTION']):
                    # If pattern specified, check name
                    if pattern:
                        obj_name = self._extract_object_name(content)
                        if obj_name and not re.search(pattern, obj_name, re.IGNORECASE):
                            continue

                    sql_files.append(sql_file)
            except:
                continue

        return sorted(sql_files, key=lambda p: p.name)

    def _extract_from_database(
        self,
        project_dir: Path,
        pattern: Optional[str],
        db_config: Dict[str, Any]
    ) -> List[Path]:
        """
        Extract objects from database and save to temp files

        Args:
            project_dir: Project directory (will create .temp_db_extract subdirectory)
            pattern: Optional regex pattern to filter objects
            db_config: Database connection configuration

        Returns:
            List of SQL file paths
        """
        from .tsql_db_extractor import TSQLDatabaseExtractor

        print(f"\n📊 Extracting from SQL Server database...")
        print(f"   Server: {db_config['server']}")
        print(f"   Database: {db_config['database']}")
        if db_config.get('schema'):
            print(f"   Schema: {db_config['schema']}")

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

            # Get database stats
            stats = extractor.get_database_stats()
            print(f"\n📈 Database Statistics:")
            print(f"   Procedures: {stats['procedures']}")
            print(f"   Functions: {stats['functions']}")
            print(f"   Total Objects: {stats['total_objects']}")

            # Extract objects
            objects = extractor.extract_all_objects(
                schema=db_config.get('schema'),
                pattern=pattern
            )

            if not objects:
                print(f"\n⚠️  No objects found matching criteria")
                return []

            print(f"\n✓ Extracted {len(objects)} objects")

            # Save to temp directory
            temp_dir = project_dir / '.temp_db_extract'
            file_paths = extractor.save_to_files(objects, temp_dir)

            return file_paths

        finally:
            extractor.disconnect()

    def _extract_object_name(self, sql_content: str) -> Optional[str]:
        """Extract stored procedure or function name"""
        # CREATE PROCEDURE dbo.usp_GetUser
        # CREATE FUNCTION dbo.fn_CalculateTotal
        match = re.search(r'(?:CREATE|ALTER)\s+(?:PROCEDURE|PROC|FUNCTION)\s+(?:\[?[^\]]+\]?\.)?(\[?\w+\]?)', sql_content, re.IGNORECASE)
        if match:
            name = match.group(1).strip('[]')
            return name
        return None

    def parse_class(self, file_path: Path) -> Optional[ClassInfo]:
        """
        Parse T-SQL stored procedure or function

        Args:
            file_path: Path to SQL file

        Returns:
            ClassInfo object or None if parsing fails
        """
        try:
            source_code = file_path.read_text(encoding='utf-8', errors='ignore')

            # Extract object name
            obj_name = self._extract_object_name(source_code)
            if not obj_name:
                return None

            # Determine type (stored proc vs function)
            obj_type = self._extract_object_type(source_code)

            # Extract parameters
            parameters = self._extract_parameters(source_code)

            # Extract return type (for functions)
            return_type = self._extract_return_type(source_code)

            # Extract schema
            schema_match = re.search(r'(?:CREATE|ALTER)\s+(?:PROCEDURE|PROC|FUNCTION)\s+\[?(\w+)\]?\.\[?\w+\]?', source_code, re.IGNORECASE)
            schema = schema_match.group(1) if schema_match else 'dbo'

            # Extract referenced tables/views
            dependencies = self._extract_dependencies(source_code)

            # Build metadata
            metadata = {
                'object_type': obj_type,  # 'stored_procedure', 'scalar_function', 'table_function'
                'schema': schema,
                'parameters': parameters,
                'return_type': return_type,
                'has_output_params': any(p.get('is_output') for p in parameters),
                'references_tables': dependencies
            }

            # Create a single "method" representing the stored procedure/function
            method = MethodInfo(
                name=obj_name,
                return_type=return_type or 'void',
                parameters=parameters,
                is_async=False,
                is_public=True
            )

            return ClassInfo(
                name=obj_name,
                namespace=schema,
                file_path=file_path,
                source_code=source_code,
                methods=[method],
                dependencies=dependencies,
                is_controller=False,
                is_service=True,
                language='tsql',
                metadata=metadata
            )

        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None

    def _extract_object_type(self, source_code: str) -> str:
        """Determine if stored procedure or function type"""
        upper_code = source_code.upper()

        if 'CREATE PROCEDURE' in upper_code or 'ALTER PROCEDURE' in upper_code or 'CREATE PROC' in upper_code:
            return 'stored_procedure'
        elif 'RETURNS TABLE' in upper_code:
            return 'table_function'
        elif 'RETURNS' in upper_code:
            return 'scalar_function'
        else:
            return 'stored_procedure'

    def _extract_parameters(self, source_code: str) -> List[Dict[str, str]]:
        """Extract parameters from stored procedure/function"""
        parameters = []

        # Find parameter block
        # CREATE PROCEDURE usp_GetUser (@UserId INT, @IsActive BIT = 1, @Result VARCHAR(100) OUTPUT)
        param_pattern = r'@(\w+)\s+([A-Z]+(?:\([^\)]+\))?)\s*(=\s*[^,\)]+)?(?:\s+OUTPUT)?'

        for match in re.finditer(param_pattern, source_code, re.IGNORECASE):
            param_name = match.group(1)
            param_type = match.group(2)
            has_default = match.group(3) is not None
            is_output = 'OUTPUT' in match.group(0).upper()

            parameters.append({
                'name': param_name,
                'type': param_type,
                'has_default': has_default,
                'is_output': is_output
            })

        return parameters

    def _extract_return_type(self, source_code: str) -> Optional[str]:
        """Extract return type for functions"""
        # RETURNS INT
        # RETURNS TABLE
        match = re.search(r'RETURNS\s+([A-Z]+(?:\([^\)]+\))?)', source_code, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def _extract_dependencies(self, source_code: str) -> List[str]:
        """Extract referenced tables and views"""
        dependencies = []

        # Find FROM/JOIN clauses
        # FROM dbo.Users
        # JOIN dbo.Orders ON ...
        table_pattern = r'(?:FROM|JOIN)\s+(?:\[?(\w+)\]?\.)?\[?(\w+)\]?'

        for match in re.finditer(table_pattern, source_code, re.IGNORECASE):
            schema = match.group(1) or 'dbo'
            table = match.group(2)
            full_name = f"{schema}.{table}"
            if full_name not in dependencies:
                dependencies.append(full_name)

        return dependencies

    def generate_test_prompt(
        self,
        class_info: ClassInfo,
        patterns: Dict[str, Any],
        test_framework: str = 'tsqlt',
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate AI prompt for T-SQL test generation

        Args:
            class_info: Parsed stored procedure/function info
            patterns: Learned patterns
            test_framework: Test framework (tsqlt)
            context: Additional context

        Returns:
            Formatted prompt string
        """
        metadata = class_info.metadata
        obj_type = metadata.get('object_type', 'stored_procedure')
        schema = metadata.get('schema', 'dbo')
        parameters = metadata.get('parameters', [])
        return_type = metadata.get('return_type')
        has_output = metadata.get('has_output_params', False)

        param_str = '\n'.join([
            f"  - @{p['name']} {p['type']}" + (" OUTPUT" if p.get('is_output') else "") + (" = default" if p.get('has_default') else "")
            for p in parameters
        ]) if parameters else '  None'

        dependencies_str = '\n'.join([f"  - {dep}" for dep in class_info.dependencies]) if class_info.dependencies else '  None'

        prompt = f"""Generate comprehensive tSQLt unit tests for the following T-SQL {obj_type}.

**Object:** {schema}.{class_info.name}
**Type:** {obj_type.upper()}

**Source Code:**
```sql
{class_info.source_code}
```

**Object Details:**
- Name: {class_info.name}
- Schema: {schema}
- Parameters:
{param_str}
- Return Type: {return_type or 'N/A (stored procedure)'}
- Has Output Parameters: {has_output}
- Referenced Tables:
{dependencies_str}

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
10. Test transaction handling

**tSQLt Framework Functions:**
- EXEC tSQLt.NewTestClass '{schema}Tests'
- EXEC tSQLt.FakeTable 'dbo.TableName'
- EXEC tSQLt.AssertEquals @Expected, @Actual
- EXEC tSQLt.AssertEqualsTable @Expected, @Actual
- EXEC tSQLt.ExpectException

**Example Test Structure:**
```sql
-- Create test class
EXEC tSQLt.NewTestClass '{schema}Tests';
GO

-- Test 1: Basic successful execution
CREATE PROCEDURE [{schema}Tests].[test {class_info.name} returns expected results with valid input]
AS
BEGIN
    -- Arrange
    EXEC tSQLt.FakeTable 'dbo.Users';

    INSERT INTO dbo.Users (UserId, Name, IsActive)
    VALUES (1, 'Test User', 1);

    DECLARE @Result VARCHAR(100);

    -- Act
    EXEC {schema}.{class_info.name}
        @UserId = 1,
        @Result = @Result OUTPUT;

    -- Assert
    EXEC tSQLt.AssertEquals 'Test User', @Result;
END;
GO

-- Test 2: Handle NULL input
CREATE PROCEDURE [{schema}Tests].[test {class_info.name} handles NULL input gracefully]
AS
BEGIN
    -- Arrange
    EXEC tSQLt.FakeTable 'dbo.Users';

    -- Act & Assert
    EXEC tSQLt.ExpectException
        @ExpectedMessagePattern = '%cannot be NULL%';

    EXEC {schema}.{class_info.name}
        @UserId = NULL;
END;
GO

-- Test 3: Verify data modifications
CREATE PROCEDURE [{schema}Tests].[test {class_info.name} updates data correctly]
AS
BEGIN
    -- Arrange
    EXEC tSQLt.FakeTable 'dbo.Orders';

    INSERT INTO dbo.Orders (OrderId, Status)
    VALUES (1, 'Pending');

    -- Act
    EXEC {schema}.{class_info.name}
        @OrderId = 1;

    -- Assert
    DECLARE @ActualStatus VARCHAR(50);
    SELECT @ActualStatus = Status FROM dbo.Orders WHERE OrderId = 1;

    EXEC tSQLt.AssertEquals 'Completed', @ActualStatus;
END;
GO
```

**Important Notes:**
- Each test should be completely isolated
- Use FakeTable for all dependent tables
- Reset state in each test
- Test both positive and negative scenarios
- Include descriptive test names

Generate comprehensive tSQLt tests covering all execution paths now:"""

        return prompt

    def extract_code_from_response(self, response: str) -> str:
        """
        Extract SQL code from AI response (may contain markdown)

        Args:
            response: AI response text

        Returns:
            Extracted SQL code
        """
        # Try to find ```sql or ```tsql blocks
        pattern = r'```(?:sql|tsql|plsql)?\n(.*?)\n```'
        matches = re.findall(pattern, response, re.DOTALL)

        if matches:
            return matches[0].strip()

        # If no code block, return entire response
        return response.strip()

    def auto_fix_syntax(self, test_code: str) -> tuple[str, List[str], List[str]]:
        """
        Auto-fix common T-SQL test syntax issues

        Args:
            test_code: Generated test code

        Returns:
            Tuple of (fixed_code, fixes_applied, warnings)
        """
        fixed_code = test_code
        fixes = []
        warnings = []

        # Ensure GO statements are on their own lines
        fixed_code = re.sub(r';\s*GO\s*;', ';\nGO\n', fixed_code, flags=re.IGNORECASE)
        fixed_code = re.sub(r'END\s*GO', 'END\nGO', fixed_code, flags=re.IGNORECASE)

        # Ensure test class creation is at the top
        if 'NewTestClass' not in fixed_code:
            # Try to infer schema from test code
            schema_match = re.search(r'EXEC\s+(\w+)\.', fixed_code)
            schema = schema_match.group(1) if schema_match else 'dbo'
            fixed_code = f"EXEC tSQLt.NewTestClass '{schema}Tests';\nGO\n\n" + fixed_code
            fixes.append(f"Added test class creation for {schema}Tests")

        return fixed_code, fixes, warnings

    def get_test_class_name(self, class_name: str) -> str:
        """Generate test file name"""
        return f"{class_name}.test"

    def get_test_namespace(self, namespace: str) -> str:
        """Return test schema"""
        return f"{namespace}Tests"

    def get_language_name(self) -> str:
        """Return language name"""
        return "T-SQL"

    def get_test_framework(self) -> str:
        """Return test framework"""
        return 'tSQLt'

    def get_test_file_path(self, source_path: Path, output_dir: Path) -> Path:
        """Generate test file path for T-SQL procedure"""
        # For T-SQL, create tests in output directory
        test_name = source_path.stem + '.test.sql'
        return output_dir / test_name
