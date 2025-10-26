# Universal Test Generator - Implementation Guide

**Date**: 2025-10-25
**Status**: Ready for Implementation
**Implementation Timeline**: 15 days
**Team Size**: 1 developer + AI assistance (GPT-4o-mini)

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Implementation Phases](#implementation-phases)
4. [Module Details](#module-details)
5. [Testing Strategy](#testing-strategy)
6. [Cost Analysis](#cost-analysis)
7. [Success Metrics](#success-metrics)
8. [Rollout Plan](#rollout-plan)

---

## Overview

### Project Goals

Extend the proven .NET unit test generator to support multiple test types and programming languages:

1. **Jest Test Generator** - JavaScript/TypeScript/Vue.js unit tests
2. **API Integration Test Generator** - REST API endpoint validation
3. **Database Test Generator** - Repository and stored procedure tests
4. **Playwright E2E Test Generator** - Browser-based end-to-end tests

### Success Criteria from Current Implementation

**Baseline Performance** (.NET Generator):
- ✅ 44 test files generated in ~5 minutes
- ✅ $2.23 total cost ($1.73 generation + $0.50 pattern learning)
- ✅ 30-40% error reduction with pattern learning
- ✅ 15 patterns automatically discovered and cached

**Target Performance** (Universal Generator):
- ✅ Support 4 test types (Jest, API, Database, E2E)
- ✅ Maintain <$5 cost per project
- ✅ Achieve 30-40% error reduction across all test types
- ✅ Complete implementation in 15 days

---

## Architecture

### Unified Base Architecture

```python
# generators/base_generator.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path
import json

class BaseTestGenerator(ABC):
    """
    Abstract base class for all test generators

    Provides common functionality:
    - Pattern caching
    - LLM integration
    - Cost tracking
    - Error learning
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.generator_type = self._get_generator_type()
        self.pattern_cache = self._load_patterns()
        self.llm_client = self._initialize_llm()
        self.cost_tracker = CostTracker()

    @abstractmethod
    def _get_generator_type(self) -> str:
        """Return the type of generator (dotnet, jest, api, database, playwright)"""
        pass

    @abstractmethod
    def analyze_source(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze source code to extract testable elements

        Returns:
            Dictionary containing analyzed elements (methods, properties, etc.)
        """
        pass

    @abstractmethod
    def generate_tests(self, analysis: Dict[str, Any]) -> str:
        """
        Generate test code from analysis results

        Args:
            analysis: Output from analyze_source()

        Returns:
            Generated test code as string
        """
        pass

    @abstractmethod
    def learn_patterns(self, error_log: str) -> List[Dict[str, Any]]:
        """
        Learn patterns from test execution errors

        Args:
            error_log: Output from test execution

        Returns:
            List of discovered patterns
        """
        pass

    def _load_patterns(self) -> Dict[str, Any]:
        """Load cached patterns from .test-gen-cache/"""
        cache_path = Path(".test-gen-cache") / f"{self.generator_type}_patterns.json"
        if cache_path.exists():
            return json.loads(cache_path.read_text())
        return {
            "imports": [],
            "type_corrections": [],
            "mock_requirements": [],
            "custom_patterns": []
        }

    def _save_patterns(self, patterns: Dict[str, Any]):
        """Save learned patterns to cache"""
        cache_path = Path(".test-gen-cache") / f"{self.generator_type}_patterns.json"
        cache_path.parent.mkdir(exist_ok=True)
        cache_path.write_text(json.dumps(patterns, indent=2))

    def _initialize_llm(self):
        """Initialize LangChain LLM client (GPT-4o-mini)"""
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.2,  # Low temperature for consistent output
            max_tokens=4000
        )

    def generate_with_patterns(self, file_path: str) -> str:
        """
        Complete generation workflow:
        1. Analyze source
        2. Apply cached patterns
        3. Generate tests
        4. Track costs
        """
        # Analyze
        analysis = self.analyze_source(file_path)

        # Apply patterns
        analysis = self._apply_cached_patterns(analysis)

        # Generate
        test_code = self.generate_tests(analysis)

        # Track cost
        self.cost_tracker.record_generation(file_path, self.llm_client.get_num_tokens(test_code))

        return test_code

    def _apply_cached_patterns(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Apply cached patterns to improve analysis"""
        for pattern_type, patterns in self.pattern_cache.items():
            if pattern_type == "type_corrections":
                for pattern in patterns:
                    # Apply type corrections to analysis
                    analysis = self._apply_type_correction(analysis, pattern)
            elif pattern_type == "import_corrections":
                for pattern in patterns:
                    # Add missing imports
                    analysis = self._apply_import_correction(analysis, pattern)

        return analysis
```

### Specialized Generators

Each generator extends `BaseTestGenerator` and implements specific logic:

```
BaseTestGenerator (abstract)
├── DotNetTestGenerator (existing)
├── JestTestGenerator (new)
├── ApiIntegrationGenerator (new)
├── DatabaseTestGenerator (new)
└── PlaywrightTestGenerator (new)
```

### Pattern Learning Architecture

```python
# pattern_learners/base_pattern_learner.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import JsonOutputParser

class BasePatternLearner(ABC):
    """Base class for pattern learning from test errors"""

    def __init__(self, llm_client):
        self.llm = llm_client
        self.parser = JsonOutputParser()

    @abstractmethod
    def get_error_patterns(self) -> Dict[str, List[str]]:
        """Return regex patterns for recognizing errors"""
        pass

    def learn_from_errors(self, error_log: str) -> List[Dict[str, Any]]:
        """
        Analyze error log and discover patterns

        Uses LangChain to:
        1. Extract errors using regex patterns
        2. Categorize errors by type
        3. Generate fix recommendations
        4. Return structured pattern objects
        """
        # Extract errors
        errors = self._extract_errors(error_log)

        # Use LLM to categorize and analyze
        prompt = ChatPromptTemplate.from_template("""
        Analyze the following test errors and provide structured patterns:

        Errors:
        {errors}

        For each unique error pattern, provide:
        1. Error type
        2. Root cause
        3. Fix recommendation
        4. Confidence score (0-1)

        Return JSON array of patterns.
        """)

        chain = prompt | self.llm | self.parser
        patterns = chain.invoke({"errors": json.dumps(errors)})

        return patterns

    def _extract_errors(self, error_log: str) -> List[Dict[str, Any]]:
        """Extract errors from log using regex patterns"""
        errors = []
        error_patterns = self.get_error_patterns()

        for error_type, regex_list in error_patterns.items():
            for regex in regex_list:
                matches = re.findall(regex, error_log)
                for match in matches:
                    errors.append({
                        "type": error_type,
                        "match": match,
                        "context": self._extract_context(error_log, match)
                    })

        return errors
```

---

## Implementation Phases

### Phase 1: Jest Generator (Days 1-3)

**Priority**: Highest (needed for ecommerce-app immediately)

**Day 1: Core Implementation**
```bash
# Create module structure
mkdir -p generators/jest
mkdir -p analyzers/javascript
mkdir -p templates/jest

# Implement files
touch generators/jest/jest_generator.py
touch analyzers/javascript/vue_analyzer.py
touch templates/jest/vue_component.jinja2
```

**Tasks**:
- [ ] Implement `JestTestGenerator` class extending `BaseTestGenerator`
- [ ] Implement `VueComponentAnalyzer` for Vue SFC parsing
- [ ] Create Jinja2 template for Vue component tests
- [ ] Test on single Vue component (PaymentSuccess.vue)

**Validation**:
```bash
cd /mnt/d/dev2/dotnet-unit-test-gen
source venv/bin/activate
python -m generators.jest.jest_generator \
  /mnt/d/dev2/michaeljr/ecommerce-app/src/views/PaymentSuccess.vue \
  -o /mnt/d/dev2/michaeljr/ecommerce-app/tests/unit/PaymentSuccess.spec.js
```

**Day 2: Pattern Learning**
- [ ] Implement `JestPatternLearner` class
- [ ] Define Jest-specific error patterns
- [ ] Test pattern learning on 5 components
- [ ] Validate 30-40% error reduction

**Day 3: Full Integration**
- [ ] Generate tests for all 45 ecommerce-app components
- [ ] Run Jest test suite: `npm test`
- [ ] Collect errors and learn patterns
- [ ] Regenerate with learned patterns
- [ ] Document results

**Success Metrics**:
- ✅ 40+ test files generated
- ✅ Cost < $1.00
- ✅ 30-40% error reduction
- ✅ 80%+ method coverage

---

### Phase 2: API Integration Generator (Days 4-6)

**Priority**: High (validates ecommerce-app ↔ PaymentAPI integration)

**Day 4: Backend API Analysis**
- [ ] Implement `ApiAnalyzer` for .NET Web API controllers
- [ ] Extract endpoints from `EcommerceController.vb`
- [ ] Generate integration test template
- [ ] Test on 1 PaymentAPI endpoint

**Day 5: Frontend + Contract Validation**
- [ ] Implement `FrontendApiAnalyzer` for JavaScript API services
- [ ] Extract API calls from `ecommerceApi.js`
- [ ] Implement `ApiContractValidator`
- [ ] Generate contract mismatch report

**Expected Output**:
```markdown
# API Contract Validation Report

## Type Mismatches Found

1. **send-customer-receipt endpoint**
   - Field: `pickupLocationId`
   - Frontend sends: Integer
   - Backend expects: String
   - Severity: Medium
   - Fix: Convert to string on frontend

2. **send-pickup-notification endpoint**
   - Field: `orderTotal`
   - Frontend sends: Number
   - Backend expects: String
   - Severity: Medium
   - Fix: Use .toFixed(2) before sending
```

**Day 6: Integration Testing**
- [ ] Generate full integration test suite
- [ ] Run tests against PaymentAPI
- [ ] Learn patterns from failures
- [ ] Regenerate with patterns

**Success Metrics**:
- ✅ 15+ endpoint tests generated
- ✅ Cost < $0.50
- ✅ 100% type mismatch detection
- ✅ 80%+ test pass rate

---

### Phase 3: Database Test Generator (Days 7-10)

**Priority**: Medium (needed for PaymentAPI data layer)

**Day 7-8: Repository Testing**
- [ ] Implement `RepositoryAnalyzer`
- [ ] Create InMemory database test template
- [ ] Test on PaymentDataAccess repository
- [ ] Generate CRUD operation tests

**Day 9: Stored Procedure Testing**
- [ ] Implement `SqlProcedureAnalyzer`
- [ ] Extract procedures from PaymentAPI database
- [ ] Create procedure integration test template
- [ ] Generate procedure tests with TestContainers

**Day 10: Pattern Learning + Integration**
- [ ] Run generated tests
- [ ] Learn constraint and FK patterns
- [ ] Regenerate with patterns
- [ ] Measure improvement

**Success Metrics**:
- ✅ 8+ repository tests generated
- ✅ 10+ procedure tests generated
- ✅ Cost < $0.50
- ✅ Transaction and FK handling validated

---

### Phase 4: Playwright E2E Generator (Days 11-15)

**Priority**: Medium (validates complete user journeys)

**Day 11-12: Page Object Generation**
- [ ] Implement `RouteAnalyzer` for Vue Router
- [ ] Implement `ComponentInteractionAnalyzer`
- [ ] Create Page Object Model template
- [ ] Test on ecommerce-app routes

**Day 13-14: User Flow Tests**
- [ ] Implement `UserFlowAnalyzer`
- [ ] Detect checkout flow in ecommerce-app
- [ ] Generate complete user journey tests
- [ ] Run Playwright tests

**Day 15: Visual Testing + Pattern Learning**
- [ ] Add visual regression tests
- [ ] Implement `PlaywrightPatternLearner`
- [ ] Learn selector and navigation patterns
- [ ] Final regeneration

**Success Metrics**:
- ✅ 8+ Page Objects generated
- ✅ 3+ user flow tests
- ✅ Cost < $1.00
- ✅ 70%+ test pass rate
- ✅ Visual baseline created

---

## Module Details

### File Structure After Implementation

```
dotnet-unit-test-gen/
├── README.md (updated)
├── requirements.txt (updated with new dependencies)
├── .test-gen-cache/
│   ├── dotnet_patterns.json
│   ├── jest_patterns.json
│   ├── api_patterns.json
│   ├── database_patterns.json
│   └── playwright_patterns.json
├── generators/
│   ├── base_generator.py                # NEW - Base class
│   ├── dotnet/
│   │   └── dotnet_generator.py          # Refactored from existing
│   ├── jest/
│   │   └── jest_generator.py            # NEW
│   ├── api/
│   │   └── api_integration_generator.py # NEW
│   ├── database/
│   │   └── database_generator.py        # NEW
│   └── playwright/
│       └── playwright_generator.py      # NEW
├── analyzers/
│   ├── base_analyzer.py                 # NEW - Base analyzer
│   ├── dotnet/
│   │   └── csharp_analyzer.py
│   ├── javascript/
│   │   ├── vue_analyzer.py              # NEW
│   │   ├── react_analyzer.py            # NEW (future)
│   │   └── typescript_analyzer.py       # NEW (future)
│   ├── api/
│   │   ├── dotnet_api_analyzer.py       # NEW
│   │   └── frontend_api_analyzer.py     # NEW
│   ├── database/
│   │   ├── repository_analyzer.py       # NEW
│   │   ├── dbcontext_analyzer.py        # NEW
│   │   └── sql_procedure_analyzer.py    # NEW
│   └── playwright/
│       ├── route_analyzer.py            # NEW
│       ├── user_flow_analyzer.py        # NEW
│       └── component_interaction_analyzer.py # NEW
├── templates/
│   ├── dotnet/
│   │   └── xunit_controller.jinja2
│   ├── jest/
│   │   ├── vue_component.jinja2         # NEW
│   │   ├── react_component.jinja2       # NEW (future)
│   │   ├── vuex_store.jinja2            # NEW
│   │   └── service_class.jinja2         # NEW
│   ├── api/
│   │   ├── dotnet_api_integration.jinja2  # NEW
│   │   ├── javascript_api_client.jinja2   # NEW
│   │   └── contract_validation.jinja2     # NEW
│   ├── database/
│   │   ├── repository_tests.jinja2        # NEW
│   │   ├── dbcontext_tests.jinja2         # NEW
│   │   └── stored_procedure_tests.jinja2  # NEW
│   └── playwright/
│       ├── page_object.jinja2             # NEW
│       ├── user_flow_test.jinja2          # NEW
│       └── visual_regression.jinja2       # NEW
├── pattern_learners/
│   ├── base_pattern_learner.py          # NEW - Base learner
│   ├── langchain_pattern_learner.py     # Refactored from existing
│   ├── jest_pattern_learner.py          # NEW
│   ├── api_pattern_learner.py           # NEW
│   ├── database_pattern_learner.py      # NEW
│   └── playwright_pattern_learner.py    # NEW
├── utils/
│   ├── cost_tracker.py                  # NEW - Cost tracking
│   ├── test_data_builder.py            # NEW - Test data generation
│   └── validators.py                    # NEW - Contract validation
└── docs/
    ├── UNIVERSAL-TEST-GENERATOR-PLAN.md
    ├── IMPLEMENTATION-GUIDE.md          # THIS FILE
    └── modules/
        ├── JEST-GENERATOR-SPEC.md
        ├── API-INTEGRATION-GENERATOR-SPEC.md
        ├── DATABASE-GENERATOR-SPEC.md
        └── PLAYWRIGHT-GENERATOR-SPEC.md
```

---

## Testing Strategy

### Meta-Testing Approach

**Principle**: Use TDD to build the test generators themselves

**Phase 1 Tests** (Jest Generator):
```python
# tests/test_jest_generator.py
import pytest
from generators.jest.jest_generator import JestTestGenerator

class TestJestGenerator:
    def test_analyze_vue_component(self):
        """Test Vue component analysis"""
        generator = JestTestGenerator({})
        analysis = generator.analyze_source("tests/fixtures/SampleComponent.vue")

        assert analysis["type"] == "vue_component"
        assert "props" in analysis
        assert "methods" in analysis

    def test_generate_basic_test(self):
        """Test basic test generation"""
        generator = JestTestGenerator({})
        analysis = {
            "type": "vue_component",
            "name": "SampleComponent",
            "props": [{"name": "title", "type": "String"}],
            "methods": [{"name": "handleClick", "is_async": False}]
        }

        test_code = generator.generate_tests(analysis)

        assert "describe('SampleComponent'" in test_code
        assert "it('should accept title prop'" in test_code
        assert "it('should execute handleClick'" in test_code

    def test_pattern_learning(self):
        """Test pattern learning from Jest errors"""
        generator = JestTestGenerator({})
        error_log = """
        FAIL  tests/SampleComponent.spec.js
          ● SampleComponent › should render
            Cannot find module '@/services/api'
        """

        patterns = generator.learn_patterns(error_log)

        assert len(patterns) > 0
        assert patterns[0]["type"] == "import_correction"
```

**Validation Process**:
1. Write tests for generator BEFORE implementing
2. Implement generator to pass tests
3. Run generator on real project (ecommerce-app)
4. Collect errors
5. Improve generator based on real-world errors
6. Repeat until success metrics met

---

## Cost Analysis

### Per-Module Cost Breakdown

| Module | Files Generated | Cost per File | Total Generation | Pattern Learning | Total Cost |
|--------|----------------|---------------|------------------|------------------|------------|
| Jest | 45 components | $0.0015 | $0.0675 | $0.50 | **$0.57** |
| API Integration | 15 endpoints | $0.0008 | $0.012 | $0.30 | **$0.31** |
| Database | 18 classes/procs | $0.0012 | $0.022 | $0.40 | **$0.42** |
| Playwright | 11 pages/flows | $0.0015 | $0.0165 | $0.50 | **$0.52** |
| **TOTAL** | **89 test files** | - | **$0.12** | **$1.70** | **$1.82** |

### ROI Calculation

**Developer Time Saved**:
- Manual test writing: 89 files × 30 minutes/file = **44.5 hours**
- Developer rate: $100/hour
- **Total value**: $4,450

**AI Cost**:
- Generation: $0.12
- Pattern learning: $1.70
- **Total cost**: $1.82

**Net Savings**: $4,450 - $1.82 = **$4,448.18**

**ROI**: (4,448.18 / 1.82) × 100 = **244,307%**

---

## Success Metrics

### Quantitative Metrics

**Generation Performance**:
- ✅ Generate 89 test files in < 30 minutes
- ✅ Total cost < $2.00 for ecommerce-app + PaymentAPI
- ✅ 30-40% error reduction with pattern learning
- ✅ 80%+ code coverage across all test types

**Quality Metrics**:
- ✅ 70%+ tests pass on first run (before pattern learning)
- ✅ 90%+ tests pass after pattern learning
- ✅ Zero false positives (tests fail when they should)
- ✅ 100% type mismatch detection (API contracts)

### Qualitative Metrics

- ✅ Tests follow framework best practices
- ✅ Readable test descriptions
- ✅ Proper mocking and setup
- ✅ Comprehensive error handling
- ✅ Documentation generated alongside tests

---

## Rollout Plan

### Week 1: Foundation (Days 1-5)

**Days 1-3**: Jest Generator (Phase 1)
- Implement and test on ecommerce-app
- Document patterns learned
- Update README with Jest examples

**Days 4-5**: API Integration Generator (Phase 2 start)
- Implement backend API analysis
- Test on PaymentAPI endpoints

### Week 2: Integration (Days 6-10)

**Days 6-7**: API Integration Generator (Phase 2 complete)
- Frontend analysis and contract validation
- Generate full integration suite

**Days 8-10**: Database Generator (Phase 3)
- Repository and procedure testing
- Test on PaymentDataAccess layer

### Week 3: E2E + Polish (Days 11-15)

**Days 11-15**: Playwright Generator (Phase 4)
- Page Objects and user flows
- Visual regression testing
- Final documentation

---

## Next Steps

### Immediate Actions (Today)

1. ✅ Create comprehensive planning documentation (COMPLETE)
2. ⏭️ Update project README with universal generator vision
3. ⏭️ Set up new directory structure
4. ⏭️ Implement `BaseTestGenerator` abstract class
5. ⏭️ Begin Jest generator implementation

### First Implementation Task (Tomorrow)

**Task**: Implement Jest Generator for single Vue component

**Steps**:
```bash
# 1. Create base generator
touch generators/base_generator.py

# 2. Create Jest generator
mkdir -p generators/jest
touch generators/jest/__init__.py
touch generators/jest/jest_generator.py

# 3. Create Vue analyzer
mkdir -p analyzers/javascript
touch analyzers/javascript/__init__.py
touch analyzers/javascript/vue_analyzer.py

# 4. Create template
mkdir -p templates/jest
touch templates/jest/vue_component.jinja2

# 5. Test on single component
python -m generators.jest.jest_generator \
  /mnt/d/dev2/michaeljr/ecommerce-app/src/views/Home.vue \
  -o /mnt/d/dev2/michaeljr/ecommerce-app/tests/unit/Home.spec.js
```

**Validation**:
```bash
cd /mnt/d/dev2/michaeljr/ecommerce-app
npm test tests/unit/Home.spec.js
```

**Expected Outcome**:
- Single test file generated (< 5 minutes)
- Cost < $0.01
- Test compiles and runs (may have errors, that's OK)
- Errors logged for pattern learning

---

## Risk Mitigation

### Technical Risks

**Risk 1**: Pattern learning doesn't generalize well across test types
**Mitigation**:
- Start with proven .NET pattern learner
- Adapt gradually for each test type
- Validate on real projects before scaling

**Risk 2**: Cost exceeds budget ($2.00 target)
**Mitigation**:
- Use GPT-4o-mini (not GPT-4)
- Cache aggressively
- Limit token usage per file
- Monitor costs in real-time

**Risk 3**: Generated tests too brittle
**Mitigation**:
- Use best practices (Page Objects, proper mocking)
- Learn from real errors
- Iterate based on actual usage

### Process Risks

**Risk 4**: Implementation timeline slips
**Mitigation**:
- Start with highest-value module (Jest)
- Get early feedback from real usage
- Prioritize working code over perfect code
- Document learnings for future iterations

---

## Conclusion

This implementation guide provides a comprehensive roadmap for extending the proven .NET unit test generator to a universal test generation platform. By following the TDD approach and leveraging the successful pattern learning architecture, we can deliver significant value to developers while maintaining low costs and high quality.

**Key Takeaways**:
1. Build on proven success (existing .NET generator)
2. Use TDD for meta-testing (test the test generator)
3. Leverage LangChain and GPT-4o-mini for cost-effective pattern learning
4. Start with highest-value module (Jest for ecommerce-app)
5. Iterate based on real-world usage

**Expected Impact**:
- **Time Saved**: 44.5 hours per project
- **Cost**: $1.82 per project
- **ROI**: 244,307%
- **Developer Satisfaction**: High (automated tedious work)
