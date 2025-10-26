# Database Test Generator Module Specification

**Date**: 2025-10-25
**Status**: Planning Phase
**Target**: Database integration and repository testing
**Priority**: Phase 3 (Medium - needed for PaymentAPI data access layer)

---

## Executive Summary

The Database Test Generator creates comprehensive tests for database operations, repository patterns, Entity Framework contexts, and SQL stored procedures. It validates data access logic, transaction handling, and data integrity constraints.

**Primary Use Cases**:
1. **PaymentAPI Data Access Testing** - Test PaymentDataAccess layer
2. **Repository Pattern Testing** - Validate CRUD operations
3. **Stored Procedure Testing** - Test SQL Server procedures
4. **Entity Framework Testing** - Validate EF Core queries and migrations

**Technology Stack**:
- **Backend DB Tests**: xUnit + InMemory Database / TestContainers
- **EF Core**: DbContext mocking and integration tests
- **SQL Server**: Stored procedure validation
- **Transaction Testing**: Rollback and isolation testing

---

## Architecture Design

### Module Structure

```
dotnet-unit-test-gen/
├── generators/
│   └── database_generator.py           # NEW - DB test generator
├── analyzers/
│   ├── repository_analyzer.py          # NEW - Repository pattern analyzer
│   ├── dbcontext_analyzer.py           # NEW - EF Core context analyzer
│   └── sql_procedure_analyzer.py       # NEW - SQL procedure analyzer
├── templates/
│   └── database/
│       ├── repository_tests.jinja2         # Repository CRUD tests
│       ├── dbcontext_tests.jinja2          # EF Core context tests
│       ├── stored_procedure_tests.jinja2   # SQL procedure tests
│       └── integration_db_tests.jinja2     # Full integration tests
└── fixtures/
    └── test_data_builder.py            # NEW - Test data generation
```

---

## Database Analysis Strategy

### Repository Pattern Analysis

```python
class RepositoryAnalyzer(BaseAnalyzer):
    """Analyzes repository classes for test generation"""

    def analyze_repository(self, file_path: str) -> Dict[str, Any]:
        """
        Extract repository operations:
        - Entity type
        - CRUD methods (GetById, GetAll, Add, Update, Delete)
        - Query methods
        - Transaction handling
        - Dependency injection
        """
        content = Path(file_path).read_text()

        return {
            "repository_name": self._extract_class_name(file_path),
            "entity_type": self._extract_entity_type(content),
            "crud_methods": self._extract_crud_methods(content),
            "query_methods": self._extract_query_methods(content),
            "dependencies": self._extract_dependencies(content),
            "uses_transactions": self._detect_transactions(content)
        }

    def _extract_entity_type(self, content: str) -> str:
        """
        Identify the entity type being managed:

        VB.NET pattern:
        Public Class PaymentRepository
            Inherits Repository(Of Payment)

        C# pattern:
        public class PaymentRepository : Repository<Payment>
        """
        # VB.NET pattern
        vb_match = re.search(r'Inherits\s+Repository\(Of\s+(\w+)\)', content)
        if vb_match:
            return vb_match.group(1)

        # C# pattern
        cs_match = re.search(r':\s*Repository<(\w+)>', content)
        if cs_match:
            return cs_match.group(1)

        return "Unknown"

    def _extract_crud_methods(self, content: str) -> Dict[str, Dict[str, Any]]:
        """
        Extract CRUD method signatures:
        - GetById(id)
        - GetAll()
        - Add(entity)
        - Update(entity)
        - Delete(id)
        """
        crud_methods = {}

        # VB.NET method pattern
        vb_pattern = r'Public\s+(Function|Sub)\s+(\w+)\(([^)]*)\)\s+As\s+(\w+(?:\(Of \w+\))?)'

        for match in re.finditer(vb_pattern, content):
            method_type, name, params, return_type = match.groups()

            if name in ['GetById', 'GetAll', 'Add', 'Update', 'Delete', 'Insert']:
                crud_methods[name] = {
                    "name": name,
                    "parameters": self._parse_vb_parameters(params),
                    "return_type": return_type,
                    "is_async": "Async" in return_type or "Task" in return_type
                }

        return crud_methods

    def _extract_query_methods(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract custom query methods:
        - FindByEmail(email)
        - GetActivePayments()
        - SearchByDateRange(start, end)
        """
        query_methods = []

        # Pattern for custom query methods (not CRUD)
        vb_pattern = r'Public\s+Function\s+(Get\w+|Find\w+|Search\w+)\(([^)]*)\)\s+As\s+(\w+(?:\(Of \w+\))?)'

        for match in re.finditer(vb_pattern, content):
            name, params, return_type = match.groups()

            if name not in ['GetById', 'GetAll']:
                query_methods.append({
                    "name": name,
                    "parameters": self._parse_vb_parameters(params),
                    "return_type": return_type,
                    "is_async": "Async" in return_type or "Task" in return_type
                })

        return query_methods
```

