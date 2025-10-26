# TODO - .NET Unit Test Generator

**Last Updated**: October 25, 2025
**Current Status**: Production-Ready (LangChain 1.0 operational)
**Project Phase**: Enhancement & Expansion

---

## 🎯 Priority Matrix

| Priority | Timeline | Focus Area |
|----------|----------|------------|
| **P0** | This Week | Critical fixes, documentation gaps |
| **P1** | 1-2 Weeks | Core enhancements, immediate value-adds |
| **P2** | 1-2 Months | Universal generator expansion |
| **P3** | 3+ Months | Advanced features, marketplace |

---

## 📋 P0: Critical Tasks (Do First)

### Documentation & Marketing

- [ ] **Update README.md badges and status**
  - Add Python version badge
  - Add license badge
  - Update "Last Updated" to Oct 25, 2025
  - Verify all links work
  - Time: 15 min

- [ ] **Create docs/README.md (Documentation Index)**
  - Link to all guides (QUICKSTART, TWO-PHASE-WORKFLOW)
  - Link to LangChain docs
  - Link to module specs
  - Link to implementation guide
  - Time: 15 min

- [ ] **Verify pattern cache integrity**
  - Check `.test-gen-cache/b5df0a773108/patterns.json` has 15 patterns
  - Verify project-info.json is correct
  - Test pattern loading in generate_tests.py
  - Time: 10 min

### Code Quality

- [ ] **Add .gitignore entries**
  - Add `*.log`, `build-output.txt`
  - Add `.test-gen-cache/` (but keep structure documented)
  - Add `__pycache__/`, `*.pyc`
  - Add `venv/` if not already there
  - Time: 5 min

- [ ] **Create LICENSE file**
  - Choose appropriate license (MIT recommended for open source tier)
  - Add commercial licensing note
  - Time: 10 min

---

## 🔧 P1: Core Enhancements (1-2 Weeks)

### Current .NET Generator Improvements

- [ ] **Iterative Refinement Module (CRITICAL)**
  - Status: `langchain_refinement.py` exists but marked "In Progress"
  - Test compatibility with LangChain 1.0
  - Integrate with main workflow after pattern learning
  - Target: 70-90% auto-fix rate (from docs)
  - Files: `langchain_refinement.py`
  - Time: 2-3 hours

- [ ] **Cross-File Context Management**
  - Status: `langchain_context_manager.py` exists but marked "In Progress"
  - Test integration with generate_tests.py
  - Verify context improves generation quality
  - Measure impact on error reduction
  - Files: `langchain_context_manager.py`
  - Time: 2-3 hours

- [ ] **NUnit Framework Support**
  - Extend generate_tests.py to support NUnit
  - Add NUnit-specific templates
  - Test on sample project
  - Update docs
  - Time: 4-6 hours

- [ ] **MSTest Framework Support**
  - Extend generate_tests.py to support MSTest
  - Add MSTest-specific templates
  - Test on sample project
  - Update docs
  - Time: 4-6 hours

- [ ] **VB.NET Generator Enhancement**
  - Status: `generate_tests_vbnet.py` exists (34KB)
  - Test on PaymentAPI project
  - Document results
  - Integrate pattern learning
  - Files: `generate_tests_vbnet.py`
  - Time: 2-3 hours

### Multi-Provider Support (Cost Optimization)

- [ ] **Add Claude 3.5 Haiku Support**
  - Install anthropic SDK: `pip install anthropic`
  - Create `providers/claude_provider.py`
  - Pricing: $0.0008 input / $0.004 output per 1K tokens
  - Cost savings: 74% cheaper than GPT-4 Turbo
  - Time: 2-3 hours

- [ ] **Add Google Gemini 2.0 Flash Support**
  - Install google-generativeai SDK
  - Create `providers/gemini_provider.py`
  - Pricing: $0.0001 input / $0.0004 output per 1K tokens
  - Cost savings: 97% cheaper than GPT-4 Turbo
  - Time: 2-3 hours

