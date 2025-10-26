"""
API Integration Test Handler

Generates end-to-end integration tests for API endpoints
Tests frontend (Vue.js/React) -> Backend (C#/VB.NET) -> Database (T-SQL)
"""

import re
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

from .base_language import (
    BaseLanguageHandler,
    ClassInfo,
    MethodInfo
)


class IntegrationTestHandler(BaseLanguageHandler):
    """
    API Integration test handler

    Supports:
    - Frontend-to-Backend integration (Vue.js/React → C#/VB.NET)
    - Backend-to-Database integration (C#/VB.NET → T-SQL)
    - Full-stack integration (Frontend → Backend → Database)
    - API contract testing
    - E2E workflows
    """

    def __init__(self, frontend_handler=None, backend_handler=None, database_handler=None):
        """
        Initialize integration test handler

        Args:
            frontend_handler: Vue.js or React handler
            backend_handler: C# or VB.NET handler
            database_handler: T-SQL handler
        """
        self.frontend_handler = frontend_handler
        self.backend_handler = backend_handler
        self.database_handler = database_handler

    def get_file_extensions(self) -> List[str]:
        """Return integration test file extensions"""
        return ['.integration.test.ts', '.e2e.test.ts']

    def get_test_file_extension(self) -> str:
        """Return test file extension"""
        return '.integration.test.ts'

    def get_test_framework_default(self) -> str:
        """Return default test framework"""
        return 'playwright'  # or 'cypress'

    def detect_files(self, project_dir: Path, pattern: Optional[str] = None) -> List[Path]:
        """
        Detect API endpoints for integration testing

        Args:
            project_dir: Project directory to search
            pattern: Optional regex pattern to filter

        Returns:
            List of API endpoint files
        """
        # This would typically analyze OpenAPI/Swagger specs or controller routes
        # For now, return empty as this is usually generated from existing components
        return []

    def parse_class(self, file_path: Path) -> Optional[ClassInfo]:
        """
        Parse integration test requirements

        For integration tests, this is typically called programmatically
        with frontend and backend ClassInfo objects

        Args:
            file_path: Not used for integration tests

        Returns:
            None - use generate_integration_test() instead
        """
        return None

    def generate_integration_test(
        self,
        frontend_info: Optional[ClassInfo],
        backend_info: ClassInfo,
        database_info: Optional[ClassInfo] = None
    ) -> str:
        """
        Generate integration test from frontend, backend, and optionally database components

        Args:
            frontend_info: Frontend component info (Vue.js/React)
            backend_info: Backend controller/service info (C#/VB.NET)
            database_info: Database stored procedure info (T-SQL)

        Returns:
            Generated integration test code
        """
        test_scenarios = self._identify_test_scenarios(frontend_info, backend_info, database_info)

        if frontend_info and backend_info:
            return self._generate_full_stack_test(frontend_info, backend_info, database_info, test_scenarios)
        elif backend_info and database_info:
            return self._generate_backend_database_test(backend_info, database_info, test_scenarios)
        else:
            return self._generate_api_contract_test(backend_info, test_scenarios)

    def _identify_test_scenarios(
        self,
        frontend_info: Optional[ClassInfo],
        backend_info: ClassInfo,
        database_info: Optional[ClassInfo]
    ) -> List[Dict[str, Any]]:
        """Identify integration test scenarios based on components"""
        scenarios = []

        # Extract API endpoints from backend
        if backend_info:
            for method in backend_info.methods:
                scenario = {
                    'name': method.name,
                    'endpoint': self._infer_endpoint(backend_info.name, method.name),
                    'http_method': self._infer_http_method(method.name),
                    'parameters': method.parameters,
                    'return_type': method.return_type,
                    'is_async': method.is_async
                }
                scenarios.append(scenario)

        return scenarios

    def _infer_endpoint(self, controller_name: str, method_name: str) -> str:
        """Infer API endpoint from controller and method name"""
        # Remove "Controller" suffix
        base = controller_name.replace('Controller', '').lower()

        # Convert method name to route
        # GetUser -> /user
        # GetUsers -> /users
        # CreateUser -> /user
        route = method_name.lower()
        for prefix in ['get', 'post', 'put', 'delete', 'patch']:
            if route.startswith(prefix):
                route = route[len(prefix):]
                break

        return f"/api/{base}/{route}" if route else f"/api/{base}"

    def _infer_http_method(self, method_name: str) -> str:
        """Infer HTTP method from method name"""
        name_lower = method_name.lower()

        if name_lower.startswith('get'):
            return 'GET'
        elif name_lower.startswith('create') or name_lower.startswith('add') or name_lower.startswith('post'):
            return 'POST'
        elif name_lower.startswith('update') or name_lower.startswith('put'):
            return 'PUT'
        elif name_lower.startswith('delete') or name_lower.startswith('remove'):
            return 'DELETE'
        elif name_lower.startswith('patch'):
            return 'PATCH'
        else:
            return 'GET'

    def _generate_full_stack_test(
        self,
        frontend_info: ClassInfo,
        backend_info: ClassInfo,
        database_info: Optional[ClassInfo],
        scenarios: List[Dict[str, Any]]
    ) -> str:
        """Generate full-stack integration test (Frontend -> Backend -> Database)"""
        frontend_type = frontend_info.language  # 'vuejs' or 'react'

        test_code = f"""/**
 * Full-Stack Integration Tests
 * Frontend: {frontend_info.name} ({frontend_type})
 * Backend: {backend_info.name} ({backend_info.language})
 * Database: {database_info.name if database_info else 'N/A'}
 */

import {{ test, expect }} from '@playwright/test'

const API_BASE_URL = process.env.API_URL || 'http://localhost:5000'

test.describe('{frontend_info.name} -> {backend_info.name} Integration', () => {{
  test.beforeEach(async ({{ page }}) => {{
    // Setup: Navigate to component
    await page.goto('http://localhost:3000')

    // Setup: Mock authentication if needed
    await page.evaluate(() => {{
      localStorage.setItem('auth_token', 'test-token')
    }})
  }})

"""

        # Generate test for each scenario
        for scenario in scenarios[:5]:  # Limit to 5 scenarios
            test_code += self._generate_scenario_test(
                frontend_info,
                backend_info,
                scenario,
                frontend_type
            )

        test_code += """})

// API Contract Tests (without UI)
test.describe('API Contract Tests', () => {
"""

        for scenario in scenarios[:5]:
            test_code += self._generate_api_contract_test_case(backend_info, scenario)

        test_code += """})
"""

        return test_code

    def _generate_scenario_test(
        self,
        frontend_info: ClassInfo,
        backend_info: ClassInfo,
        scenario: Dict[str, Any],
        frontend_type: str
    ) -> str:
        """Generate single integration test scenario"""
        method_name = scenario['name']
        endpoint = scenario['endpoint']
        http_method = scenario['http_method']

        test_name = f"should {method_name} via UI and verify backend response"

        test_code = f"""  test('{test_name}', async ({{ page }}) => {{
    // Intercept API call
    await page.route(`${{API_BASE_URL}}{endpoint}*`, async (route) => {{
      const response = await route.fetch()
      const json = await response.json()

      // Verify API response structure
      expect(response.status()).toBe(200)
      expect(json).toHaveProperty('data')

      route.fulfill({{ response }})
    }})

    // User interaction on frontend
"""

        if http_method == 'GET':
            test_code += f"""    // Click button or link that triggers GET request
    await page.click('[data-testid="load-button"]')

    // Wait for API call to complete
    await page.waitForResponse((response) =>
      response.url().includes('{endpoint}') && response.status() === 200
    )

    // Verify UI updates with data
    await expect(page.locator('[data-testid="result"]')).toBeVisible()
"""
        elif http_method == 'POST':
            test_code += f"""    // Fill form
    await page.fill('[name="name"]', 'Test User')
    await page.fill('[name="email"]', 'test@example.com')

    // Submit form
    await page.click('[type="submit"]')

    // Wait for API call to complete
    await page.waitForResponse((response) =>
      response.url().includes('{endpoint}') && response.status() === 201
    )

    // Verify success message
    await expect(page.locator('.success-message')).toContainText('Created successfully')
"""

        test_code += "  })\n\n"
        return test_code

    def _generate_api_contract_test_case(
        self,
        backend_info: ClassInfo,
        scenario: Dict[str, Any]
    ) -> str:
        """Generate API contract test case"""
        method_name = scenario['name']
        endpoint = scenario['endpoint']
        http_method = scenario['http_method']

        test_code = f"""  test('{http_method} {endpoint} - {method_name}', async ({{ request }}) => {{
    const response = await request.{http_method.lower()}(`${{API_BASE_URL}}{endpoint}`, {{
"""

        if http_method in ['POST', 'PUT', 'PATCH']:
            test_code += """      data: {
        // Request payload
        name: 'Test',
        value: 123
      },
"""

        test_code += """      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer test-token'
      }
    })

    // Verify response
    expect(response.ok()).toBeTruthy()
"""

        if http_method == 'GET':
            test_code += """    const data = await response.json()
    expect(data).toBeDefined()
    expect(Array.isArray(data) || typeof data === 'object').toBeTruthy()
"""
        elif http_method == 'POST':
            test_code += """    expect(response.status()).toBe(201)
    const data = await response.json()
    expect(data).toHaveProperty('id')
"""
        elif http_method == 'DELETE':
            test_code += """    expect(response.status()).toBe(204)
"""

        test_code += "  })\n\n"
        return test_code

    def _generate_backend_database_test(
        self,
        backend_info: ClassInfo,
        database_info: ClassInfo,
        scenarios: List[Dict[str, Any]]
    ) -> str:
        """Generate backend-to-database integration test"""
        test_code = f"""/**
 * Backend-Database Integration Tests
 * Backend: {backend_info.name} ({backend_info.language})
 * Database: {database_info.name}
 */

using Xunit;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Data.SqlClient;

namespace {backend_info.namespace}.IntegrationTests
{{
    public class {backend_info.name}IntegrationTests : IClassFixture<WebApplicationFactory<Program>>
    {{
        private readonly WebApplicationFactory<Program> _factory;
        private readonly string _connectionString;

        public {backend_info.name}IntegrationTests(WebApplicationFactory<Program> factory)
        {{
            _factory = factory;
            _connectionString = "Server=localhost;Database=TestDB;...";
        }}

        [Fact]
        public async Task {backend_info.methods[0].name if backend_info.methods else 'Method'}_ShouldInteractWithDatabase()
        {{
            // Arrange: Setup test data in database
            await SeedTestData();

            // Act: Call API endpoint
            var client = _factory.CreateClient();
            var response = await client.GetAsync("/api/test");

            // Assert: Verify API response
            response.EnsureSuccessStatusCode();

            // Assert: Verify database state
            await VerifyDatabaseState();
        }}

        private async Task SeedTestData()
        {{
            using var connection = new SqlConnection(_connectionString);
            await connection.OpenAsync();

            using var command = connection.CreateCommand();
            command.CommandText = @"
                INSERT INTO TestTable (Name, Value)
                VALUES (@Name, @Value)";

            command.Parameters.AddWithValue("@Name", "Test");
            command.Parameters.AddWithValue("@Value", 123);

            await command.ExecuteNonQueryAsync();
        }}

        private async Task VerifyDatabaseState()
        {{
            using var connection = new SqlConnection(_connectionString);
            await connection.OpenAsync();

            using var command = connection.CreateCommand();
            command.CommandText = "SELECT COUNT(*) FROM TestTable";

            var count = (int)await command.ExecuteScalarAsync();
            Assert.True(count > 0);
        }}
    }}
}}
"""

        return test_code

    def _generate_api_contract_test(
        self,
        backend_info: ClassInfo,
        scenarios: List[Dict[str, Any]]
    ) -> str:
        """Generate API contract-only test"""
        test_code = f"""/**
 * API Contract Tests
 * Backend: {backend_info.name}
 */

import {{ test, expect }} from '@playwright/test'

const API_BASE_URL = process.env.API_URL || 'http://localhost:5000'

test.describe('{backend_info.name} API Contract', () => {{
"""

        for scenario in scenarios:
            test_code += self._generate_api_contract_test_case(backend_info, scenario)

        test_code += """})
"""

        return test_code

    def generate_test_prompt(
        self,
        class_info: ClassInfo,
        patterns: Dict[str, Any],
        test_framework: str = 'playwright',
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate prompt for integration test

        This is typically not used - integration tests are generated
        programmatically using generate_integration_test()
        """
        return ""

    def auto_fix_syntax(self, test_code: str, class_info: ClassInfo) -> str:
        """Auto-fix integration test syntax"""
        return test_code

    def get_test_class_name(self, class_name: str) -> str:
        """Generate test file name"""
        return f"{class_name}.integration.test"

    def get_test_namespace(self, namespace: str) -> str:
        """Return test directory"""
        return f"{namespace}/integration"
