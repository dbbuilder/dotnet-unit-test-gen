# Enhancement: Vue 2 vs Vue 3 Automatic Detection

## Problem Statement

Currently, the Vue.js language handler generates tests using Vue 3 APIs, which are incompatible with Vue 2 projects. This requires manual post-processing to convert:

- `createStore()` (Vuex 4) → `new Vuex.Store()` (Vuex 3)
- `createRouter()` (Vue Router 4) → `new VueRouter()` (Vue Router 3)
- `global.plugins` (Vue 3) → `localVue` (Vue 2)
- `@vue/test-utils` v2 → v1

## Solution

Add automatic Vue version detection to `VueJSLanguageHandler` and generate version-appropriate tests.

## Implementation Status

### ✅ Phase 1: Version Detection (COMPLETE)

Added `_detect_vue_version()` method to `VueJSLanguageHandler`:

```python
def _detect_vue_version(self, project_dir: Path) -> int:
    """
    Detect Vue version from package.json

    Returns: 2 or 3 (Vue major version)
    """
    # Searches for package.json in project and parent directories
    # Parses Vue dependency version
    # Caches result per project
    # Defaults to Vue 3 if not found
```

**Features**:
- ✅ Reads `package.json` from project directory
- ✅ Searches parent directories if not found in project root
- ✅ Checks both `dependencies` and `devDependencies`
- ✅ Extracts major version from semver string
- ✅ Caches result to avoid repeated file reads
- ✅ Defaults to Vue 3 for forward compatibility

### 🔄 Phase 2: Version-Specific Test Generation (TODO)

Need to update `generate_test_prompt()` to generate different code based on Vue version:

#### Vue 2 Test Template

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, createLocalVue } from '@vue/test-utils'
import Vuex from 'vuex'
import VueRouter from 'vue-router'
import ComponentName from './ComponentName.vue'

describe('ComponentName', () => {
  let localVue
  let store
  let router

  beforeEach(() => {
    localVue = createLocalVue()
    localVue.use(Vuex)
    localVue.use(VueRouter)

    store = new Vuex.Store({
      state: { /* ... */ },
      getters: { /* ... */ },
      actions: { /* ... */ }
    })

    router = new VueRouter({
      mode: 'abstract',
      routes: [ /* ... */ ]
    })
  })

  it('renders properly', () => {
    const wrapper = mount(ComponentName, {
      localVue,
      store,
      router,
      propsData: { /* ... */ }
    })

    expect(wrapper.exists()).toBe(true)
  })
})
```

#### Vue 3 Test Template

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createStore } from 'vuex'
import { createRouter, createMemoryHistory } from 'vue-router'
import ComponentName from './ComponentName.vue'

describe('ComponentName', () => {
  let store
  let router

  beforeEach(() => {
    store = createStore({
      state: { /* ... */ },
      getters: { /* ... */ },
      actions: { /* ... */ }
    })

    router = createRouter({
      history: createMemoryHistory(),
      routes: [ /* ... */ ]
    })
  })

  it('renders properly', () => {
    const wrapper = mount(ComponentName, {
      global: {
        plugins: [store, router]
      },
      props: { /* ... */ }
    })

    expect(wrapper.exists()).toBe(true)
  })
})
```

### 🔄 Phase 3: Update Test Helper Functions (TODO)

Update `tests/helpers/store.ts` and `tests/helpers/router.ts` to export version-appropriate helpers.

### 🔄 Phase 4: Update Documentation (TODO)

Update `TESTING.md` to mention automatic Vue version detection.

## API Differences

### Vuex

| Vue 2 (Vuex 3) | Vue 3 (Vuex 4) |
|----------------|----------------|
| `import Vuex from 'vuex'` | `import { createStore } from 'vuex'` |
| `new Vuex.Store({...})` | `createStore({...})` |
| Same API | Same API |

### Vue Router

| Vue 2 (Vue Router 3) | Vue 3 (Vue Router 4) |
|----------------------|----------------------|
| `import VueRouter from 'vue-router'` | `import { createRouter, createMemoryHistory } from 'vue-router'` |
| `new VueRouter({mode: 'abstract', routes})` | `createRouter({history: createMemoryHistory(), routes})` |
| `router.push()` | `router.push()` |

### Vue Test Utils

| Vue 2 (@vue/test-utils v1) | Vue 3 (@vue/test-utils v2) |
|-----------------------------|----------------------------|
| `import { mount, createLocalVue } from '@vue/test-utils'` | `import { mount } from '@vue/test-utils'` |
| `const localVue = createLocalVue()` | Not needed |
| `localVue.use(Vuex)` | Not needed |
| `mount(Component, { localVue, store, router, propsData })` | `mount(Component, { global: { plugins: [store, router] }, props })` |

### Component Mounting

| Vue 2 | Vue 3 |
|-------|-------|
| `propsData: { name: 'test' }` | `props: { name: 'test' }` |
| `localVue, store, router` at top level | `global: { plugins: [store, router] }` |
| `createLocalVue()` required | Not needed |

## Testing the Enhancement

### Test Case 1: Vue 2 Project Detection

```bash
cd /mnt/d/dev2/michaeljr/ecommerce-app
python generate_tests_v2.py src --language vuejs --dry-run
# Should detect: Vue 2.7.16
```

### Test Case 2: Vue 3 Project Detection

```bash
cd /path/to/vue3/project
python generate_tests_v2.py src --language vuejs --dry-run
# Should detect: Vue 3.x.x
```

### Test Case 3: No package.json

```bash
cd /tmp/no-package-json
python generate_tests_v2.py . --language vuejs --dry-run
# Should default to: Vue 3 (with warning)
```

## Benefits

1. **Zero Manual Fixes**: Tests work out-of-the-box for both Vue 2 and Vue 3
2. **Better DX**: Developers don't need to know the differences
3. **Accurate Tests**: Uses correct APIs for the project's Vue version
4. **Future-Proof**: Easy to add Vue 4+ support when released

## Implementation Checklist

- [x] Add `_detect_vue_version()` method
- [x] Add version caching
- [x] Handle missing package.json gracefully
- [ ] Update `generate_test_prompt()` to use version
- [ ] Create Vue 2 test template
- [ ] Create Vue 3 test template
- [ ] Update test helper templates
- [ ] Add version detection to dry-run output
- [ ] Update documentation
- [ ] Add unit tests for version detection
- [ ] Test on Vue 2 project (ecommerce-app)
- [ ] Test on Vue 3 project
- [ ] Update CHANGELOG.md

## Estimated Effort

- **Detection (Phase 1)**: ✅ Complete (30 minutes)
- **Templates (Phase 2)**: 2 hours
- **Helpers (Phase 3)**: 1 hour
- **Docs (Phase 4)**: 30 minutes
- **Testing**: 1 hour
- **Total**: ~4.5 hours

## Priority

**HIGH** - This eliminates a major pain point and makes the tool truly universal for Vue projects.

## Related Enhancements

1. **React Version Detection**: Detect React 16/17/18 for Hooks vs Class components
2. **Angular Version Detection**: Detect Angular version for TestBed configuration
3. **Framework Version in Metadata**: Store detected version in ClassInfo.metadata

---

**Status**: Phase 1 Complete
**Next Step**: Implement Phase 2 (version-specific templates)
**Assigned**: Pending
**Target**: v1.4 Release