- [ ] **Add OpenRouter Aggregator Support**
  - Install openrouter SDK
  - Create `providers/openrouter_provider.py`
  - Access to 100+ models via single API
  - Time: 2-3 hours

- [ ] **Add Provider Selection CLI Flag**
  - Update generate_tests.py CLI: `--provider openai|claude|gemini|openrouter`
  - Add cost comparison in --dry-run mode
  - Default to cheapest provider
  - Document in README and CLAUDE.md
  - Time: 1-2 hours

### Developer Experience

- [ ] **Create Benchmark Script**
  - Measure generation time per file
  - Measure token usage per file
  - Measure cost per file
  - Measure error reduction with patterns
  - Output: `docs/BENCHMARKS.md`
  - Time: 1-2 hours

- [ ] **Create GitHub Issue Templates**
  - Bug report template
  - Feature request template
  - Pattern submission template
  - Time: 30 min

- [ ] **Create Pull Request Template**
  - Checklist for contributors
  - Testing requirements
  - Documentation requirements
  - Time: 20 min

- [ ] **Create CONTRIBUTING.md**
  - How to set up dev environment
  - How to run tests
  - How to submit PRs
  - Code style guidelines
  - Time: 1 hour

---

## 🚀 P2: Universal Test Generator (1-2 Months)

### Architecture Refactoring

- [ ] **Create Base Abstraction Layer**
  - Implement `generators/base_generator.py` (from IMPLEMENTATION-GUIDE.md)
  - Implement `analyzers/base_analyzer.py`
  - Implement `pattern_learners/base_pattern_learner.py`
  - Implement `templates/base_template.py` (Jinja2)
  - Refactor existing generate_tests.py to inherit from base
  - Time: 2 days
  - Spec: `docs/IMPLEMENTATION-GUIDE.md` lines 54-182

- [ ] **Modular Language Support Architecture**
  - Create `languages/base_language.py` interface
  - Migrate C# to `languages/csharp_language.py`
  - Migrate VB.NET to `languages/vbnet_language.py`
  - Create unified `core/generator.py` orchestrator
  - Time: 2 days
  - Benefit: Makes adding Java/Python/TypeScript trivial

### Module 1: Jest Generator (Phase 1 - Highest Priority)

- [ ] **Day 1: Core Jest Implementation**
  - Create `generators/jest/jest_generator.py`
  - Create `analyzers/javascript/vue_analyzer.py`
  - Create `templates/jest/vue_component.jinja2`
  - Test on single Vue component (PaymentSuccess.vue from ecommerce-app)
  - Time: 1 day
  - Spec: `docs/modules/JEST-GENERATOR-SPEC.md`

- [ ] **Day 2: Jest Pattern Learning**
  - Create `pattern_learners/jest_pattern_learner.py`
  - Define Jest-specific error patterns (describe/it errors, mock errors, etc.)
  - Test on 5 components
  - Validate 30-40% error reduction
  - Time: 1 day

- [ ] **Day 3: Full Jest Integration**
  - Generate tests for all 45 ecommerce-app components
  - Run `npm test` and collect errors
  - Learn patterns and regenerate
  - Document results in `docs/modules/JEST-TEST-RESULTS.md`
  - Time: 1 day
  - Target: 40+ test files, <$1.00 cost, 30-40% error reduction

### Module 2: API Integration Generator (Phase 2)

- [ ] **Day 1: Backend API Analysis**
  - Create `generators/api/api_integration_generator.py`
  - Create `analyzers/dotnet/api_analyzer.py`
  - Extract endpoints from .NET Web API controllers
  - Test on 1 PaymentAPI endpoint
  - Time: 1 day
  - Spec: `docs/modules/API-INTEGRATION-GENERATOR-SPEC.md`