### EF Core DbContext Analysis

```python
class DbContextAnalyzer(BaseAnalyzer):
    """Analyzes Entity Framework DbContext classes"""

    def analyze_dbcontext(self, file_path: str) -> Dict[str, Any]:
        """
        Extract DbContext information:
        - DbSet properties (entity collections)
        - OnModelCreating configurations
        - Database relationships
        - Indexes and constraints
        """
        content = Path(file_path).read_text()

        return {
            "context_name": self._extract_class_name(file_path),
            "dbsets": self._extract_dbsets(content),
            "relationships": self._extract_relationships(content),
            "configurations": self._extract_model_configurations(content)
        }

    def _extract_dbsets(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract DbSet<T> properties:

        C# pattern:
        public DbSet<Payment> Payments { get; set; }

        VB.NET pattern:
        Public Property Payments As DbSet(Of Payment)
        """
        dbsets = []

        # C# pattern
        cs_pattern = r'public\s+DbSet<(\w+)>\s+(\w+)\s+{\s*get;\s*set;\s*}'
        for match in re.finditer(cs_pattern, content):
            entity_type, property_name = match.groups()
            dbsets.append({
                "entity_type": entity_type,
                "property_name": property_name
            })

        # VB.NET pattern
        vb_pattern = r'Public\s+Property\s+(\w+)\s+As\s+DbSet\(Of\s+(\w+)\)'
        for match in re.finditer(vb_pattern, content):
            property_name, entity_type = match.groups()
            dbsets.append({
                "entity_type": entity_type,
                "property_name": property_name
            })

        return dbsets

    def _extract_relationships(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract entity relationships from OnModelCreating:
        - One-to-many
        - Many-to-many
        - Foreign keys
        - Navigation properties
        """
        relationships = []

        # Look for HasOne, HasMany, WithOne, WithMany patterns
        relationship_pattern = r'HasOne<(\w+)>\(\)\.WithMany\(\)\.HasForeignKey\("(\w+)"\)'

        for match in re.finditer(relationship_pattern, content):
            principal_entity, foreign_key = match.groups()
            relationships.append({
                "type": "one-to-many",
                "principal": principal_entity,
                "foreign_key": foreign_key
            })

        return relationships
```

### SQL Stored Procedure Analysis

```python
class SqlProcedureAnalyzer:
    """Analyzes SQL Server stored procedures"""

    def analyze_procedure(self, procedure_text: str) -> Dict[str, Any]:
        """
        Extract stored procedure information:
        - Procedure name
        - Input parameters
        - Output parameters
        - Return type (table, scalar, none)
        - Transaction handling
        """
        return {
            "name": self._extract_procedure_name(procedure_text),
            "parameters": self._extract_parameters(procedure_text),
            "returns_table": self._check_returns_table(procedure_text),
            "uses_transaction": "BEGIN TRANSACTION" in procedure_text,
            "modifies_data": self._check_data_modification(procedure_text)
        }

    def _extract_parameters(self, procedure_text: str) -> List[Dict[str, Any]]:
        """
        Extract parameters from CREATE PROCEDURE statement:

        Example:
        CREATE PROCEDURE [dbo].[sp_InsertPayment]
            @TransactionId VARCHAR(50),
            @Amount DECIMAL(18,2),
            @CustomerId INT OUTPUT
        AS
        """
        params = []

        # Pattern: @ParamName TYPE [OUTPUT]
        param_pattern = r'@(\w+)\s+([\w()]+)(?:\s+(OUTPUT))?'

        for match in re.finditer(param_pattern, procedure_text):
            name, data_type, is_output = match.groups()
            params.append({
                "name": name,
                "type": data_type,
                "is_output": bool(is_output)
            })

        return params

    def _check_returns_table(self, procedure_text: str) -> bool:
        """Check if procedure returns a result set"""
        return "SELECT" in procedure_text and "@" not in procedure_text.split("SELECT")[1].split()[0]

    def _check_data_modification(self, procedure_text: str) -> Dict[str, bool]:
        """Check what type of data modification occurs"""
        return {
            "inserts": "INSERT INTO" in procedure_text,
            "updates": "UPDATE" in procedure_text,
            "deletes": "DELETE FROM" in procedure_text
        }
```

