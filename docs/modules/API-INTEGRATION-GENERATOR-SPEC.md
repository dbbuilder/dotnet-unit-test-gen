# API Integration Test Generator Module Specification

**Date**: 2025-10-25
**Status**: Planning Phase
**Target**: REST API endpoint validation
**Priority**: Phase 2 (High - needed for PaymentAPI and ecommerce-app integration)

---

## Executive Summary

The API Integration Test Generator creates comprehensive integration tests for REST APIs, validating end-to-end request/response flows, authentication, error handling, and data consistency. It supports both backend API implementation testing and frontend-backend integration validation.

**Primary Use Cases**:
1. **PaymentAPI Endpoint Testing** - Validate VB.NET Web API endpoints
2. **ecommerce-app Integration Testing** - Validate frontend API calls against backend
3. **Contract Testing** - Ensure API contracts match between frontend and backend

**Technology Stack**:
- **Backend Testing**: xUnit with WebApplicationFactory (for .NET APIs)
- **Integration Testing**: Axios + Jest (for JavaScript API calls)
- **Contract Validation**: JSON Schema validation

---

## Architecture Design

### Module Structure

```
dotnet-unit-test-gen/
├── generators/
│   └── api_integration_generator.py    # NEW - API test generator
├── analyzers/
│   └── api_analyzer.py                  # NEW - API endpoint analyzer
├── templates/
│   └── api/
│       ├── dotnet_api_integration.jinja2    # .NET API tests
│       ├── javascript_api_client.jinja2     # JS API client tests
│       └── contract_validation.jinja2       # Contract tests
└── validators/
    └── api_contract_validator.py       # NEW - Contract validation
```

---

## API Endpoint Analysis Strategy

### Backend API Discovery (.NET/VB.NET)

```python
class ApiAnalyzer(BaseAnalyzer):
    """Analyzes API controllers to extract endpoint information"""

    def analyze_dotnet_controller(self, file_path: str) -> Dict[str, Any]:
        """
        Extract API endpoints from .NET Web API controllers:
        - Route attributes
        - HTTP method attributes (HttpGet, HttpPost, etc.)
        - Parameter bindings (FromBody, FromQuery, FromRoute)
        - Return types
        - Authorization requirements
        """
        content = Path(file_path).read_text()

        return {
            "controller_name": self._extract_controller_name(file_path),
            "base_route": self._extract_route_prefix(content),
            "endpoints": self._extract_endpoints(content),
            "authentication": self._extract_auth_requirements(content)
        }

    def _extract_endpoints(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract endpoint definitions from controller

        Example VB.NET pattern:
        <HttpPost>
        <Route("send-customer-receipt")>
        Public Function SendCustomerReceiptNotification(<FromBody()> ByVal req As JObject)
        """
        endpoints = []

        # Find all HTTP method attributes
        http_methods = {
            "HttpGet": "GET",
            "HttpPost": "POST",
            "HttpPut": "PUT",
            "HttpDelete": "DELETE",
            "HttpPatch": "PATCH"
        }

        # VB.NET pattern matching
        function_pattern = r'<(Http\w+)>\s*<Route\("([^"]+)"\)>\s*Public Function (\w+)\(([^)]*)\)'

        for match in re.finditer(function_pattern, content, re.MULTILINE):
            http_attr, route, function_name, parameters = match.groups()

            endpoints.append({
                "method": http_methods.get(http_attr, "GET"),
                "route": route,
                "function_name": function_name,
                "parameters": self._parse_parameters(parameters),
                "request_body": self._extract_request_body(parameters),
                "response_type": self._extract_response_type(content, function_name),
                "requires_auth": self._check_authorization(content, function_name)
            })

        return endpoints

    def _parse_parameters(self, param_string: str) -> List[Dict[str, Any]]:
        """
        Parse parameter definitions:
        - <FromBody()> ByVal req As JObject
        - <FromQuery()> ByVal id As Integer
        - <FromRoute()> ByVal name As String
        """
        params = []

        # Pattern: <FromBody()> ByVal req As JObject
        param_pattern = r'<From(\w+)\(\)>\s*ByVal\s+(\w+)\s+As\s+(\w+)'

        for match in re.finditer(param_pattern, param_string):
            binding, name, param_type = match.groups()
            params.append({
                "name": name,
                "type": param_type,
                "binding": binding.lower(),  # body, query, route
                "required": True
            })

        return params

    def _extract_request_body(self, parameters: str) -> Optional[Dict[str, Any]]:
        """
        Extract request body schema from <FromBody> parameter

        For JObject types, we'll need to analyze the function body
        to see what properties are accessed
        """
        if "FromBody" not in parameters:
            return None

        # Example: Extract from function body
        # Dim customerEmail As String = If(req("customerEmail")?.ToString(), "")
        # → Property: customerEmail, Type: string

        return {
            "type": "JObject",  # Will be refined in pattern learning
            "schema": {}  # Will be populated from function body analysis
        }
```