- [ ] **Day 2: Frontend + Contract Validation**
  - Create `analyzers/javascript/frontend_api_analyzer.py`
  - Extract API calls from JavaScript (axios, fetch)
  - Implement contract validator (frontend ↔ backend match)
  - Generate mismatch report
  - Time: 1 day

- [ ] **Day 3: Full API Test Suite**
  - Generate tests for 15 PaymentAPI endpoints
  - Test frontend-backend contracts
  - Document mismatches
  - Time: 1 day
  - Target: 15 test files, <$0.50 cost

### Module 3: Database Test Generator (Phase 3)

- [ ] **Day 1-2: Repository Test Generation**
  - Create `generators/database/database_generator.py`
  - Analyze Entity Framework repositories
  - Generate repository unit tests
  - Time: 2 days
  - Spec: `docs/modules/DATABASE-GENERATOR-SPEC.md`

- [ ] **Day 3-4: Stored Procedure Testing**
  - Create SQL analyzer for stored procedures
  - Generate integration tests with TestContainers
  - Generate mock data factories
  - Time: 2 days
  - Target: 18 test files, <$0.50 cost

### Module 4: Playwright E2E Generator (Phase 4)

- [ ] **Day 1-3: Page Object + Flow Generation**
  - Create `generators/playwright/playwright_generator.py`
  - Analyze Vue routes and components
  - Generate Page Object Models
  - Time: 3 days
  - Spec: `docs/modules/PLAYWRIGHT-GENERATOR-SPEC.md`

- [ ] **Day 4-5: User Flow Tests**
  - Generate end-to-end user flow tests
  - Test critical paths (checkout, login, etc.)
  - Integrate with CI/CD
  - Time: 2 days
  - Target: 11 test files, <$0.60 cost

---

## 🎨 P3: Advanced Features (3+ Months)

### Advanced Testing Features

- [ ] **Test Data Builder Generation**
  - Generate builder pattern classes for test data
  - Support for complex object graphs
  - Faker integration for realistic data
  - Time: 1 week

- [ ] **Coverage Report Integration**
  - Integrate with dotnet-coverage
  - Generate coverage gap reports
  - Auto-generate tests for uncovered code
  - Time: 1 week

- [ ] **Custom Prompt Templates**
  - Allow users to customize test generation prompts
  - Template marketplace concept
  - Time: 1 week

### Pattern Library & Marketplace

- [ ] **Pattern Library Creation**
  - Extract common patterns from RemoteC
  - Create pattern templates for ASP.NET Core
  - Create pattern templates for Entity Framework
  - Create pattern templates for Vue.js
  - Files: `patterns/library/` directory
  - Time: 2 days

- [ ] **Pattern Import/Export**
  - Add CLI commands: `--export-patterns`, `--import-patterns`
  - Support JSON format for sharing
  - Time: 1 day

- [ ] **Pattern Marketplace (Concept)**
  - Web interface for browsing patterns
  - User-submitted patterns
  - Rating and review system
  - Time: 2 weeks

### IDE Integrations

- [ ] **Visual Studio Extension**
  - Right-click → "Generate Unit Tests"
  - Show pattern suggestions inline
  - Time: 2 weeks

- [ ] **VS Code Extension**
  - Command palette integration
  - Test generation from sidebar
  - Time: 1 week

- [ ] **CI/CD Integration Scripts**
  - GitHub Actions workflow template
  - Azure DevOps pipeline template
  - GitLab CI template
  - Time: 1 week

- [ ] **Pre-commit Hook**
  - Auto-generate tests for new/modified classes
  - Validate test coverage before commit
  - Time: 2 days

### Marketing & Growth

- [ ] **Marketing Landing Page**
  - Create `site/index.html` (responsive design)
  - ROI calculator (interactive)
  - Case studies section
  - Pricing & licensing tiers
  - Contact form
  - Time: 4-6 hours
  - Reference: TODO.md lines 32-88 (old)