---

## Test Generation Templates

### Repository Test Template

```csharp
// templates/database/repository_tests.jinja2
using System;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.EntityFrameworkCore;
using Xunit;
using {{ namespace }}.Data;
using {{ namespace }}.Models;
using {{ namespace }}.Repositories;

namespace {{ namespace }}.Tests.Repositories
{
    public class {{ repository_name }}Tests : IDisposable
    {
        private readonly DbContextOptions<{{ context_name }}> _options;
        private readonly {{ context_name }} _context;
        private readonly {{ repository_name }} _repository;

        public {{ repository_name }}Tests()
        {
            // Use InMemory database for testing
            _options = new DbContextOptionsBuilder<{{ context_name }}>()
                .UseInMemoryDatabase(databaseName: "Test_{{ repository_name }}_{{ guid }}")
                .Options;

            _context = new {{ context_name }}(_options);
            _repository = new {{ repository_name }}(_context);
        }

        public void Dispose()
        {
            _context.Database.EnsureDeleted();
            _context.Dispose();
        }

        {% if 'GetById' in crud_methods %}
        [Fact]
        public async Task GetById_WithValidId_ReturnsEntity()
        {
            // Arrange
            var entity = new {{ entity_type }}
            {
                {% for prop in entity_properties %}
                {{ prop.name }} = {{ prop.test_value }},
                {% endfor %}
            };
            _context.{{ dbset_name }}.Add(entity);
            await _context.SaveChangesAsync();

            // Act
            var result = await _repository.GetById(entity.Id);

            // Assert
            Assert.NotNull(result);
            Assert.Equal(entity.Id, result.Id);
            {% for prop in entity_properties %}
            Assert.Equal(entity.{{ prop.name }}, result.{{ prop.name }});
            {% endfor %}
        }

        [Fact]
        public async Task GetById_WithInvalidId_ReturnsNull()
        {
            // Act
            var result = await _repository.GetById(999999);

            // Assert
            Assert.Null(result);
        }
        {% endif %}

        {% if 'GetAll' in crud_methods %}
        [Fact]
        public async Task GetAll_WithMultipleEntities_ReturnsAll()
        {
            // Arrange
            var entities = new[]
            {
                new {{ entity_type }} { {% for prop in entity_properties %}{{ prop.name }} = {{ prop.test_value_1 }}{{ ', ' if not loop.last }}{% endfor %} },
                new {{ entity_type }} { {% for prop in entity_properties %}{{ prop.name }} = {{ prop.test_value_2 }}{{ ', ' if not loop.last }}{% endfor %} },
                new {{ entity_type }} { {% for prop in entity_properties %}{{ prop.name }} = {{ prop.test_value_3 }}{{ ', ' if not loop.last }}{% endfor %} }
            };
            _context.{{ dbset_name }}.AddRange(entities);
            await _context.SaveChangesAsync();

            // Act
            var result = await _repository.GetAll();

            // Assert
            Assert.NotNull(result);
            Assert.Equal(3, result.Count());
        }

        [Fact]
        public async Task GetAll_WithEmptyDatabase_ReturnsEmpty()
        {
            // Act
            var result = await _repository.GetAll();

            // Assert
            Assert.NotNull(result);
            Assert.Empty(result);
        }
        {% endif %}

        {% if 'Add' in crud_methods or 'Insert' in crud_methods %}
        [Fact]
        public async Task Add_WithValidEntity_InsertsToDatabase()
        {
            // Arrange
            var entity = new {{ entity_type }}
            {
                {% for prop in entity_properties %}
                {{ prop.name }} = {{ prop.test_value }},
                {% endfor %}
            };

            // Act
            var result = await _repository.Add(entity);
            await _context.SaveChangesAsync();

            // Assert
            Assert.NotNull(result);
            Assert.True(result.Id > 0);

            var dbEntity = await _context.{{ dbset_name }}.FindAsync(result.Id);
            Assert.NotNull(dbEntity);
            {% for prop in entity_properties %}
            Assert.Equal(entity.{{ prop.name }}, dbEntity.{{ prop.name }});
            {% endfor %}
        }

        [Fact]
        public async Task Add_WithNullEntity_ThrowsException()
        {
            // Act & Assert
            await Assert.ThrowsAsync<ArgumentNullException>(
                async () => await _repository.Add(null)
            );
        }
        {% endif %}

        {% if 'Update' in crud_methods %}
        [Fact]
        public async Task Update_WithValidEntity_UpdatesDatabase()
        {
            // Arrange
            var entity = new {{ entity_type }}
            {
                {% for prop in entity_properties %}
                {{ prop.name }} = {{ prop.test_value }},
                {% endfor %}
            };
            _context.{{ dbset_name }}.Add(entity);
            await _context.SaveChangesAsync();

            // Modify entity
            {% for prop in updatable_properties %}
            entity.{{ prop.name }} = {{ prop.updated_value }};
            {% endfor %}

            // Act
            await _repository.Update(entity);
            await _context.SaveChangesAsync();

            // Assert
            var dbEntity = await _context.{{ dbset_name }}.FindAsync(entity.Id);
            {% for prop in updatable_properties %}
            Assert.Equal({{ prop.updated_value }}, dbEntity.{{ prop.name }});
            {% endfor %}
        }
        {% endif %}

        {% if 'Delete' in crud_methods %}
        [Fact]
        public async Task Delete_WithValidId_RemovesFromDatabase()
        {
            // Arrange
            var entity = new {{ entity_type }}
            {
                {% for prop in entity_properties %}
                {{ prop.name }} = {{ prop.test_value }},
                {% endfor %}
            };
            _context.{{ dbset_name }}.Add(entity);
            await _context.SaveChangesAsync();
            var entityId = entity.Id;

            // Act
            await _repository.Delete(entityId);
            await _context.SaveChangesAsync();

            // Assert
            var dbEntity = await _context.{{ dbset_name }}.FindAsync(entityId);
            Assert.Null(dbEntity);
        }

        [Fact]
        public async Task Delete_WithInvalidId_DoesNotThrow()
        {
            // Act & Assert (should not throw)
            await _repository.Delete(999999);
        }
        {% endif %}

        {% for query_method in query_methods %}
        [Fact]
        public async Task {{ query_method.name }}_WithValidInput_ReturnsExpectedResults()
        {
            // Arrange
            {% for param in query_method.parameters %}
            var {{ param.name }} = {{ param.test_value }};
            {% endfor %}

            // TODO: Add test data to database that matches query criteria

            // Act
            var result = await _repository.{{ query_method.name }}(
                {% for param in query_method.parameters %}
                {{ param.name }}{{ ', ' if not loop.last }}
                {% endfor %}
            );

            // Assert
            Assert.NotNull(result);
            // TODO: Add specific assertions based on query logic
        }
        {% endfor %}
    }
}
```