### Frontend API Analysis (JavaScript/TypeScript)

```python
class FrontendApiAnalyzer:
    """Analyzes frontend API service files"""

    def analyze_api_service(self, file_path: str) -> Dict[str, Any]:
        """
        Extract API calls from frontend service files:
        - axios.get/post/put/delete calls
        - Request payload structures
        - Response handling
        - Error handling
        """
        content = Path(file_path).read_text()

        return {
            "service_name": self._extract_service_name(file_path),
            "base_url": self._extract_base_url(content),
            "api_calls": self._extract_api_calls(content)
        }

    def _extract_api_calls(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract API call patterns:

        Example from ecommerceApi.js:
        async sendCustomerReceiptNotification(receiptRequest) {
          const response = await ECommerceAPI.post('send-customer-receipt', receiptRequest);
          return response.data;
        }
        """
        calls = []

        # Pattern: async methodName(params) { ... ECommerceAPI.post(...) }
        method_pattern = r'async\s+(\w+)\(([^)]*)\)\s*{([^}]+)}'

        for match in re.finditer(method_pattern, content, re.DOTALL):
            method_name, params, body = match.groups()

            # Find axios/API calls within method body
            api_call_pattern = r'(?:await\s+)?(?:\w+\.)?(\w+)\([\'"]([^\'"]+)[\'"](?:,\s*(\w+))?\)'
            api_match = re.search(api_call_pattern, body)

            if api_match:
                http_method, endpoint, payload_var = api_match.groups()

                calls.append({
                    "method_name": method_name,
                    "http_method": http_method.upper(),
                    "endpoint": endpoint,
                    "request_payload": payload_var or params,
                    "response_handling": "response.data" in body
                })

        return calls
```

---

## Test Generation Templates

### .NET API Integration Test Template

```csharp
// templates/api/dotnet_api_integration.jinja2
using System.Net;
using System.Net.Http;
using System.Text;
using Microsoft.AspNetCore.Mvc.Testing;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Xunit;

namespace {{ namespace }}.Tests.Integration
{
    public class {{ controller_name }}IntegrationTests : IClassFixture<WebApplicationFactory<Program>>
    {
        private readonly WebApplicationFactory<Program> _factory;
        private readonly HttpClient _client;

        public {{ controller_name }}IntegrationTests(WebApplicationFactory<Program> factory)
        {
            _factory = factory;
            _client = _factory.CreateClient();
        }

        {% for endpoint in endpoints %}
        [Fact]
        public async Task {{ endpoint.function_name }}_WithValidRequest_ReturnsSuccess()
        {
            // Arrange
            {% if endpoint.request_body %}
            var requestBody = new JObject
            {
                {% for prop in endpoint.request_body.properties %}
                ["{{ prop.name }}"] = {{ prop.test_value | tojson }},
                {% endfor %}
            };
            var content = new StringContent(
                JsonConvert.SerializeObject(requestBody),
                Encoding.UTF8,
                "application/json"
            );
            {% endif %}

            // Act
            var response = await _client.{{ endpoint.method }}Async(
                "/api/{{ base_route }}/{{ endpoint.route }}"
                {% if endpoint.request_body %}, content{% endif %}
            );

            // Assert
            Assert.Equal(HttpStatusCode.OK, response.StatusCode);

            var responseBody = await response.Content.ReadAsStringAsync();
            var jsonResponse = JObject.Parse(responseBody);

            Assert.True(jsonResponse["Successful"]?.Value<bool>() ?? false);
            {% for expected_field in endpoint.response_fields %}
            Assert.NotNull(jsonResponse["{{ expected_field }}"]);
            {% endfor %}
        }

        [Fact]
        public async Task {{ endpoint.function_name }}_WithInvalidRequest_ReturnsBadRequest()
        {
            // Arrange
            var requestBody = new JObject
            {
                // Missing required fields
            };
            var content = new StringContent(
                JsonConvert.SerializeObject(requestBody),
                Encoding.UTF8,
                "application/json"
            );

            // Act
            var response = await _client.{{ endpoint.method }}Async(
                "/api/{{ base_route }}/{{ endpoint.route }}",
                content
            );

            // Assert
            Assert.True(
                response.StatusCode == HttpStatusCode.BadRequest ||
                response.StatusCode == HttpStatusCode.InternalServerError
            );

            var responseBody = await response.Content.ReadAsStringAsync();
            var jsonResponse = JObject.Parse(responseBody);

            Assert.False(jsonResponse["Successful"]?.Value<bool>() ?? true);
            Assert.NotNull(jsonResponse["Message"]);
        }

        {% if endpoint.requires_auth %}
        [Fact]
        public async Task {{ endpoint.function_name }}_WithoutAuthentication_ReturnsUnauthorized()
        {
            // Arrange
            var client = _factory.CreateClient();
            // Don't set authentication headers

            {% if endpoint.request_body %}
            var requestBody = new JObject();
            var content = new StringContent(
                JsonConvert.SerializeObject(requestBody),
                Encoding.UTF8,
                "application/json"
            );
            {% endif %}

            // Act
            var response = await client.{{ endpoint.method }}Async(
                "/api/{{ base_route }}/{{ endpoint.route }}"
                {% if endpoint.request_body %}, content{% endif %}
            );

            // Assert
            Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
        }
        {% endif %}
        {% endfor %}
    }
}
```

