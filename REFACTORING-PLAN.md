# Modular Architecture Refactoring Plan

**Branch**: `refactor/modular-architecture`
**Baseline**: v1.0 (tag created)
**Date Started**: October 25, 2025
**Goal**: First-class modular tool with multi-provider and multi-language support

---

## 🎯 Objectives

### Primary Goals

1. **Multi-Provider Support** - Reduce costs by 74-97%
   - Add Claude 3.5 Haiku ($0.0008/$0.004 per 1K tokens)
   - Add Gemini 2.0 Flash ($0.0001/$0.0004 per 1K tokens)
   - Add OpenRouter aggregator (100+ models)
   - Make provider selection trivial via CLI

2. **Modular Language Support** - Make adding new languages easy
   - Abstract language-specific logic into plugins
   - Create unified orchestrator
   - Enable Java, Python, TypeScript, Go support with minimal effort

3. **Maintainability** - Clean, testable architecture
   - Separation of concerns
   - Single Responsibility Principle
   - Easy to test each component
   - Clear interfaces

### Success Metrics

- ✅ All existing tests still pass
- ✅ Pattern learning still works (15 patterns for RemoteC)
- ✅ Cost reduced by 74%+ when using Claude Haiku
- ✅ Cost reduced by 97%+ when using Gemini Flash
- ✅ Adding a new language takes <4 hours
- ✅ Adding a new provider takes <2 hours
- ✅ Code coverage >80%

---

## 📐 New Architecture

### Directory Structure

```
dotnet-unit-test-gen/
├── core/
│   ├── __init__.py
│   ├── orchestrator.py         # Main workflow orchestration
│   ├── file_scanner.py          # File discovery and filtering
│   ├── output_writer.py         # Test file writing
│   └── cost_tracker.py          # Cost tracking across providers
│
├── providers/
│   ├── __init__.py
│   ├── base_provider.py         # Abstract base class
│   ├── openai_provider.py       # OpenAI/GPT implementation
│   ├── claude_provider.py       # Anthropic Claude implementation
│   ├── gemini_provider.py       # Google Gemini implementation
│   └── openrouter_provider.py   # OpenRouter aggregator
│
├── languages/
│   ├── __init__.py
│   ├── base_language.py         # Abstract language handler
│   ├── csharp_language.py       # C# parser, prompts, auto-fixes
│   ├── vbnet_language.py        # VB.NET parser, prompts, auto-fixes
│   ├── java_language.py         # Future: Java support
│   ├── python_language.py       # Future: Python support
│   └── typescript_language.py   # Future: TypeScript support
│
├── patterns/
│   ├── __init__.py
│   ├── pattern_cache.py         # Pattern storage (refactored from generate_tests.py)
│   ├── pattern_learner.py       # Base pattern learner
│   └── langchain_learner.py     # LangChain-based learner (existing logic)
│
├── tests/                       # NEW - Unit tests for all components
│   ├── __init__.py
│   ├── test_providers.py
│   ├── test_languages.py
│   ├── test_pattern_cache.py
│   └── test_integration.py
│
├── generate_tests.py            # Main CLI (refactored to use new architecture)
├── requirements.txt             # Add: anthropic, google-generativeai
└── .env.template                # Add provider API keys
```

### Component Interfaces

#### 1. BaseAIProvider

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

@dataclass
class CompletionRequest:
    prompt: str
    max_tokens: int = 2000
    temperature: float = 0.2

@dataclass
class CompletionResponse:
    content: str
    input_tokens: int
    output_tokens: int
    cost: float
    model: str

class BaseAIProvider(ABC):
    """Abstract base class for AI providers"""

    @abstractmethod
    def generate_completion(self, request: CompletionRequest) -> CompletionResponse:
        """Generate completion from prompt"""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return provider name (e.g., 'OpenAI GPT-4')"""
        pass

    @abstractmethod
    def get_cost_per_1k_input(self) -> float:
        """Return cost per 1K input tokens"""
        pass

    @abstractmethod
    def get_cost_per_1k_output(self) -> float:
        """Return cost per 1K output tokens"""
        pass

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for token counts"""
        input_cost = (input_tokens / 1000) * self.get_cost_per_1k_input()
        output_cost = (output_tokens / 1000) * self.get_cost_per_1k_output()
        return input_cost + output_cost
