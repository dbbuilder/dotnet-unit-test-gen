# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is an **AI-powered unit test generator** with self-learning pattern discovery. It generates xUnit tests for .NET projects and learns from compilation errors to improve accuracy over time.

**Key Innovation**: The pattern learning system automatically discovers project-specific patterns (property names, return types, enum values) by analyzing compilation errors, reducing errors by 30-40% on subsequent runs.

**Production Status**: ✅ Fully operational (validated Oct 2025 on RemoteC project - 44 test files, $2.23 cost)

## Core Architecture

### Main Components

1. **generate_tests.py** (29KB) - Main test generator
   - Analyzes .NET source files using regex parsing
   - Uses LiteLLM for OpenAI API calls with GPT-4/GPT-3.5
   - Implements cost optimization (cheaper models for simple classes)
   - Loads cached patterns from `ProjectPatternCache`
   - Generates xUnit tests with Moq and FluentAssertions

2. **langchain_pattern_learner_v1.py** (15KB) - LangChain 1.0 pattern learner
   - Creates ReAct agent with 4 tools: compile_tests, analyze_error_pattern, seed_pattern, get_error_details
   - Compiles generated tests with `dotnet build`
   - Parses MSBuild errors (CS#### codes)
   - Automatically categorizes patterns: property_name, return_type, enum_values, hint
   - Seeds patterns into cache for next generation

3. **add_pattern.py** (1.6KB) - Manual pattern seeding utility
   - CLI helper for manually adding patterns to cache
   - Useful for one-off corrections before pattern learner

4. **ProjectPatternCache** (in generate_tests.py) - Pattern persistence system
   - Cache location: `.test-gen-cache/{project_hash}/patterns.json`
   - Project hash: MD5 of absolute project path (12 chars)
   - Stores patterns as JSON with type, context, value, confidence, last_seen
   - Automatically loads patterns during test generation

### Key Data Structures

```python
@dataclass
class ClassInfo:
    name: str
    namespace: str
    file_path: Path
    source_code: str
    methods: List[str]
    dependencies: List[str]
    is_controller: bool
    is_service: bool

@dataclass
class ProjectPattern:
    pattern_type: str  # 'return_type', 'enum_value', 'property_name', 'hint'
    context: str       # e.g., 'IDeviceRepository.GetUserDevicesAsync'
    value: str         # e.g., 'DataPagedResult<DeviceDto>'
    confidence: float  # 1.0 by default
    last_seen: str     # ISO timestamp
```

## Common Development Commands

### Environment Setup

```bash
# Initial setup
./setup.sh

# Or manually:
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.template .env
# Edit .env and add OPENAI_API_KEY
```

### Standard Test Generation

```bash
# Activate environment (required for all commands)
source venv/bin/activate

# Dry run (analyze only, no generation)
python generate_tests.py /path/to/project --dry-run

# Generate tests for controllers
python generate_tests.py /path/to/project -o /path/to/tests -p "Controller"

# Generate tests for specific class
python generate_tests.py /path/to/project -o /path/to/tests -p "SessionsController" --force

# Limit to 5 classes (useful for testing)
python generate_tests.py /path/to/project -n 5

# Force overwrite existing tests
python generate_tests.py /path/to/project --force
```

### Two-Phase Workflow (Generate → Learn → Regenerate)

```bash
# Phase 1: Initial generation
python generate_tests.py /path/to/project -o /path/to/tests -p "Controller"

# Phase 2: Learn patterns from compilation errors
python langchain_pattern_learner_v1.py /path/to/project /path/to/tests

# Phase 3: Regenerate with learned patterns (30-40% fewer errors)
python generate_tests.py /path/to/project -o /path/to/tests -p "Controller" --force
```

### Manual Pattern Management

```bash
# Add return type pattern
python add_pattern.py /path/to/project return_type \
  'IDeviceRepository.GetUserDevicesAsync' \
  'DataPagedResult<DeviceDto>'

# Add enum values
python add_pattern.py /path/to/project enum_values \
  'ConnectionType' \
  'P2P,Relay,Direct'

# Add property name correction
python add_pattern.py /path/to/project property_name \
  'ClipboardContent.Content' \
  'Data'

# Add general hint
python add_pattern.py /path/to/project hint \
  'Use DataPagedResult not PagedResult for repository returns' \
  'check IDeviceRepository, ISessionRepository'
```

### Pattern Cache Management

```bash
# View cached patterns for a project
cat .test-gen-cache/{project_hash}/patterns.json

# Find project hash
ls -la .test-gen-cache/

# View project info
cat .test-gen-cache/{project_hash}/project-info.json

# Clear cache for project (forces relearning)
rm -rf .test-gen-cache/{project_hash}/
```

## Universal Test Generator Expansion (Planned)

**Status**: Planning complete (Oct 2025), implementation not started

The repository is planned to expand beyond .NET to become a **Universal Test Generator** supporting:

1. **Jest Generator** (Phase 1) - JavaScript/TypeScript/Vue.js unit tests
2. **API Integration Generator** (Phase 2) - REST API endpoint validation
3. **Database Generator** (Phase 3) - Repository/SQL testing
4. **Playwright Generator** (Phase 4) - E2E browser testing

**Planning Documents**:
- `docs/UNIVERSAL-TEST-GENERATOR-PLAN.md` - Overall vision
- `docs/IMPLEMENTATION-GUIDE.md` - 15-day implementation roadmap
- `docs/modules/*.md` - Individual module specifications

**Architecture Design**:
- `BaseTestGenerator` abstract class (not yet implemented)
- `BasePatternLearner` for cross-language pattern learning
- Jinja2 template system for test scaffolding
- Shared `.test-gen-cache/` for all generators

**Cost Estimates** (for ecommerce-app + PaymentAPI):
- Jest: 45 components @ $0.57
- API Integration: 15 endpoints @ $0.31
- Database: 18 classes/procs @ $0.42
- Playwright: 11 pages/flows @ $0.52
- **Total**: 89 test files @ $1.82

## Important Technical Details

### LangChain 1.0 Migration (Completed Oct 2025)

The pattern learner uses **LangChain 1.0** API (breaking changes from 0.x):

```python
# New API (used in langchain_pattern_learner_v1.py)
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

@tool
def compile_tests(query: str = "") -> str:
    """Tool docstring becomes description"""
    return result

agent = create_react_agent(llm, tools=[compile_tests, ...])
```

**Migration Notes**:
- `@tool` decorator replaces `Tool(name=..., func=..., description=...)`
- `create_react_agent()` replaces `initialize_agent()`
- Recursion limit increased to 100 (was 50) to handle complex error analysis

### Source Code Analysis (Pure Python)

The generator does **NOT** use Roslyn or any .NET libraries. It parses C# using regex:

```python
# Pattern examples from generate_tests.py
CLASS_PATTERN = r'public\s+(?:sealed\s+)?(?:partial\s+)?(?:abstract\s+)?class\s+(\w+)'
METHOD_PATTERN = r'public\s+(?:async\s+)?(?:virtual\s+)?(?:override\s+)?(?:Task<?[\w<>]+>?|IActionResult|ActionResult<[\w<>]+>|void|[\w<>]+)\s+(\w+)\s*\('
DEPENDENCY_PATTERN = r'private\s+readonly\s+(I\w+)'
```

**Why**: Avoids .NET runtime dependency, works on Linux/Mac/Windows, faster startup

**Limitation**: Cannot resolve complex type inference or cross-project references (hence pattern learning)

### Cost Optimization Strategy

**Model Selection** (configurable in `.env`):
- **GPT-4 Turbo** (`PRIMARY_MODEL`): Complex classes (>3 methods or >2 dependencies)
- **GPT-3.5 Turbo** (`SIMPLE_MODEL`): Simple classes (≤3 methods, ≤2 dependencies)
- **GPT-3.5 Turbo** (`FALLBACK_MODEL`): Automatic fallback if primary fails

**Token Optimization**:
- Include only relevant source code in prompt
- Use structured output format (reduces parsing tokens)
- Cache patterns to reduce regeneration needs

**Rate Limiting** (`.env`):
- `MAX_REQUESTS_PER_MINUTE=50` - Avoid OpenAI rate limits
- `RETRY_ATTEMPTS=3` - Exponential backoff on failures

### Pattern Learning Mechanics

**Error Compilation**:
```bash
cd /path/to/tests
dotnet build 2>&1 | tee build.log
# Parses: "File.cs(123,45): error CS0117: 'Type' does not contain 'Property'"
```

**Pattern Discovery** (automatic in langchain_pattern_learner_v1.py):
1. Compile tests → capture errors
2. Group by error code (CS0117, CS0246, CS0029, etc.)
3. LLM analyzes error patterns → categorizes
4. Seed patterns → save to cache
5. Regenerate → reduced errors

**Pattern Categories**:
- `property_name`: Wrong property used (e.g., Content vs Data)
- `return_type`: Wrong type in test mock (e.g., PagedResult vs DataPagedResult)
- `enum_values`: Invalid enum value used (needs comma-separated list)
- `hint`: General guidance for test generation (freeform text)

### Dependencies and Versions

**Critical**: Uses LangChain 1.0 (multiple packages):
```
langchain==1.0.2
langchain-classic==1.0.0
langchain-community==0.4
langchain-core==1.0.0
langchain-openai==1.0.1
langchain-text-splitters==1.0.0
```

**LiteLLM** for multi-provider support:
```
litellm>=1.30.0
openai>=1.12.0  # Used via LiteLLM
```

**UI/UX**:
```
rich>=13.7.0     # Terminal formatting
click>=8.1.7     # CLI argument parsing
```

## File Organization

```
dotnet-unit-test-gen/
├── generate_tests.py              # Main generator (standard workflow)
├── langchain_pattern_learner_v1.py # LangChain agent (auto pattern learning)
├── add_pattern.py                 # Manual pattern helper
├── generate_tests_vbnet.py        # VB.NET support (experimental)
├── generate_tests_enhanced*.py    # Enhanced variants (experimental)
├── langchain_*.py                 # Other LangChain modules (in progress)
├── .test-gen-cache/              # Pattern cache (not in git)
│   └── {project_hash}/
│       ├── patterns.json         # Learned patterns
│       └── project-info.json     # Metadata
├── docs/
│   ├── guides/
│   │   ├── QUICKSTART.md
│   │   └── TWO-PHASE-WORKFLOW.md
│   ├── langchain/
│   │   ├── LANGCHAIN-TEST-RESULTS.md      # RemoteC case study
│   │   └── LANGCHAIN-V1-UPDATE-COMPLETE.md
│   ├── modules/                   # Universal generator specs (planned)
│   │   ├── JEST-GENERATOR-SPEC.md
│   │   ├── API-INTEGRATION-GENERATOR-SPEC.md
│   │   ├── DATABASE-GENERATOR-SPEC.md
│   │   └── PLAYWRIGHT-GENERATOR-SPEC.md
│   ├── UNIVERSAL-TEST-GENERATOR-PLAN.md   # Future expansion plan
│   └── IMPLEMENTATION-GUIDE.md            # 15-day roadmap
├── site/                         # Marketing site (static HTML)
├── setup.sh                      # Environment setup script
├── example_usage.sh              # Usage examples
├── requirements.txt              # Python dependencies
└── .env.template                 # Environment configuration template
```

## Troubleshooting

### "OPENAI_API_KEY not found"
- Create `.env` from `.env.template`
- Add `OPENAI_API_KEY=sk-...`

### Rate limit errors
- Reduce `MAX_REQUESTS_PER_MINUTE` in `.env`
- Use `--dry-run` to test without API calls
- Use `-n 5` to limit generation during testing

### Pattern learner recursion limit
- Increase in `langchain_pattern_learner_v1.py`: `agent_executor.invoke(..., recursion_limit=100)`
- Default is 100 (sufficient for most projects)

### Wrong patterns cached
- Delete cache: `rm -rf .test-gen-cache/{project_hash}/`
- Regenerate: `python generate_tests.py ... --force`
- Review patterns: `cat .test-gen-cache/{project_hash}/patterns.json`

### Compilation errors in generated tests
- **Expected**: First run typically has project-specific errors
- **Solution**: Run pattern learner → regenerate
- **Target**: 30-40% error reduction after pattern learning
- **Reality**: May need 2-3 learning cycles for complex projects

## Key Success Metrics (RemoteC Case Study)

- **Files**: 44 test files generated
- **Time**: ~5 minutes generation + ~3 minutes pattern learning
- **Cost**: $1.73 generation + $0.50 learning = $2.23 total
- **Patterns**: 15 discovered (12 automatic + 3 manual)
- **Errors**: 266 baseline → 160-185 after learning (30-40% reduction)
- **ROI**: $25-33 value per run (at $100/hr developer rate)

## Future Development Notes

When implementing the Universal Test Generator expansion:

1. **Create base classes first**: `BaseTestGenerator`, `BasePatternLearner`, `BaseAnalyzer`
2. **Refactor existing .NET generator** to inherit from base classes
3. **Implement Jest generator** (Phase 1) using same architecture
4. **Test pattern learning** on JavaScript/TypeScript errors
5. **Share cache structure** across all generators in `.test-gen-cache/`
6. **Use Jinja2 templates** for test scaffolding (replace string formatting)

**Recommended implementation order**:
1. Base abstraction layer (2 days)
2. Jest generator (3 days)
3. API integration generator (3 days)
4. Database generator (4 days)
5. Playwright E2E generator (5 days)

**Total**: 15 days to production-ready universal generator

See `docs/IMPLEMENTATION-GUIDE.md` for detailed daily tasks.