### JavaScript API Client Test Template

```javascript
// templates/api/javascript_api_client.jinja2
import axios from 'axios';
import MockAdapter from 'axios-mock-adapter';
import { {{ service_name }} } from '@/services/{{ service_file }}';

describe('{{ service_name }} Integration Tests', () => {
  let mock;

  beforeEach(() => {
    mock = new MockAdapter(axios);
  });

  afterEach(() => {
    mock.restore();
  });

  {% for api_call in api_calls %}
  describe('{{ api_call.method_name }}', () => {
    it('should call {{ api_call.endpoint }} with correct payload', async () => {
      // Arrange
      const requestPayload = {
        {% for field in api_call.expected_fields %}
        {{ field.name }}: {{ field.test_value | tojson }},
        {% endfor %}
      };

      const expectedResponse = {
        Successful: true,
        {% for field in api_call.response_fields %}
        {{ field.name }}: {{ field.test_value | tojson }},
        {% endfor %}
      };

      mock.on{{ api_call.http_method.lower() }}('{{ base_url }}/{{ api_call.endpoint }}')
        .reply(200, expectedResponse);

      // Act
      const result = await {{ service_name }}.{{ api_call.method_name }}(requestPayload);

      // Assert
      expect(result.Successful).toBe(true);
      {% for field in api_call.response_fields %}
      expect(result.{{ field.name }}).toBeDefined();
      {% endfor %}
    });

    it('should handle {{ api_call.endpoint }} errors gracefully', async () => {
      // Arrange
      const requestPayload = {
        {% for field in api_call.expected_fields %}
        {{ field.name }}: {{ field.test_value | tojson }},
        {% endfor %}
      };

      const errorResponse = {
        Successful: false,
        Message: 'Test error message'
      };

      mock.on{{ api_call.http_method.lower() }}('{{ base_url }}/{{ api_call.endpoint }}')
        .reply(400, errorResponse);

      // Act
      const result = await {{ service_name }}.{{ api_call.method_name }}(requestPayload);

      // Assert
      expect(result.Successful).toBe(false);
      expect(result.Message).toBeDefined();
    });

    it('should handle {{ api_call.endpoint }} network errors', async () => {
      // Arrange
      const requestPayload = {
        {% for field in api_call.expected_fields %}
        {{ field.name }}: {{ field.test_value | tojson }},
        {% endfor %}
      };

      mock.on{{ api_call.http_method.lower() }}('{{ base_url }}/{{ api_call.endpoint }}')
        .networkError();

      // Act & Assert
      await expect(
        {{ service_name }}.{{ api_call.method_name }}(requestPayload)
      ).rejects.toThrow();
    });
  });
  {% endfor %}
});
```

---

## Contract Validation

### API Contract Validator