```

#### 2. BaseLanguageHandler

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any

@dataclass
class ClassInfo:
    """Language-agnostic class information"""
    name: str
    namespace: str
    file_path: Path
    source_code: str
    methods: List[Dict[str, Any]]
    dependencies: List[str]
    metadata: Dict[str, Any]  # Language-specific metadata

class BaseLanguageHandler(ABC):
    """Abstract base class for language handlers"""

    @abstractmethod
    def get_file_extensions(self) -> List[str]:
        """Return supported file extensions (e.g., ['.cs', '.csx'])"""
        pass

    @abstractmethod
    def detect_files(self, path: Path, pattern: Optional[str] = None) -> List[Path]:
        """Find all testable files in directory"""
        pass

    @abstractmethod
    def parse_class(self, file_path: Path) -> Optional[ClassInfo]:
        """Parse source file and extract class information"""
        pass

    @abstractmethod
    def generate_test_prompt(self, class_info: ClassInfo, patterns: Dict[str, Any]) -> str:
        """Generate AI prompt for test generation"""
        pass

    @abstractmethod
    def get_test_framework(self) -> str:
        """Return test framework name (e.g., 'xunit', 'jest', 'junit')"""
        pass

    @abstractmethod
    def get_test_file_path(self, source_path: Path, output_dir: Path) -> Path:
        """Determine output path for test file"""
        pass

    @abstractmethod
    def auto_fix_syntax(self, code: str) -> tuple[str, List[str], List[str]]:
        """
        Auto-fix common syntax issues
        Returns: (fixed_code, warnings, errors)
        """
        pass
```

---

## 🔧 Implementation Steps

### Phase 1: Core Infrastructure (Day 1)

- [x] Create directory structure
- [ ] Implement `providers/base_provider.py`
- [ ] Implement `languages/base_language.py`
- [ ] Implement `core/orchestrator.py`
- [ ] Implement `patterns/pattern_cache.py` (extract from generate_tests.py)
- [ ] Create unit tests for base classes

**Time**: 4-6 hours

### Phase 2: Provider Migration (Day 1-2)

- [ ] Implement `providers/openai_provider.py`
  - Extract existing OpenAI logic from generate_tests.py
  - Add proper error handling
  - Add retry logic with exponential backoff
  - Test with RemoteC project

- [ ] Implement `providers/claude_provider.py`
  - Install `anthropic` SDK
  - Use Claude 3.5 Haiku model
  - Test cost savings (74% reduction)

- [ ] Implement `providers/gemini_provider.py`
  - Install `google-generativeai` SDK
  - Use Gemini 2.0 Flash model
  - Test cost savings (97% reduction)

**Time**: 6-8 hours

### Phase 3: Language Handler Migration (Day 2-3)

- [ ] Implement `languages/csharp_language.py`
  - Extract C# parsing logic from generate_tests.py
  - Move regex patterns
  - Move prompt generation logic
  - Test with RemoteC project (44 controllers)

- [ ] Implement `languages/vbnet_language.py`
  - Extract VB.NET logic from generate_tests_vbnet.py
  - Unify with C# handler where possible
  - Test with PaymentAPI project

**Time**: 6-8 hours

### Phase 4: CLI Integration (Day 3)

- [ ] Refactor `generate_tests.py` to use new architecture
  - Add `--provider` flag: `openai|claude|gemini|openrouter`
  - Add `--language` flag: `csharp|vbnet`
  - Add cost comparison in `--dry-run` mode
  - Maintain backward compatibility

- [ ] Update `.env.template` with new provider keys:
  ```bash
  # OpenAI (existing)
  OPENAI_API_KEY=sk-...

  # Anthropic Claude (NEW)
  ANTHROPIC_API_KEY=sk-ant-...

  # Google Gemini (NEW)
  GOOGLE_API_KEY=...

  # OpenRouter (NEW)
  OPENROUTER_API_KEY=sk-or-...
  ```

**Time**: 3-4 hours

### Phase 5: Testing & Validation (Day 4)

- [ ] Create comprehensive test suite
  - Unit tests for each provider
  - Unit tests for each language handler
  - Integration tests for full workflow
  - Cost calculation tests