- [ ] **Demo Video Creation**
  - Screencast: Basic generation (2 min)
  - Screencast: Pattern learning (3 min)
  - Screencast: Error reduction (2 min)
  - Upload to YouTube
  - Embed on landing page
  - Time: 2-3 hours

- [ ] **Blog Posts**
  - "How We Built a Self-Learning .NET Test Generator"
  - "ROI Analysis: AI-Powered Test Generation"
  - "LangChain 1.0 Pattern Learning Deep Dive"
  - "RemoteC Case Study: 44 Controllers in 5 Minutes"
  - Time: 2 hours each

- [ ] **Social Media Campaign**
  - LinkedIn posts with results
  - Dev.to article on pattern learning
  - Reddit posts (r/dotnet, r/csharp)
  - Twitter/X thread
  - Time: 2-3 hours

---

## 🔬 Testing & Validation

### Test the Test Generator (TDD)

- [ ] **Unit Tests for Core Components**
  - Test `ProjectPatternCache` load/save
  - Test pattern matching logic
  - Test cost calculation
  - Test file discovery
  - Framework: pytest
  - Time: 1 day

- [ ] **Integration Tests**
  - Test full workflow on sample project
  - Test pattern learning cycle
  - Test multi-provider switching
  - Time: 1 day

- [ ] **Regression Tests**
  - Test RemoteC project (44 controllers)
  - Verify 15 patterns still loaded
  - Verify error reduction still 30-40%
  - Time: 30 min

### Validation Projects

- [ ] **Run on PaymentAPI (VB.NET)**
  - Generate tests for all controllers
  - Learn patterns
  - Regenerate
  - Document results in `docs/case-studies/PAYMENT-API-RESULTS.md`
  - Time: 1 hour

- [ ] **Run on ecommerce-app (Vue.js)**
  - After Jest generator complete
  - Generate tests for all components
  - Document results
  - Time: 1 hour

---

## 📦 Release Management

### Version 1.1 (Current + P1 Features)

- [ ] **Features**
  - ✅ LangChain 1.0 pattern learning
  - ✅ Pattern persistence
  - ✅ Multi-model support (GPT-4, GPT-3.5)
  - [ ] Multi-provider support (Claude, Gemini)
  - [ ] Iterative refinement module
  - [ ] Cross-file context
  - [ ] NUnit/MSTest support

- [ ] **Release Tasks**
  - Update version in README.md
  - Create CHANGELOG.md
  - Tag release: `git tag v1.1.0`
  - Create GitHub release with notes
  - Time: 1 hour

### Version 2.0 (Universal Generator)

- [ ] **Features**
  - [ ] Base abstraction layer
  - [ ] Jest generator
  - [ ] API integration generator
  - [ ] Database generator
  - [ ] Playwright generator

- [ ] **Release Tasks**
  - Major version bump
  - Marketing push
  - Blog post announcement
  - Time: 2 hours

---

## 🎓 Documentation Improvements

### User Documentation

- [ ] **FAQ.md**
  - Common questions
  - Troubleshooting tips
  - Pattern examples
  - Time: 1 hour

- [ ] **VIDEO-TUTORIALS.md**
  - Links to YouTube tutorials
  - Timestamps for key sections
  - Time: 30 min

- [ ] **BEST-PRACTICES.md**
  - When to use pattern learning
  - How to organize test projects
  - Naming conventions
  - Time: 1 hour

### Technical Documentation

- [ ] **ARCHITECTURE.md**
  - System design overview
  - Component interactions
  - Data flow diagrams
  - Time: 2 hours

- [ ] **API-REFERENCE.md**
  - CLI commands reference
  - Python API reference (for programmatic use)
  - Time: 2 hours

- [ ] **PATTERN-SCHEMA.md**
  - Pattern JSON schema
  - Pattern types reference
  - How to write custom patterns
  - Time: 1 hour

---

## 🐛 Known Issues & Improvements

