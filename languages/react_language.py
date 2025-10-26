"""
React Language Handler

Provides React component and hook testing with Jest + React Testing Library
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


class ReactLanguageHandler(BaseLanguageHandler):
    """
    React language handler with Jest + React Testing Library

    Supports:
    - React functional components (hooks-based)
    - React class components
    - Custom hooks
    - TypeScript and JavaScript
    - Jest + React Testing Library
    - Redux/Context testing
    """

    def get_file_extensions(self) -> List[str]:
        """Return React file extensions"""
        return ['.jsx', '.tsx', '.js', '.ts']

    def get_test_file_extension(self) -> str:
        """Return test file extension"""
        return '.test.tsx'

    def get_test_framework_default(self) -> str:
        """Return default test framework (Jest)"""
        return 'jest'

    def detect_files(self, project_dir: Path, pattern: Optional[str] = None) -> List[Path]:
        """
        Find all React component and hook files

        Args:
            project_dir: Project directory to search
            pattern: Optional regex pattern to filter files

        Returns:
            List of React file paths
        """
        react_files = []

        # Find React component files
        for ext in ['.jsx', '.tsx']:
            for react_file in project_dir.rglob(f'*{ext}'):
                # Skip test files, node_modules, build, dist
                if any(exclude in str(react_file) for exclude in ['node_modules', 'build', 'dist', '.test', '.spec', '__tests__', '__mocks__']):
                    continue

                # Check if file contains React code
                try:
                    content = react_file.read_text(encoding='utf-8', errors='ignore')
                    if self._is_react_file(content):
                        # If pattern specified, check if component name matches
                        if pattern:
                            component_name = self._extract_component_name(content, react_file)
                            if component_name and not re.search(pattern, component_name):
                                continue

                        react_files.append(react_file)
                except:
                    continue

        # Find custom hooks
        for hook_dir in ['hooks', 'customHooks', 'use']:
            for ts_file in project_dir.rglob(f'{hook_dir}/*.ts'):
                if 'node_modules' not in str(ts_file) and '.test' not in str(ts_file):
                    react_files.append(ts_file)
            for tsx_file in project_dir.rglob(f'{hook_dir}/*.tsx'):
                if 'node_modules' not in str(tsx_file) and '.test' not in str(tsx_file):
                    react_files.append(tsx_file)

        return sorted(react_files, key=lambda p: p.name)

    def _is_react_file(self, content: str) -> bool:
        """Check if file contains React code"""
        react_indicators = [
            'import React',
            'from \'react\'',
            'from "react"',
            'useState',
            'useEffect',
            'useContext',
            'Component',
            'return <',
            'return (<'
        ]
        return any(indicator in content for indicator in react_indicators)

    def _extract_component_name(self, content: str, file_path: Path) -> Optional[str]:
        """Extract component name from React file"""
        # Try from export: export default ComponentName
        export_match = re.search(r'export\s+default\s+(\w+)', content)
        if export_match:
            return export_match.group(1)

        # Try from function: function ComponentName() or const ComponentName = ()
        func_match = re.search(r'(?:function|const)\s+(\w+)\s*[=:]', content)
        if func_match:
            return func_match.group(1)

        # Fallback to filename
        return file_path.stem

    def parse_class(self, file_path: Path) -> Optional[ClassInfo]:
        """
        Parse React component or hook

        Args:
            file_path: Path to React file

        Returns:
            ClassInfo object or None if parsing fails
        """
        try:
            source_code = file_path.read_text(encoding='utf-8', errors='ignore')

            # Determine if this is a component or hook
            is_hook = 'use' in file_path.stem.lower() and not self._is_component(source_code)

            if is_hook:
                return self._parse_hook(file_path, source_code)
            else:
                return self._parse_component(file_path, source_code)

        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None

    def _is_component(self, source_code: str) -> bool:
        """Check if file is a React component"""
        component_indicators = [
            'return <',
            'return (<',
            'return React.createElement',
            'extends Component',
            'extends React.Component'
        ]
        return any(indicator in source_code for indicator in component_indicators)

    def _parse_component(self, file_path: Path, source_code: str) -> Optional[ClassInfo]:
        """Parse React component"""
        component_name = self._extract_component_name(source_code, file_path)
        if not component_name:
            return None

        # Determine component type
        is_functional = 'function ' in source_code or 'const ' in source_code
        is_class = 'class ' in source_code and 'extends' in source_code

        # Extract props
        props = self._extract_props(source_code, component_name)

        # Extract state (hooks or class state)
        state_vars = self._extract_state(source_code, is_functional)

        # Extract methods/event handlers
        methods = self._extract_methods(source_code, is_functional)

        # Extract hooks used
        hooks = self._extract_hooks_used(source_code)

        # Extract context used
        contexts = self._extract_contexts(source_code)

        # Build metadata
        metadata = {
            'component_type': 'functional' if is_functional else 'class',
            'props': props,
            'state': state_vars,
            'hooks_used': hooks,
            'contexts': contexts,
            'has_redux': 'useSelector' in source_code or 'useDispatch' in source_code or 'connect(' in source_code,
            'is_typescript': file_path.suffix in ['.tsx', '.ts']
        }

        return ClassInfo(
            name=component_name,
            namespace=str(file_path.parent.relative_to(file_path.parent.parent.parent)),
            file_path=file_path,
            source_code=source_code,
            methods=methods,
            dependencies=hooks + contexts,
            is_controller=False,
            is_service=False,
            language='react',
            metadata=metadata
        )

    def _parse_hook(self, file_path: Path, source_code: str) -> Optional[ClassInfo]:
        """Parse React custom hook"""
        # Extract hook name (e.g., useAuth, useCounter)
        hook_match = re.search(r'export\s+(?:const|function)\s+(use\w+)', source_code)
        if not hook_match:
            return None

        hook_name = hook_match.group(1)

        # Extract methods/functions
        methods = self._extract_methods(source_code, is_functional=True)

        # Extract hooks used
        hooks = self._extract_hooks_used(source_code)

        metadata = {
            'is_custom_hook': True,
            'hooks_used': hooks,
            'returns_state': 'useState' in source_code,
            'returns_effect': 'useEffect' in source_code,
            'is_typescript': file_path.suffix == '.ts'
        }

        return ClassInfo(
            name=hook_name,
            namespace=str(file_path.parent.relative_to(file_path.parent.parent)),
            file_path=file_path,
            source_code=source_code,
            methods=methods,
            dependencies=hooks,
            is_controller=False,
            is_service=True,
            language='react',
            metadata=metadata
        )

    def _extract_props(self, source_code: str, component_name: str) -> List[Dict[str, str]]:
        """Extract component props"""
        props = []

        # TypeScript interface/type
        # interface ComponentProps { name: string; age: number }
        interface_pattern = rf'(?:interface|type)\s+{component_name}Props\s*(?:=\s*)?\{{\s*([^}}]+)\}}'
        interface_match = re.search(interface_pattern, source_code, re.DOTALL)

        if interface_match:
            props_str = interface_match.group(1)
            for prop in props_str.split('\n'):
                prop = prop.strip()
                if ':' in prop and not prop.startswith('//'):
                    match = re.match(r'(\w+)\??:\s*([^;,\n]+)', prop)
                    if match:
                        props.append({
                            'name': match.group(1),
                            'type': match.group(2).strip(),
                            'optional': '?' in prop
                        })

        # Destructured props in function
        # const Component = ({ name, age }: Props)
        destructure_match = re.search(r'\(\s*\{\s*([^}]+)\}\s*[:\)]', source_code)
        if destructure_match and not props:
            prop_names = [p.strip() for p in destructure_match.group(1).split(',')]
            props = [{'name': name, 'type': 'any', 'optional': False} for name in prop_names]

        return props

    def _extract_state(self, source_code: str, is_functional: bool) -> List[Dict[str, str]]:
        """Extract state variables"""
        state_vars = []

        if is_functional:
            # useState hooks: const [count, setCount] = useState(0)
            for match in re.finditer(r'const\s+\[(\w+),\s*(\w+)\]\s*=\s*useState', source_code):
                state_vars.append({
                    'name': match.group(1),
                    'setter': match.group(2)
                })
        else:
            # Class state: this.state = { count: 0 }
            state_match = re.search(r'this\.state\s*=\s*\{([^}]+)\}', source_code)
            if state_match:
                state_str = state_match.group(1)
                for state in state_str.split(','):
                    state = state.strip()
                    if ':' in state:
                        name = state.split(':')[0].strip()
                        state_vars.append({'name': name})

        return state_vars

    def _extract_methods(self, source_code: str, is_functional: bool) -> List[MethodInfo]:
        """Extract methods/event handlers"""
        methods = []

        if is_functional:
            # const handleClick = () => { }
            # const handleSubmit = async () => { }
            function_pattern = r'const\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>'
            for match in re.finditer(function_pattern, source_code):
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
            # Class methods: handleClick() { } or async handleSubmit() { }
            method_pattern = r'(async\s+)?(\w+)\s*\([^)]*\)\s*\{'
            for match in re.finditer(method_pattern, source_code):
                is_async = match.group(1) is not None
                method_name = match.group(2)
                # Skip constructor and lifecycle methods
                if method_name not in ['constructor', 'render', 'componentDidMount', 'componentWillUnmount']:
                    methods.append(MethodInfo(
                        name=method_name,
                        return_type='void',
                        parameters=[],
                        is_async=is_async,
                        is_public=True
                    ))

        return methods

    def _extract_hooks_used(self, source_code: str) -> List[str]:
        """Extract React hooks used"""
        hooks = []
        hook_pattern = r'(use\w+)\s*\('

        for match in re.finditer(hook_pattern, source_code):
            hook = match.group(1)
            if hook not in hooks and hook not in ['useEffect', 'useState', 'useContext', 'useRef', 'useMemo', 'useCallback']:
                hooks.append(hook)

        return hooks

    def _extract_contexts(self, source_code: str) -> List[str]:
        """Extract contexts used"""
        contexts = []

        # useContext(SomeContext)
        for match in re.finditer(r'useContext\((\w+)\)', source_code):
            context = match.group(1)
            if context not in contexts:
                contexts.append(context)

        return contexts

    def generate_test_prompt(
        self,
        class_info: ClassInfo,
        patterns: Dict[str, Any],
        test_framework: str = 'jest',
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate AI prompt for React test generation

        Args:
            class_info: Parsed component/hook information
            patterns: Learned patterns
            test_framework: Test framework (jest)
            context: Additional context

        Returns:
            Formatted prompt string
        """
        metadata = class_info.metadata
        is_hook = metadata.get('is_custom_hook', False)

        if is_hook:
            return self._generate_hook_test_prompt(class_info, test_framework)
        else:
            return self._generate_component_test_prompt(class_info, test_framework)

    def _generate_component_test_prompt(self, class_info: ClassInfo, test_framework: str) -> str:
        """Generate prompt for React component testing"""
        metadata = class_info.metadata
        props = metadata.get('props', [])
        state = metadata.get('state', [])
        component_type = metadata.get('component_type', 'functional')
        has_redux = metadata.get('has_redux', False)

        props_str = '\n'.join([f"  - {p['name']}: {p['type']}" + (" (optional)" if p.get('optional') else "") for p in props]) if props else '  None'
        state_str = '\n'.join([f"  - {s['name']}" for s in state]) if state else '  None'

        prompt = f"""Generate comprehensive Jest + React Testing Library tests for the following React component.

**Component:** {class_info.name}
**Type:** {component_type.upper()}

**Source Code:**
```typescript
{class_info.source_code}
```

**Component Details:**
- Name: {class_info.name}
- Type: {component_type}
- Redux: {has_redux}
- Props:
{props_str}
- State:
{state_str}
- Methods: {len(class_info.methods)}
- Custom Hooks: {', '.join(class_info.dependencies) if class_info.dependencies else 'None'}

**Test Requirements:**
1. Use Jest + React Testing Library
2. Test component rendering with various prop combinations
3. Test user interactions (clicks, inputs, form submissions)
4. Test state changes
5. Test conditional rendering
6. Mock all custom hooks and external dependencies
7. Test accessibility (a11y)
8. Test error boundaries if applicable
9. Use userEvent for realistic interactions
10. Follow React Testing Library best practices (query by role, label, text)

**Required Imports:**
```typescript
import {{ render, screen, waitFor, fireEvent }} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {{ {class_info.name} }} from './{class_info.file_path.stem}'
```

**Example Test Structure:**
```typescript
describe('{class_info.name}', () => {{
  it('renders with required props', () => {{
    render(<{class_info.name} /* props */ />)

    expect(screen.getByRole('heading')).toHaveTextContent('Expected Text')
  }})

  it('handles user interaction', async () => {{
    const user = userEvent.setup()
    render(<{class_info.name} />)

    const button = screen.getByRole('button', {{ name: /submit/i }})
    await user.click(button)

    await waitFor(() => {{
      expect(screen.getByText('Success')).toBeInTheDocument()
    }})
  }})

  it('updates state when input changes', async () => {{
    const user = userEvent.setup()
    render(<{class_info.name} />)

    const input = screen.getByRole('textbox')
    await user.type(input, 'Test value')

    expect(input).toHaveValue('Test value')
  }})
}})
```

**React Testing Library Best Practices:**
- Use `screen.getByRole()` instead of `getByTestId()`
- Use `userEvent` instead of `fireEvent` for realistic interactions
- Use `waitFor()` for async operations
- Query by accessibility attributes (role, label, text)
- Test behavior, not implementation details

Generate the complete test file now:"""

        return prompt

    def _generate_hook_test_prompt(self, class_info: ClassInfo, test_framework: str) -> str:
        """Generate prompt for React hook testing"""
        prompt = f"""Generate comprehensive Jest tests for the following React custom hook.

**Hook:** {class_info.name}

**Source Code:**
```typescript
{class_info.source_code}
```

**Hook Details:**
- Name: {class_info.name}
- Methods/Functions: {len(class_info.methods)}
- Dependencies: {', '.join(class_info.dependencies) if class_info.dependencies else 'None'}

**Test Requirements:**
1. Use Jest + @testing-library/react-hooks
2. Test all exported functions
3. Test state updates
4. Test side effects
5. Test async operations
6. Mock external dependencies

**Required Imports:**
```typescript
import {{ renderHook, act, waitFor }} from '@testing-library/react'
import {{ {class_info.name} }} from './{class_info.file_path.stem}'
```

**Example Test Structure:**
```typescript
describe('{class_info.name}', () => {{
  it('initializes with default values', () => {{
    const {{ result }} = renderHook(() => {class_info.name}())

    expect(result.current.state).toBeDefined()
  }})

  it('updates state when action called', () => {{
    const {{ result }} = renderHook(() => {class_info.name}())

    act(() => {{
      result.current.updateState('new value')
    }})

    expect(result.current.state).toBe('new value')
  }})

  it('handles async operations', async () => {{
    const {{ result }} = renderHook(() => {class_info.name}())

    await act(async () => {{
      await result.current.fetchData()
    }})

    await waitFor(() => {{
      expect(result.current.data).toBeDefined()
    }})
  }})
}})
```

Generate the complete test file now:"""

        return prompt

    def extract_code_from_response(self, response: str) -> str:
        """
        Extract TypeScript/JavaScript code from AI response (may contain markdown)

        Args:
            response: AI response text

        Returns:
            Extracted code
        """
        # Try to find ```typescript or ```javascript or ```tsx blocks
        pattern = r'```(?:typescript|tsx|ts|javascript|jsx|js)?\n(.*?)\n```'
        matches = re.findall(pattern, response, re.DOTALL)

        if matches:
            return matches[0].strip()

        # If no code block, return entire response
        return response.strip()

    def auto_fix_syntax(self, test_code: str) -> tuple[str, List[str], List[str]]:
        """
        Auto-fix common React test syntax issues

        Args:
            test_code: Generated test code

        Returns:
            Tuple of (fixed_code, fixes_applied, warnings)
        """
        fixed_code = test_code
        fixes = []
        warnings = []

        # Ensure proper imports
        if '@testing-library/react' not in fixed_code:
            fixed_code = "import { render, screen } from '@testing-library/react'\n" + fixed_code
            fixes.append("Added @testing-library/react imports")

        if 'userEvent' not in fixed_code and 'user interaction' in test_code.lower():
            fixed_code = "import userEvent from '@testing-library/user-event'\n" + fixed_code
            fixes.append("Added userEvent import")

        return fixed_code, fixes, warnings

    def get_test_class_name(self, class_name: str) -> str:
        """Generate test file name"""
        return f"{class_name}.test"

    def get_test_namespace(self, namespace: str) -> str:
        """Return test directory (same as source for React)"""
        return namespace

    def get_language_name(self) -> str:
        """Return language name"""
        return "React"

    def get_test_framework(self) -> str:
        """Return test framework"""
        return 'jest'

    def get_test_file_path(self, source_path: Path, output_dir: Path) -> Path:
        """Generate test file path for React component"""
        # For React, place test next to source file with .test.tsx extension
        test_name = source_path.stem + '.test.tsx'
        return source_path.parent / test_name