- [ ] Run validation tests
  - RemoteC project (C#, 44 controllers)
  - PaymentAPI project (VB.NET)
  - Compare costs across providers
  - Verify pattern learning still works

**Time**: 4-6 hours

### Phase 6: Documentation (Day 4)

- [ ] Update CLAUDE.md with new architecture
- [ ] Update README.md with provider options
- [ ] Create ARCHITECTURE.md (detailed design doc)
- [ ] Update TODO.md (mark P1 tasks complete)
- [ ] Add provider comparison table to docs

**Time**: 2-3 hours

---

## 📊 Expected Results

### Cost Comparison (RemoteC Project - 44 files, ~113K tokens)

| Provider | Model | Input Cost | Output Cost | Total | Savings |
|----------|-------|------------|-------------|-------|---------|
| OpenAI | GPT-4 Turbo | $0.01/1K | $0.03/1K | **$1.73** | Baseline |
| OpenAI | GPT-3.5 Turbo | $0.0005/1K | $0.0015/1K | **$0.09** | 95% |
| Anthropic | Claude 3.5 Haiku | $0.0008/1K | $0.004/1K | **$0.45** | 74% |
| Google | Gemini 2.0 Flash | $0.0001/1K | $0.0004/1K | **$0.05** | 97% |
| Google | Gemini Flash-Lite | $0.00002/1K | $0.00008/1K | **$0.01** | 99% |

### Quality Comparison

Need to validate that cheaper models maintain quality:

| Provider | Compilation Errors | Pattern Learning | Notes |
|----------|-------------------|------------------|-------|
| GPT-4 Turbo | 266 baseline | 15 patterns | Current baseline |
| Claude Haiku | TBD | TBD | Test required |
| Gemini Flash | TBD | TBD | Test required |

**Validation Strategy**:
1. Generate same 44 RemoteC tests with each provider
2. Compile and count errors
3. Run pattern learner
4. Compare quality vs cost

---

## 🚀 Migration Strategy

### Backward Compatibility

Keep existing `generate_tests.py` working during migration:

```python
# Old command (still works)
python generate_tests.py /path/to/project

# New command with provider selection
python generate_tests.py /path/to/project --provider claude

# New command with language specification
python generate_tests.py /path/to/project --language vbnet --provider gemini
```

### Gradual Rollout

1. **Week 1**: Refactor to new architecture, maintain existing behavior
2. **Week 2**: Add new providers, test quality
3. **Week 3**: Add new language handlers
4. **Week 4**: Deprecate old code paths

---

## 🧪 Testing Strategy

### Unit Tests

```python
# tests/test_providers.py
def test_openai_provider_completion():
    provider = OpenAIProvider(api_key="test")
    request = CompletionRequest(prompt="test", max_tokens=100)
    response = provider.generate_completion(request)
    assert response.content is not None
    assert response.cost > 0

# tests/test_languages.py
def test_csharp_parse_class():
    handler = CSharpLanguageHandler()
    class_info = handler.parse_class(Path("test.cs"))
    assert class_info.name == "TestController"
    assert len(class_info.methods) > 0
```

### Integration Tests

```python
# tests/test_integration.py
def test_full_workflow_with_claude():
    # Test complete generation workflow with Claude provider
    result = generate_tests(
        project_dir="/path/to/test/project",
        provider="claude",
        language="csharp"
    )
    assert result.files_generated == 5
    assert result.cost < 0.50  # Should be cheaper than OpenAI
```

---

## 📝 Commit Strategy

### Commit Pattern

Each phase gets its own commit:

```bash
# Phase 1
git commit -m "🏗️ Add base infrastructure (providers, languages, orchestrator)"

# Phase 2
git commit -m "✨ Add multi-provider support (OpenAI, Claude, Gemini)"

# Phase 3
git commit -m "♻️ Refactor language handlers (C#, VB.NET)"

# Phase 4
git commit -m "🔧 Update CLI with provider/language selection"

# Phase 5
git commit -m "✅ Add comprehensive test suite"

# Phase 6
git commit -m "📚 Update documentation for modular architecture"
```

### Merge to Master

After all phases complete and tests pass:

```bash
git checkout master
git merge refactor/modular-architecture
git tag v1.1
git push origin master --tags
```

---

## 🎯 Success Criteria

Project considered successful when:

- [x] v1.0 tag created (baseline)
- [x] Refactor branch created
- [ ] All existing tests pass
- [ ] RemoteC project generates same 44 files
- [ ] Pattern learning works (15 patterns cached)
- [ ] Cost reduced by 74%+ with Claude
- [ ] Cost reduced by 97%+ with Gemini
- [ ] Unit test coverage >80%
- [ ] Documentation updated
- [ ] CLI maintains backward compatibility
- [ ] Ready to add Java/Python/TypeScript with minimal effort

---

## 📅 Timeline

**Estimated Duration**: 4 days (full-time) or 2 weeks (part-time)

- **Day 1**: Phases 1-2 (infrastructure + providers)
- **Day 2**: Phase 3 (language handlers)
- **Day 3**: Phases 4-5 (CLI + testing)
- **Day 4**: Phase 6 (documentation + merge)

**Start Date**: October 25, 2025
**Target Completion**: November 1, 2025 (if full-time)

---

## 🔗 References

- **Baseline Code**: v1.0 tag
- **TODO.md**: P1 tasks (multi-provider + modular language)
- **IMPLEMENTATION-GUIDE.md**: Lines 54-182 (base architecture)
- **UNIVERSAL-TEST-GENERATOR-PLAN.md**: Long-term vision

---

**Created**: October 25, 2025
**Status**: In Progress - Phase 1
**Branch**: `refactor/modular-architecture`
**Baseline**: v1.0