### Bug Fixes

- [ ] **Handle empty source files gracefully**
  - Currently may error on empty .cs files
  - Should skip with warning
  - Priority: Low

- [ ] **Improve error messages for missing dependencies**
  - Better error when OPENAI_API_KEY missing
  - Better error when dotnet not installed (for pattern learner)
  - Priority: Medium

- [ ] **Rate limiting improvements**
  - Add exponential backoff for rate limits
  - Add progress indicator during retries
  - Priority: Low

### Performance Improvements

- [ ] **Cache LLM responses**
  - Avoid regenerating identical classes
  - Use content hash as cache key
  - Priority: Medium
  - Potential savings: 50%+ cost reduction on reruns

- [ ] **Parallel test generation**
  - Generate multiple tests concurrently
  - Respect rate limits
  - Priority: Medium
  - Potential speedup: 3-5x

- [ ] **Optimize token usage**
  - Remove unnecessary whitespace from prompts
  - Use more efficient prompt formatting
  - Priority: Low
  - Potential savings: 10-15% cost reduction

---

## 📊 Metrics & Analytics

### Track These Metrics

- [ ] **Usage Analytics**
  - Number of test files generated
  - Total projects analyzed
  - Average cost per project
  - Store in `.test-gen-cache/analytics.json`
  - Time: 2 hours

- [ ] **Pattern Effectiveness**
  - Track error reduction by pattern type
  - Identify most valuable patterns
  - Generate pattern effectiveness report
  - Time: 3 hours

- [ ] **Cost Tracking Dashboard**
  - Web dashboard showing costs over time
  - Provider cost comparison
  - ROI calculator
  - Time: 1 day

---

## 🎯 Success Criteria

### Project Considered "Complete" When:

**Version 1.1 (Current + Enhancements)**
- [x] LangChain 1.0 pattern learner operational
- [x] Pattern persistence working (15+ patterns cached)
- [x] Documentation comprehensive (CLAUDE.md, README.md)
- [ ] Multi-provider support (Claude, Gemini)
- [ ] Iterative refinement module integrated
- [ ] NUnit/MSTest support
- [ ] License file added
- [ ] Marketing page live
- [ ] 100+ downloads/users

**Version 2.0 (Universal Generator)**
- [ ] Jest generator operational (40+ test files)
- [ ] API integration generator operational (15+ test files)
- [ ] Database generator operational (18+ test files)
- [ ] Playwright generator operational (11+ test files)
- [ ] All modules achieve 30-40% error reduction
- [ ] Total cost <$5 per full project suite
- [ ] Documentation for all 4 modules
- [ ] 500+ downloads/users

---

## 🔗 Reference

**Key Files**:
- Current implementation: `generate_tests.py`, `langchain_pattern_learner_v1.py`
- Planning docs: `docs/UNIVERSAL-TEST-GENERATOR-PLAN.md`, `docs/IMPLEMENTATION-GUIDE.md`
- Module specs: `docs/modules/*.md`
- Case study: `docs/langchain/LANGCHAIN-TEST-RESULTS.md`

**Current Status** (Oct 25, 2025):
- ✅ Core generator: Production-ready
- ✅ Pattern learning: Operational (LangChain 1.0)
- ✅ Pattern cache: Working (15 patterns)
- ⚠️ Iterative refinement: In progress (`langchain_refinement.py`)
- ⚠️ Cross-file context: In progress (`langchain_context_manager.py`)
- 🔵 Universal expansion: Planning complete, implementation not started
- 🔵 Multi-provider: Planned, not implemented

**Next Actions**:
1. Complete P0 tasks (documentation, .gitignore, LICENSE)
2. Test and integrate refinement module
3. Add multi-provider support (biggest ROI)
4. Begin Universal Generator Phase 1 (Jest)

---

**Created**: October 23, 2025
**Updated**: October 25, 2025
**Next Review**: After P0 tasks complete