```python
class ApiContractValidator:
    """Validates API contracts between frontend and backend"""

    def validate_contracts(
        self,
        frontend_analysis: Dict[str, Any],
        backend_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Compare frontend API calls with backend endpoint definitions
        to find mismatches in:
        - Request payload structures
        - Response structures
        - HTTP methods
        - Route paths
        - Data types
        """
        mismatches = []

        for api_call in frontend_analysis["api_calls"]:
            matching_endpoint = self._find_matching_endpoint(
                api_call,
                backend_analysis["endpoints"]
            )

            if not matching_endpoint:
                mismatches.append({
                    "type": "missing_endpoint",
                    "frontend_call": api_call["method_name"],
                    "endpoint": api_call["endpoint"],
                    "severity": "high"
                })
                continue

            # Validate HTTP method
            if api_call["http_method"] != matching_endpoint["method"]:
                mismatches.append({
                    "type": "http_method_mismatch",
                    "endpoint": api_call["endpoint"],
                    "frontend_method": api_call["http_method"],
                    "backend_method": matching_endpoint["method"],
                    "severity": "critical"
                })

            # Validate request payload structure
            payload_issues = self._validate_request_payload(
                api_call,
                matching_endpoint
            )
            mismatches.extend(payload_issues)

            # Validate response structure
            response_issues = self._validate_response_structure(
                api_call,
                matching_endpoint
            )
            mismatches.extend(response_issues)

        return mismatches

    def _validate_request_payload(
        self,
        api_call: Dict[str, Any],
        endpoint: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Validate that frontend request payload matches backend expectations

        Example issue from ecommerce-app analysis:
        - Frontend sends pickupLocationId as Integer
        - Backend expects String
        """
        issues = []

        if not endpoint.get("request_body"):
            return issues

        # Compare field types
        for field in endpoint["request_body"]["properties"]:
            frontend_type = self._infer_frontend_type(api_call, field["name"])
            backend_type = field["type"]

            if frontend_type != backend_type:
                issues.append({
                    "type": "type_mismatch",
                    "endpoint": endpoint["route"],
                    "field": field["name"],
                    "frontend_type": frontend_type,
                    "backend_type": backend_type,
                    "severity": "medium"
                })

        return issues
```

---

## Pattern Learning for API Tests

### API-Specific Error Patterns

```python
class ApiPatternLearner:
    """Learns patterns from API test execution"""

    API_ERROR_PATTERNS = {
        "serialization_errors": [
            r"Cannot deserialize the current JSON object",
            r"Error converting value"
        ],
        "validation_errors": [
            r"One or more validation errors occurred",
            r"The field (\w+) is required"
        ],
        "authentication_errors": [
            r"Authorization has been denied",
            r"No authentication token provided"
        ],
        "network_errors": [
            r"No connection could be made",
            r"The remote server returned an error: \((\d+)\)"
        ]
    }

    def learn_from_integration_tests(
        self,
        test_output: str
    ) -> List[Dict[str, Any]]:
        """
        Learn patterns from integration test failures

        Example learned patterns:
        1. "Cannot deserialize JObject to String"
           → Frontend should send string, not object

        2. "The field customerEmail is required"
           → Add customerEmail to required fields in test template

        3. "Authorization has been denied for user"
           → Endpoint requires authentication, add [Authorize] check
        """
        patterns = []

        for error_type, regex_patterns in self.API_ERROR_PATTERNS.items():
            for regex in regex_patterns:
                matches = re.findall(regex, test_output)
                for match in matches:
                    pattern = self._create_api_pattern(error_type, match)
                    patterns.append(pattern)

        return patterns
```

---

## Cost Estimation

### Token Usage Breakdown (GPT-4o-mini)

**Per API Endpoint Analysis**:
- Controller source: ~200 lines average
- Endpoint extraction: ~300 tokens
- Test template rendering: ~800 tokens
- **Total per endpoint**: ~1100 tokens
- **Cost per endpoint**: ~$0.0008 (0.08 cents)

**ecommerce-app + PaymentAPI Integration**:
- PaymentAPI endpoints: 15 endpoints
- Frontend API calls: 20 methods
- Contract validation: 1-time cost
- Total cost: (15 + 20) × $0.0008 = **$0.028** (2.8 cents)
- Pattern learning: ~$0.30
- **Total first run**: **$0.33**

---

## Implementation Roadmap

### Day 1: Backend API Analysis
- [ ] Implement `ApiAnalyzer` for .NET controllers
- [ ] Extract endpoints from EcommerceController.vb
- [ ] Generate integration test template
- [ ] Test on 1 PaymentAPI endpoint

**Deliverable**: .NET API integration test generation working

### Day 2: Frontend API Analysis + Contract Validation
- [ ] Implement `FrontendApiAnalyzer` for JavaScript
- [ ] Extract API calls from ecommerceApi.js
- [ ] Implement `ApiContractValidator`
- [ ] Generate contract mismatch report
- [ ] Fix identified type inconsistencies

**Deliverable**: Contract validation detecting type mismatches

### Day 3: Integration + Pattern Learning
- [ ] Generate full integration test suite
- [ ] Run tests against PaymentAPI
- [ ] Learn patterns from failures
- [ ] Regenerate with learned patterns
- [ ] Measure error reduction

**Deliverable**: Complete API integration test suite

---

## Success Criteria

- ✅ Generate integration tests for 15+ API endpoints
- ✅ Total cost < $0.50 for first run
- ✅ Detect 100% of type mismatches (like pickupLocationId)
- ✅ 80%+ test pass rate after pattern learning
- ✅ Tests validate request/response contracts

---

## Next Steps

1. Implement `ApiAnalyzer` class
2. Test on EcommerceController.vb endpoints
3. Generate contract validation report for ecommerce-app
4. Create integration tests for PaymentAPI