### Stored Procedure Test Template

```csharp
// templates/database/stored_procedure_tests.jinja2
using System;
using System.Data;
using System.Data.SqlClient;
using System.Threading.Tasks;
using Xunit;

namespace {{ namespace }}.Tests.Database
{
    public class {{ procedure_name }}Tests : IClassFixture<DatabaseFixture>
    {
        private readonly DatabaseFixture _fixture;

        public {{ procedure_name }}Tests(DatabaseFixture fixture)
        {
            _fixture = fixture;
        }

        [Fact]
        public async Task {{ procedure_name }}_WithValidParameters_ExecutesSuccessfully()
        {
            // Arrange
            using var connection = _fixture.CreateConnection();
            using var command = new SqlCommand("{{ procedure_name }}", connection);
            command.CommandType = CommandType.StoredProcedure;

            {% for param in input_parameters %}
            command.Parameters.AddWithValue("@{{ param.name }}", {{ param.test_value }});
            {% endfor %}

            {% for param in output_parameters %}
            var {{ param.name }}Param = command.Parameters.Add("@{{ param.name }}", SqlDbType.{{ param.sql_type }});
            {{ param.name }}Param.Direction = ParameterDirection.Output;
            {% endfor %}

            // Act
            await connection.OpenAsync();
            {% if returns_table %}
            var reader = await command.ExecuteReaderAsync();

            // Assert
            Assert.True(reader.HasRows);

            while (await reader.ReadAsync())
            {
                // Verify expected columns exist
                {% for column in expected_columns %}
                Assert.NotNull(reader["{{ column.name }}"]);
                {% endfor %}
            }
            {% else %}
            var rowsAffected = await command.ExecuteNonQueryAsync();

            // Assert
            {% if modifies_data.inserts %}
            Assert.True(rowsAffected > 0, "Expected rows to be inserted");
            {% elif modifies_data.updates %}
            Assert.True(rowsAffected > 0, "Expected rows to be updated");
            {% elif modifies_data.deletes %}
            Assert.True(rowsAffected > 0, "Expected rows to be deleted");
            {% endif %}

            {% for param in output_parameters %}
            Assert.NotNull({{ param.name }}Param.Value);
            {% endfor %}
            {% endif %}
        }

        {% if uses_transaction %}
        [Fact]
        public async Task {{ procedure_name }}_WithError_RollsBackTransaction()
        {
            // Arrange
            using var connection = _fixture.CreateConnection();
            using var command = new SqlCommand("{{ procedure_name }}", connection);
            command.CommandType = CommandType.StoredProcedure;

            // Add invalid parameters to trigger error
            {% for param in input_parameters %}
            command.Parameters.AddWithValue("@{{ param.name }}", {{ param.invalid_value }});
            {% endfor %}

            // Act & Assert
            await connection.OpenAsync();
            await Assert.ThrowsAsync<SqlException>(async () =>
            {
                await command.ExecuteNonQueryAsync();
            });

            // Verify rollback occurred (no data was modified)
            // TODO: Add verification query
        }
        {% endif %}
    }

    // Database fixture for integration testing
    public class DatabaseFixture : IDisposable
    {
        private readonly string _connectionString;

        public DatabaseFixture()
        {
            // Use test database
            _connectionString = "Server=(localdb)\\mssqllocaldb;Database=TestDb;Trusted_Connection=True;";
        }

        public SqlConnection CreateConnection()
        {
            return new SqlConnection(_connectionString);
        }

        public void Dispose()
        {
            // Cleanup test database
        }
    }
}
```

