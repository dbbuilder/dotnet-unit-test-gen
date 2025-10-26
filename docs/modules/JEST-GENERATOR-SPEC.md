# Jest Test Generator Module Specification

**Date**: 2025-10-25
**Status**: Planning Phase
**Target Languages**: JavaScript, TypeScript, Vue.js, React
**Priority**: Phase 1 (Highest - needed for ecommerce-app)

---

## Executive Summary

The Jest Test Generator extends the proven pattern-learning architecture to JavaScript/TypeScript ecosystems. It will generate comprehensive unit tests for Vue.js components, React components, and Node.js services using the Jest testing framework.

**Key Success Metrics from .NET Generator**:
- 44 test files in ~5 minutes
- $2.23 total cost
- 30-40% error reduction with pattern learning
- 15 patterns automatically discovered

**Jest Generator Goals**:
- Generate tests for Vue 2/3 components
- Support TypeScript and JSX/TSX syntax
- Handle Vuex store testing
- Mock Vue Router and component dependencies
- Achieve similar 30-40% error reduction rate

---

## Architecture Design

### Module Structure

```
dotnet-unit-test-gen/
├── generators/
│   ├── base_generator.py           # Abstract base class
│   ├── dotnet_generator.py         # Existing .NET generator
│   └── jest_generator.py           # NEW - Jest generator
├── analyzers/
│   ├── base_analyzer.py            # Abstract base class
│   ├── dotnet_analyzer.py          # Existing .NET analyzer
│   └── javascript_analyzer.py      # NEW - JS/TS/Vue analyzer
├── templates/
│   ├── dotnet/                     # Existing .NET templates
│   └── jest/                       # NEW - Jest templates
│       ├── vue_component.jinja2
│       ├── react_component.jinja2
│       ├── vuex_store.jinja2
│       ├── service_class.jinja2
│       └── utility_function.jinja2
└── pattern_learners/
    ├── langchain_pattern_learner.py   # Existing pattern learner
    └── jest_pattern_learner.py        # NEW - Jest-specific patterns
```

