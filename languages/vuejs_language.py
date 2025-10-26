"""
Vue.js Language Handler

Provides Vue.js-specific parsing and test generation with Vitest
"""

import re
from pathlib import Path
from typing import Optional, List, Dict, Any
import json

from .base_language import (
    BaseLanguageHandler,
    ClassInfo,
    MethodInfo
)


class VueJSLanguageHandler(BaseLanguageHandler):
    """
    Vue.js language handler with Vitest support

    Supports:
    - Vue 3 Composition API and Options API
    - TypeScript and JavaScript
    - Vitest + Vue Test Utils
    - Component props, emits, and slots testing
    - Composable testing
    - Pinia store testing
    """

    def get_file_extensions(self) -> List[str]:
        """Return Vue.js file extensions"""
        return ['.vue', '.ts', '.js']

    def get_test_file_extension(self) -> str:
        """Return test file extension"""
        return '.test.ts'

    def get_test_framework_default(self) -> str:
        """Return default test framework (Vitest)"""
        return 'vitest'

    def detect_files(self, project_dir: Path, pattern: Optional[str] = None) -> List[Path]:
        """
        Find all Vue.js component and composable files

        Args:
            project_dir: Project directory to search
            pattern: Optional regex pattern to filter files

        Returns:
            List of Vue.js file paths
        """
        vue_files = []

        # Find .vue files (components)
        for vue_file in project_dir.rglob('*.vue'):
            # Skip test files, node_modules, dist
            if any(exclude in str(vue_file) for exclude in ['node_modules', 'dist', '.test', '.spec', 'test', '__tests__']):
                continue

            # If pattern specified, check if component name matches
            if pattern:
                component_name = self._extract_component_name(vue_file)
                if component_name and not re.search(pattern, component_name):
                    continue

            vue_files.append(vue_file)

        # Find composables (.ts/.js files in composables directory)
        for composable_dir in ['composables', 'hooks', 'use']:
            for ts_file in project_dir.rglob(f'{composable_dir}/*.ts'):
                if 'node_modules' not in str(ts_file) and '.test' not in str(ts_file):
                    vue_files.append(ts_file)

        return sorted(vue_files, key=lambda p: p.name)

    def _extract_component_name(self, file_path: Path) -> Optional[str]:
        """Extract component name from Vue file"""
        # Try from filename
        name = file_path.stem
        if name not in ['index', 'Index']:
            return name

        # Try from <script> block
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            # Look for: export default { name: 'ComponentName' }
            name_match = re.search(r'name:\s*[\'"](\w+)[\'"]', content)
            if name_match:
                return name_match.group(1)
        except:
            pass

        return file_path.stem

    def parse_class(self, file_path: Path) -> Optional[ClassInfo]:
        """
        Parse Vue.js component or composable

        Args:
            file_path: Path to Vue.js file

        Returns:
            ClassInfo object or None if parsing fails
        """
        try:
            source_code = file_path.read_text(encoding='utf-8', errors='ignore')

            # Determine if this is a component or composable
            is_component = file_path.suffix == '.vue'

            if is_component:
                return self._parse_component(file_path, source_code)
            else:
                return self._parse_composable(file_path, source_code)

        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None

    def _parse_component(self, file_path: Path, source_code: str) -> Optional[ClassInfo]:
        """Parse Vue.js component"""
        component_name = self._extract_component_name(file_path)
        if not component_name:
            return None

        # Extract script content
        script_match = re.search(r'<script[^>]*>(.*?)</script>', source_code, re.DOTALL)
        script_content = script_match.group(1) if script_match else ''

        # Determine API style (Composition vs Options)
        is_composition_api = 'setup(' in script_content or '<script setup' in source_code

        # Extract props
        props = self._extract_props(script_content, is_composition_api)

        # Extract emits
        emits = self._extract_emits(script_content, is_composition_api)

        # Extract methods/functions
        methods = self._extract_methods(script_content, is_composition_api)

        # Extract composables used
        dependencies = self._extract_composables(script_content)

        # Build metadata
        metadata = {
            'api_style': 'composition' if is_composition_api else 'options',
            'props': props,
            'emits': emits,
            'has_slots': '<slot' in source_code,
            'has_template': '<template' in source_code
        }

        return ClassInfo(
            name=component_name,
            namespace=str(file_path.parent.relative_to(file_path.parent.parent.parent)),
            file_path=file_path,
            source_code=source_code,
            methods=methods,
            dependencies=dependencies,
            is_controller=False,
            is_service=False,
            language='vuejs',
            metadata=metadata
        )

    def _parse_composable(self, file_path: Path, source_code: str) -> Optional[ClassInfo]:
        """Parse Vue.js composable (hook)"""
        # Extract function name (e.g., useAuth, useCounter)
        function_match = re.search(r'export\s+(?:const|function)\s+(\w+)', source_code)
        if not function_match:
            return None

        function_name = function_match.group(1)

        # Extract methods
        methods = self._extract_methods(source_code, is_composition_api=True)

        # Extract dependencies (other composables)
        dependencies = self._extract_composables(source_code)

        metadata = {
            'is_composable': True,
            'returns_ref': 'ref(' in source_code or 'reactive(' in source_code,
            'returns_computed': 'computed(' in source_code
        }

        return ClassInfo(
            name=function_name,
            namespace=str(file_path.parent.relative_to(file_path.parent.parent)),
            file_path=file_path,
            source_code=source_code,
            methods=methods,
            dependencies=dependencies,
            is_controller=False,
            is_service=True,
            language='vuejs',
            metadata=metadata
        )

    def _extract_props(self, script_content: str, is_composition_api: bool) -> List[Dict[str, str]]:
        """Extract component props"""
        props = []

        if is_composition_api:
            # defineProps<{ name: string, age: number }>()
            props_match = re.search(r'defineProps<\{([^}]+)\}>', script_content)
            if props_match:
                props_str = props_match.group(1)
                for prop in props_str.split(','):
                    prop = prop.strip()
                    if ':' in prop:
                        name, type_str = prop.split(':', 1)
                        props.append({'name': name.strip(), 'type': type_str.strip()})
        else:
            # props: { name: String, age: Number }
            props_match = re.search(r'props:\s*\{([^}]+)\}', script_content)
            if props_match:
                props_str = props_match.group(1)
                for prop in props_str.split(','):
                    prop = prop.strip()
                    if ':' in prop:
                        name, type_str = prop.split(':', 1)
                        props.append({'name': name.strip(), 'type': type_str.strip()})

        return props

    def _extract_emits(self, script_content: str, is_composition_api: bool) -> List[str]:
        """Extract component emits"""
        emits = []

        if is_composition_api:
            # defineEmits<{ (e: 'update', value: string): void }>()
            # or defineEmits(['update', 'delete'])
            emits_match = re.search(r'defineEmits\[([^\]]+)\]', script_content)
            if emits_match:
                emits_str = emits_match.group(1)
                emits = [e.strip().strip("'\"") for e in emits_str.split(',')]
        else:
            # emits: ['update', 'delete']
            emits_match = re.search(r'emits:\s*\[([^\]]+)\]', script_content)
            if emits_match:
                emits_str = emits_match.group(1)
                emits = [e.strip().strip("'\"") for e in emits_str.split(',')]

        return emits

    def _extract_methods(self, script_content: str, is_composition_api: bool) -> List[MethodInfo]:
        """Extract methods/functions"""
        methods = []

        if is_composition_api:
            # const handleClick = () => { }
            # function handleSubmit() { }
            function_pattern = r'(?:const|function)\s+(\w+)\s*[=:]\s*(?:async\s+)?\([^)]*\)\s*(?::\s*\w+)?\s*(?:=>|\{)'
            for match in re.finditer(function_pattern, script_content):
                method_name = match.group(1)
                is_async = 'async' in match.group(0)
                methods.append(MethodInfo(
                    name=method_name,
                    return_type='void',
                    parameters=[],
                    is_async=is_async,
                    is_public=True
                ))
        else:
            # methods: { handleClick() { }, async handleSubmit() { } }
            methods_block_match = re.search(r'methods:\s*\{([^}]+)\}', script_content, re.DOTALL)
            if methods_block_match:
                methods_block = methods_block_match.group(1)
                for match in re.finditer(r'(async\s+)?(\w+)\s*\([^)]*\)', methods_block):
                    is_async = match.group(1) is not None
                    method_name = match.group(2)
                    methods.append(MethodInfo(
                        name=method_name,
                        return_type='void',
                        parameters=[],
                        is_async=is_async,
                        is_public=True
                    ))

        return methods

    def _extract_composables(self, script_content: str) -> List[str]:
        """Extract used composables (dependencies)"""
        composables = []

        # Find all use* function calls
        for match in re.finditer(r'(use\w+)\s*\(', script_content):
            composable = match.group(1)
            if composable not in composables:
                composables.append(composable)

        return composables

    def generate_test_prompt(
        self,
        class_info: ClassInfo,
        patterns: Dict[str, Any],
        test_framework: str = 'vitest',
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate AI prompt for Vue.js test generation

        Args:
            class_info: Parsed component/composable information
            patterns: Learned patterns
            test_framework: Test framework (vitest, jest)
            context: Additional context

        Returns:
            Formatted prompt string
        """
        metadata = class_info.metadata
        is_component = not metadata.get('is_composable', False)

        if is_component:
            return self._generate_component_test_prompt(class_info, test_framework)
        else:
            return self._generate_composable_test_prompt(class_info, test_framework)

    def _generate_component_test_prompt(self, class_info: ClassInfo, test_framework: str) -> str:
        """Generate prompt for Vue component testing"""
        metadata = class_info.metadata
        props = metadata.get('props', [])
        emits = metadata.get('emits', [])
        api_style = metadata.get('api_style', 'composition')

        props_str = '\n'.join([f"  - {p['name']}: {p['type']}" for p in props]) if props else '  None'
        emits_str = '\n'.join([f"  - {e}" for e in emits]) if emits else '  None'

        prompt = f"""Generate comprehensive Vitest unit tests for the following Vue.js component.

**Component:** {class_info.name}
**API Style:** {api_style.upper()}

**Source Code:**
```vue
{class_info.source_code}
```

**Component Details:**
- Name: {class_info.name}
- Props:
{props_str}
- Emits:
{emits_str}
- Methods: {len(class_info.methods)}
- Composables Used: {', '.join(class_info.dependencies) if class_info.dependencies else 'None'}

**Test Requirements:**
1. Use Vitest + @vue/test-utils
2. Test component rendering with various prop combinations
3. Test all user interactions (clicks, inputs, etc.)
4. Test emitted events
5. Test computed properties and watchers
6. Mock all external composables and API calls
7. Test slots if present
8. Test lifecycle hooks if applicable

**Required Imports:**
```typescript
import {{ describe, it, expect, vi, beforeEach }} from 'vitest'
import {{ mount }} from '@vue/test-utils'
import {class_info.name} from './{class_info.file_path.stem}'
```

**Example Test Structure:**
```typescript
describe('{class_info.name}', () => {{
  it('renders properly with required props', () => {{
    const wrapper = mount({class_info.name}, {{
      props: {{
        // prop values here
      }}
    }})

    expect(wrapper.exists()).toBe(true)
    expect(wrapper.text()).toContain('expected text')
  }})

  it('emits event when button clicked', async () => {{
    const wrapper = mount({class_info.name})
    await wrapper.find('button').trigger('click')

    expect(wrapper.emitted('event-name')).toBeTruthy()
    expect(wrapper.emitted('event-name')?.[0]).toEqual(['expected-value'])
  }})

  it('updates computed property when data changes', async () => {{
    const wrapper = mount({class_info.name})
    // Test computed property logic
  }})
}})
```

Generate the complete test file now:"""

        return prompt

    def _generate_composable_test_prompt(self, class_info: ClassInfo, test_framework: str) -> str:
        """Generate prompt for composable testing"""
        prompt = f"""Generate comprehensive Vitest unit tests for the following Vue.js composable.

**Composable:** {class_info.name}

**Source Code:**
```typescript
{class_info.source_code}
```

**Composable Details:**
- Name: {class_info.name}
- Methods/Functions: {len(class_info.methods)}
- Dependencies: {', '.join(class_info.dependencies) if class_info.dependencies else 'None'}

**Test Requirements:**
1. Use Vitest for testing
2. Test all exported functions
3. Test reactive state updates
4. Test computed properties
5. Test side effects
6. Mock external dependencies

**Required Imports:**
```typescript
import {{ describe, it, expect, vi, beforeEach }} from 'vitest'
import {{ {class_info.name} }} from './{class_info.file_path.stem}'
```

**Example Test Structure:**
```typescript
describe('{class_info.name}', () => {{
  it('initializes with default values', () => {{
    const {{ state, method }} = {class_info.name}()

    expect(state.value).toBeDefined()
  }})

  it('updates state when method called', () => {{
    const {{ state, updateState }} = {class_info.name}()

    updateState('new value')

    expect(state.value).toBe('new value')
  }})

  it('handles async operations', async () => {{
    const {{ fetchData }} = {class_info.name}()

    await fetchData()

    expect(/* assertion here */).toBeTruthy()
  }})
}})
```

Generate the complete test file now:"""

        return prompt

    def auto_fix_syntax(self, test_code: str, class_info: ClassInfo) -> str:
        """
        Auto-fix common Vue.js test syntax issues

        Args:
            test_code: Generated test code
            class_info: Original component/composable info

        Returns:
            Fixed test code
        """
        fixed_code = test_code

        # Ensure proper imports
        if 'vitest' not in fixed_code:
            fixed_code = "import { describe, it, expect, vi, beforeEach } from 'vitest'\n" + fixed_code

        if '@vue/test-utils' not in fixed_code and class_info.metadata.get('is_composable') is False:
            fixed_code = "import { mount } from '@vue/test-utils'\n" + fixed_code

        return fixed_code

    def get_test_class_name(self, class_name: str) -> str:
        """Generate test file name"""
        return f"{class_name}.test"

    def get_test_namespace(self, namespace: str) -> str:
        """Return test directory (same as source for Vue.js)"""
        return namespace