---

## Pattern Learning for Database Tests

### Database-Specific Error Patterns

```python
class DatabasePatternLearner:
    """Learns patterns from database test execution"""

    DB_ERROR_PATTERNS = {
        "constraint_violations": [
            r"Violation of PRIMARY KEY constraint",
            r"Violation of FOREIGN KEY constraint",
            r"Cannot insert duplicate key"
        ],
        "null_reference_errors": [
            r"Cannot insert the value NULL into column '(\w+)'",
            r"Column '(\w+)' cannot be null"
        ],
        "type_conversion_errors": [
            r"Error converting data type (\w+) to (\w+)",
            r"Conversion failed when converting"
        ],
        "transaction_errors": [
            r"Transaction was deadlocked",
            r"Lock request time out period exceeded"
        ]
    }

    def learn_from_db_tests(self, test_output: str) -> List[Dict[str, Any]]:
        """
        Learn patterns from database test failures

        Example patterns:
        1. "Cannot insert the value NULL into column 'Email'"
           → Email is required, update test data builder

        2. "Violation of FOREIGN KEY constraint 'FK_Payment_Customer'"
           → Need to create Customer record before Payment

        3. "Error converting data type varchar to int"
           → Parameter type mismatch, fix test value
        """
        patterns = []

        for error_type, regex_patterns in self.DB_ERROR_PATTERNS.items():
            for regex in regex_patterns:
                matches = re.findall(regex, test_output)
                for match in matches:
                    pattern = self._create_db_pattern(error_type, match)
                    patterns.append(pattern)

        return patterns
```

---

## Cost Estimation

**Per Repository Analysis** (GPT-4o-mini):
- Repository class: ~150 lines
- Analysis: ~400 tokens
- Test generation: ~1200 tokens
- **Total**: ~1600 tokens
- **Cost**: ~$0.0012 (0.12 cents)

**PaymentAPI Data Access Layer**:
- Estimated repositories: 8 classes
- Stored procedures: 10 procedures
- Total cost: (8 + 10) × $0.0012 = **$0.022** (2.2 cents)
- Pattern learning: ~$0.40
- **Total first run**: **$0.42**

---

## Implementation Roadmap

### Day 1-2: Repository Testing
- [ ] Implement `RepositoryAnalyzer`
- [ ] Create repository test template
- [ ] Test on PaymentDataAccess repository
- [ ] Generate InMemory database tests

### Day 3: Stored Procedure Testing
- [ ] Implement `SqlProcedureAnalyzer`
- [ ] Create procedure test template
- [ ] Extract procedures from PaymentAPI database
- [ ] Generate procedure integration tests

### Day 4: Pattern Learning + Integration
- [ ] Run generated tests
- [ ] Learn patterns from failures
- [ ] Regenerate with learned patterns
- [ ] Measure improvement

---

## Success Criteria

- ✅ Generate tests for 8+ repository classes
- ✅ Generate tests for 10+ stored procedures
- ✅ Total cost < $0.50
- ✅ 30-40% error reduction with pattern learning
- ✅ Tests validate data integrity and transactions

---

## Next Steps

1. Implement repository analyzer
2. Test on PaymentDataAccess layer
3. Generate database test suite