### Base Generator Interface

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseTestGenerator(ABC):
    """Abstract base class for all test generators"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.pattern_cache = self._load_patterns()
        self.llm_client = self._initialize_llm()

    @abstractmethod
    def analyze_source(self, file_path: str) -> Dict[str, Any]:
        """Analyze source code to extract testable elements"""
        pass

    @abstractmethod
    def generate_tests(self, analysis: Dict[str, Any]) -> str:
        """Generate test code from analysis results"""
        pass

    @abstractmethod
    def learn_patterns(self, error_log: str) -> List[Dict[str, Any]]:
        """Learn patterns from test execution errors"""
        pass

    def _load_patterns(self) -> Dict[str, Any]:
        """Load cached patterns from .test-gen-cache/"""
        cache_path = Path(".test-gen-cache") / f"{self.generator_type}_patterns.json"
        if cache_path.exists():
            return json.loads(cache_path.read_text())
        return {}

    def _save_patterns(self, patterns: Dict[str, Any]):
        """Save learned patterns to cache"""
        cache_path = Path(".test-gen-cache") / f"{self.generator_type}_patterns.json"
        cache_path.parent.mkdir(exist_ok=True)
        cache_path.write_text(json.dumps(patterns, indent=2))
```

---

## JavaScript/TypeScript Analyzer

### Component Analysis Strategy

```python
class JavaScriptAnalyzer(BaseAnalyzer):
    """Analyzes JavaScript/TypeScript files for test generation"""

    def analyze_vue_component(self, file_path: str) -> Dict[str, Any]:
        """
        Extracts testable elements from Vue SFC:
        - Component name
        - Props definitions
        - Data properties
        - Computed properties
        - Methods
        - Lifecycle hooks
        - Vuex store dependencies
        - Vue Router dependencies
        """
        content = Path(file_path).read_text()

        return {
            "type": "vue_component",
            "name": self._extract_component_name(content),
            "props": self._extract_props(content),
            "data": self._extract_data_properties(content),
            "computed": self._extract_computed_properties(content),
            "methods": self._extract_methods(content),
            "lifecycle_hooks": self._extract_lifecycle_hooks(content),
            "imports": self._extract_imports(content),
            "store_dependencies": self._extract_store_usage(content),
            "router_dependencies": self._extract_router_usage(content),
            "template": self._extract_template(content)
        }

    def _extract_component_name(self, content: str) -> str:
        """Extract component name from export default or name property"""
        # Pattern 1: export default { name: 'ComponentName' }
        name_match = re.search(r"name:\s*['\"](\w+)['\"]", content)
        if name_match:
            return name_match.group(1)

        # Pattern 2: Infer from filename
        # Will be provided by caller
        return "UnknownComponent"

    def _extract_props(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract props definitions:
        - Simple array: props: ['prop1', 'prop2']
        - Object with types: props: { prop1: String, prop2: Number }
        - Object with validation: props: { prop1: { type: String, required: true } }
        """
        props = []

        # Match props: { ... } block
        props_match = re.search(r"props:\s*{([^}]+)}", content, re.MULTILINE | re.DOTALL)
        if props_match:
            props_content = props_match.group(1)
            # Parse each prop definition
            # This will use AST parsing in actual implementation
            props.append({
                "name": "example_prop",
                "type": "String",
                "required": True,
                "default": None
            })

        return props

    def _extract_methods(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract methods from methods: { ... } block
        Returns list of method signatures with parameter info
        """
        methods = []

        # Match methods: { ... } block
        methods_match = re.search(r"methods:\s*{([^}]+)}", content, re.MULTILINE | re.DOTALL)
        if methods_match:
            methods_content = methods_match.group(1)
            # Extract individual method signatures
            # Example: async submitForm(formData) { ... }
            method_pattern = r"(async\s+)?(\w+)\s*\(([^)]*)\)\s*{"
            for match in re.finditer(method_pattern, methods_content):
                methods.append({
                    "name": match.group(2),
                    "is_async": bool(match.group(1)),
                    "parameters": [p.strip() for p in match.group(3).split(",") if p.strip()],
                    "calls_store": "this.$store" in methods_content,
                    "calls_router": "this.$router" in methods_content
                })

        return methods

    def _extract_store_usage(self, content: str) -> Dict[str, Any]:
        """
        Identify Vuex store dependencies:
        - mapState usage
        - mapGetters usage
        - mapActions usage
        - mapMutations usage
        - Direct this.$store.dispatch calls
        """
        return {
            "uses_store": "this.$store" in content or "mapState" in content,
            "state_mappings": self._find_map_helpers(content, "mapState"),
            "getter_mappings": self._find_map_helpers(content, "mapGetters"),
            "action_mappings": self._find_map_helpers(content, "mapActions"),
            "mutation_mappings": self._find_map_helpers(content, "mapMutations")
        }
```

---

## Jest Test Templates

### Vue Component Template

```javascript
// templates/jest/vue_component.jinja2
import { shallowMount, createLocalVue } from '@vue/test-utils';
import Vuex from 'vuex';
{% if component.router_dependencies %}
import VueRouter from 'vue-router';
{% endif %}
import {{ component.name }} from '@/{{ component.path }}';

const localVue = createLocalVue();
localVue.use(Vuex);
{% if component.router_dependencies %}
localVue.use(VueRouter);
{% endif %}

describe('{{ component.name }}', () => {
  let wrapper;
  {% if component.store_dependencies.uses_store %}
  let store;
  let actions;
  let getters;
  let state;
  {% endif %}
  {% if component.router_dependencies %}
  let router;
  {% endif %}

  beforeEach(() => {
    {% if component.store_dependencies.uses_store %}
    // Mock Vuex store
    state = {
      {% for state_item in component.store_dependencies.state_mappings %}
      {{ state_item }}: null,
      {% endfor %}
    };

    getters = {
      {% for getter in component.store_dependencies.getter_mappings %}
      {{ getter }}: jest.fn(() => null),
      {% endfor %}
    };

    actions = {
      {% for action in component.store_dependencies.action_mappings %}
      {{ action }}: jest.fn(),
      {% endfor %}
    };

    store = new Vuex.Store({
      state,
      getters,
      actions
    });
    {% endif %}

    {% if component.router_dependencies %}
    // Mock Vue Router
    router = new VueRouter({
      routes: [
        { path: '/', name: 'home', component: { template: '<div>Home</div>' } }
      ]
    });
    {% endif %}

    // Create wrapper
    wrapper = shallowMount({{ component.name }}, {
      localVue,
      {% if component.store_dependencies.uses_store %}
      store,
      {% endif %}
      {% if component.router_dependencies %}
      router,
      {% endif %}
      propsData: {
        {% for prop in component.props %}
        {{ prop.name }}: {{ prop.default | tojson }},
        {% endfor %}
      }
    });
  });

  afterEach(() => {
    wrapper.destroy();
  });

  describe('Component Mounting', () => {
    it('should render successfully', () => {
      expect(wrapper.exists()).toBe(true);
    });

    it('should have correct component name', () => {
      expect(wrapper.vm.$options.name).toBe('{{ component.name }}');
    });
  });

  {% if component.props %}
  describe('Props Validation', () => {
    {% for prop in component.props %}
    it('should accept {{ prop.name }} prop', () => {
      const testValue = {{ prop.test_value | tojson }};
      wrapper.setProps({ {{ prop.name }}: testValue });
      expect(wrapper.props().{{ prop.name }}).toBe(testValue);
    });
    {% endfor %}
  });
  {% endif %}

  {% if component.data %}
  describe('Data Properties', () => {
    {% for data_prop in component.data %}
    it('should initialize {{ data_prop.name }} correctly', () => {
      expect(wrapper.vm.{{ data_prop.name }}).toBeDefined();
    });
    {% endfor %}
  });
  {% endif %}

  {% if component.computed %}
  describe('Computed Properties', () => {
    {% for computed_prop in component.computed %}
    it('should compute {{ computed_prop.name }} correctly', () => {
      // Arrange
      {% for dependency in computed_prop.dependencies %}
      wrapper.vm.{{ dependency }} = {{ computed_prop.test_setup[dependency] | tojson }};
      {% endfor %}

      // Act
      const result = wrapper.vm.{{ computed_prop.name }};

      // Assert
      expect(result).toBeDefined();
    });
    {% endfor %}
  });
  {% endif %}

  {% if component.methods %}
  describe('Methods', () => {
    {% for method in component.methods %}
    describe('{{ method.name }}', () => {
      it('should execute without errors', {{ 'async ' if method.is_async }}() => {
        // Arrange
        {% for param in method.parameters %}
        const {{ param }} = {{ method.test_values[param] | tojson }};
        {% endfor %}

        // Act
        {{ 'await ' if method.is_async }}wrapper.vm.{{ method.name }}({{ method.parameters | join(', ') }});

        // Assert
        {% if method.calls_store %}
        expect(actions.{{ method.expected_action }}).toHaveBeenCalled();
        {% endif %}
        {% if method.calls_router %}
        expect(wrapper.vm.$router.push).toHaveBeenCalled();
        {% endif %}
      });

      {% if method.is_async %}
      it('should handle errors gracefully', async () => {
        // Arrange
        {% if method.calls_store %}
        actions.{{ method.expected_action }}.mockRejectedValue(new Error('Test error'));
        {% endif %}

        // Act & Assert
        await expect(wrapper.vm.{{ method.name }}()).rejects.toThrow();
      });
      {% endif %}
    });
    {% endfor %}
  });
  {% endif %}

  {% if component.lifecycle_hooks %}
  describe('Lifecycle Hooks', () => {
    {% for hook in component.lifecycle_hooks %}
    it('should execute {{ hook.name }} correctly', () => {
      // Verify hook behavior through side effects
      expect(wrapper.vm).toBeDefined();
    });
    {% endfor %}
  });
  {% endif %}
});
```

---

## Pattern Learning for Jest

### Jest-Specific Error Patterns

```python
class JestPatternLearner:
    """Learns patterns from Jest test execution errors"""

    JEST_ERROR_PATTERNS = {
        "import_errors": [
            r"Cannot find module '([^']+)'",
            r"Module not found: Error: Can't resolve '([^']+)'"
        ],
        "mock_errors": [
            r"TypeError: Cannot read property '(\w+)' of undefined",
            r"ReferenceError: (\w+) is not defined"
        ],
        "vue_test_utils_errors": [
            r"\[vue-test-utils\]: (.+)",
            r"Unknown custom element: <([^>]+)>"
        ],
        "async_errors": [
            r"Timeout - Async callback was not invoked",
            r"Promise rejection not handled"
        ]
    }

    def learn_from_jest_output(self, test_output: str) -> List[Dict[str, Any]]:
        """
        Analyze Jest test output and extract learnable patterns

        Example patterns:
        1. Missing import: "Cannot find module '@/services/api'"
           → Learn: Always import from correct path alias

        2. Undefined mock: "TypeError: Cannot read property 'dispatch' of undefined"
           → Learn: Always mock Vuex store when component uses this.$store

        3. Unknown component: "Unknown custom element: <custom-button>"
           → Learn: Stub child components in shallowMount
        """
        patterns = []

        for error_type, regex_patterns in self.JEST_ERROR_PATTERNS.items():
            for regex in regex_patterns:
                matches = re.findall(regex, test_output)
                for match in matches:
                    pattern = self._create_pattern(error_type, match)
                    patterns.append(pattern)

        return patterns

    def _create_pattern(self, error_type: str, match: str) -> Dict[str, Any]:
        """Create pattern object from error match"""
        if error_type == "import_errors":
            return {
                "type": "import_correction",
                "module": match,
                "fix": f"Ensure '{match}' is correctly imported with path alias",
                "confidence": 0.9
            }
        elif error_type == "mock_errors":
            return {
                "type": "mock_requirement",
                "property": match,
                "fix": f"Mock '{match}' in test setup",
                "confidence": 0.85
            }
        # ... additional pattern types
```

---

## Cost Estimation

### Token Usage Breakdown

**Per Vue Component Analysis** (GPT-4o-mini):
- Source file size: ~300 lines average
- Template rendering: ~200 tokens
- Component analysis: ~500 tokens
- Test generation: ~1500 tokens
- **Total per component**: ~2200 tokens

**Pricing** (GPT-4o-mini):
- Input: $0.150 / 1M tokens
- Output: $0.600 / 1M tokens
- **Cost per component**: ~$0.0015 (0.15 cents)

**ecommerce-app Projection**:
- Estimated components: 45 Vue files
- Total cost: 45 × $0.0015 = **$0.0675** (6.75 cents)
- Pattern learning: ~$0.50 (one-time)
- **Total first run**: **$0.57**

**Comparison to .NET Generator**:
- .NET: $1.73 for 44 files
- Jest: $0.57 for 45 files
- **67% cheaper** (due to simpler JavaScript syntax vs C#)

---

## Implementation Roadmap

### Day 1: Core Architecture
- [x] Design base generator interface
- [ ] Implement `BaseTestGenerator` abstract class
- [ ] Implement `JavaScriptAnalyzer` class
- [ ] Create basic Vue component template
- [ ] Test on single Vue component from ecommerce-app

**Deliverable**: Single Vue component test generation working

### Day 2: Pattern Learning
- [ ] Implement `JestPatternLearner` class
- [ ] Create error pattern recognition for common Jest errors
- [ ] Build pattern cache system
- [ ] Test pattern learning on 5 components
- [ ] Verify 30-40% error reduction

**Deliverable**: Pattern learning functional with cache persistence

### Day 3: Full Integration
- [ ] Generate tests for all 45 ecommerce-app components
- [ ] Run Jest test suite
- [ ] Collect errors and learn patterns
- [ ] Regenerate with learned patterns
- [ ] Measure error reduction rate

**Deliverable**: Complete test suite for ecommerce-app

---

## Success Criteria

### Quantitative Metrics
- ✅ Generate 40+ component tests in < 10 minutes
- ✅ Total cost < $1.00 for first run
- ✅ Pattern learning cost < $0.50
- ✅ 30-40% error reduction with learned patterns
- ✅ 80%+ test coverage for component methods

### Qualitative Metrics
- ✅ Tests follow Jest best practices
- ✅ Proper use of `@vue/test-utils` API
- ✅ Correct mocking of Vuex and Vue Router
- ✅ Async/await handling for async methods
- ✅ Readable test descriptions

---

## Risk Mitigation

### Risk 1: Complex Component Logic
**Problem**: Deeply nested components with complex state management
**Mitigation**:
- Start with simpler components (PaymentSuccess.vue)
- Build complexity gradually
- Use pattern learning to discover edge cases

### Risk 2: Path Alias Resolution
**Problem**: Import paths like `@/services/api` may not resolve
**Mitigation**:
- Analyze `vue.config.js` for path aliases
- Configure Jest `moduleNameMapper` in template
- Learn import patterns from errors

### Risk 3: Third-Party Component Mocking
**Problem**: Components use libraries like `vue-advanced-cropper`
**Mitigation**:
- Auto-stub unknown components in shallowMount
- Provide manual mock templates for complex libraries
- Learn which components need special handling

---

## Next Steps

1. **Create prototype** (`jest_generator.py`) with basic Vue component analysis
2. **Test on PaymentSuccess.vue** (simplest starting point)
3. **Iterate based on real errors** from ecommerce-app
4. **Document learned patterns** in cache
5. **Scale to all components** once prototype validates

**Estimated Timeline**: 3 days to production-ready
**Estimated Cost**: < $1.00 for ecommerce-app full suite
**Expected Value**: $2,000+ developer time saved (40 components × 1 hour/component × $50/hr)
