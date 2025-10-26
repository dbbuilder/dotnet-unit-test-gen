# Playwright E2E Test Generator Module Specification

**Date**: 2025-10-25
**Status**: Planning Phase
**Target**: End-to-end browser testing
**Priority**: Phase 4 (Medium - needed for ecommerce-app user flows)

---

## Executive Summary

The Playwright E2E Test Generator creates comprehensive end-to-end tests for web applications, validating complete user journeys, UI interactions, and cross-browser compatibility. It analyzes Vue Router routes, component flows, and user interactions to generate realistic test scenarios.

**Primary Use Cases**:
1. **ecommerce-app User Flows** - Test checkout, payment, receipt workflows
2. **Cross-Browser Testing** - Validate Chrome, Firefox, Safari compatibility
3. **Visual Regression Testing** - Detect UI changes
4. **Accessibility Testing** - Validate WCAG compliance

**Technology Stack**:
- **Framework**: Playwright (supports Chromium, Firefox, WebKit)
- **Language**: TypeScript
- **Assertions**: Playwright's built-in expect
- **Reporting**: HTML reporter with screenshots/videos

---

## Architecture Design

### Module Structure

```
dotnet-unit-test-gen/
├── generators/
│   └── playwright_generator.py         # NEW - E2E test generator
├── analyzers/
│   ├── route_analyzer.py               # NEW - Vue Router analyzer
│   ├── user_flow_analyzer.py           # NEW - User journey analyzer
│   └── component_interaction_analyzer.py  # NEW - UI interaction analyzer
├── templates/
│   └── playwright/
│       ├── page_object.jinja2              # Page Object Model template
│       ├── user_flow_test.jinja2           # User journey test
│       ├── component_interaction.jinja2    # UI interaction test
│       └── visual_regression.jinja2        # Visual testing
└── page_objects/
    └── page_object_builder.py          # NEW - POM generation
```

---

## Route and Flow Analysis

### Vue Router Analysis

```python
class RouteAnalyzer(BaseAnalyzer):
    """Analyzes Vue Router configuration to identify testable routes"""

    def analyze_router(self, router_file: str) -> Dict[str, Any]:
        """
        Extract route definitions from Vue Router:
        - Route paths
        - Component mappings
        - Route guards (authentication)
        - Query parameters
        - Route meta data
        """
        content = Path(router_file).read_text()

        return {
            "routes": self._extract_routes(content),
            "guards": self._extract_route_guards(content),
            "redirects": self._extract_redirects(content)
        }

    def _extract_routes(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract route definitions:

        Example from router/index.js:
        {
          path: '/payment-success',
          name: 'PaymentSuccess',
          component: () => import('@/views/PaymentSuccess.vue'),
          meta: { requiresAuth: false }
        }
        """
        routes = []

        # Pattern: { path: '...', name: '...', component: ... }
        route_pattern = r"{\s*path:\s*['\"]([^'\"]+)['\"],\s*name:\s*['\"](\w+)['\"],\s*component:[^}]+}"

        for match in re.finditer(route_pattern, content, re.DOTALL):
            path, name = match.groups()

            routes.append({
                "path": path,
                "name": name,
                "component": self._extract_component_name(match.group(0)),
                "requires_auth": "requiresAuth: true" in match.group(0),
                "params": self._extract_route_params(path),
                "query": self._extract_query_params(match.group(0))
            })

        return routes

    def _extract_route_params(self, path: str) -> List[str]:
        """
        Extract dynamic route parameters:
        /user/:id → ['id']
        /product/:category/:id → ['category', 'id']
        """
        return re.findall(r':(\w+)', path)

    def _extract_route_guards(self, content: str) -> Dict[str, Any]:
        """
        Extract beforeEach and afterEach guards:
        router.beforeEach((to, from, next) => { ... })
        """
        return {
            "has_before_each": "beforeEach" in content,
            "has_after_each": "afterEach" in content,
            "checks_auth": "requiresAuth" in content
        }
```

### User Flow Analysis

```python
class UserFlowAnalyzer:
    """Analyzes application to identify common user flows"""

    def analyze_user_flows(self, project_path: str) -> List[Dict[str, Any]]:
        """
        Identify user flows by analyzing:
        - Router navigation calls (this.$router.push)
        - Form submissions
        - API calls that trigger navigation
        - Multi-step processes
        """
        flows = []

        # Analyze all Vue components for navigation patterns
        vue_files = Path(project_path).glob("**/*.vue")

        for vue_file in vue_files:
            content = vue_file.read_text()

            # Find router.push calls
            push_pattern = r'this\.\$router\.push\([\'"]([^\'"]+)[\'"]\)'
            pushes = re.findall(push_pattern, content)

            # Find form submissions
            submit_pattern = r'@submit(?:\.prevent)?=[\'"](\w+)[\'"]'
            submits = re.findall(submit_pattern, content)

            if pushes and submits:
                flows.append({
                    "component": vue_file.stem,
                    "type": "form_submission_flow",
                    "steps": [
                        {"action": "submit_form", "method": submits[0]},
                        {"action": "navigate_to", "route": pushes[0]}
                    ]
                })

        return flows

    def detect_checkout_flow(self, project_path: str) -> Optional[Dict[str, Any]]:
        """
        Detect e-commerce checkout flow:
        1. Cart → Checkout → Payment → Success
        """
        # Look for common e-commerce patterns
        cart_route = self._find_route_by_name(project_path, "Cart")
        checkout_route = self._find_route_by_name(project_path, "Checkout")
        payment_route = self._find_route_by_name(project_path, "Payment")
        success_route = self._find_route_by_name(project_path, "PaymentSuccess")

        if all([cart_route, checkout_route, payment_route, success_route]):
            return {
                "name": "checkout_flow",
                "steps": [
                    {"route": cart_route, "action": "review_cart"},
                    {"route": checkout_route, "action": "enter_details"},
                    {"route": payment_route, "action": "submit_payment"},
                    {"route": success_route, "action": "confirm_order"}
                ]
            }

        return None
```

### Component Interaction Analysis

```python
class ComponentInteractionAnalyzer:
    """Analyzes Vue components for UI interactions"""

    def analyze_component_interactions(self, component_file: str) -> Dict[str, Any]:
        """
        Extract testable UI interactions:
        - Button clicks
        - Form inputs
        - Dropdown selections
        - File uploads
        - Modal dialogs
        - Toast notifications
        """
        content = Path(component_file).read_text()

        return {
            "component_name": Path(component_file).stem,
            "interactions": self._extract_interactions(content),
            "validations": self._extract_validations(content),
            "api_calls": self._extract_api_calls(content)
        }

    def _extract_interactions(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract UI interaction points from template:
        - <button @click="methodName">
        - <input v-model="dataProperty">
        - <select v-model="selectedValue">
        """
        interactions = []

        # Button clicks
        button_pattern = r'<button[^>]*@click(?:\.prevent)?=[\'"](\w+)[\'"][^>]*>([^<]+)</button>'
        for match in re.finditer(button_pattern, content):
            method, label = match.groups()
            interactions.append({
                "type": "button_click",
                "method": method,
                "label": label.strip(),
                "selector": f"button:has-text('{label.strip()}')"
            })

        # Input fields
        input_pattern = r'<input[^>]*v-model=[\'"](\w+)[\'"][^>]*(?:placeholder=[\'"]([^\'"]+)[\'"])?'
        for match in re.finditer(input_pattern, content):
            model, placeholder = match.groups()
            interactions.append({
                "type": "input_fill",
                "model": model,
                "placeholder": placeholder,
                "selector": f"input[placeholder='{placeholder}']" if placeholder else f"input"
            })

        return interactions

    def _extract_validations(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract validation logic:
        - Required fields
        - Email validation
        - Custom validators
        """
        validations = []

        # Required field validation
        if "required" in content:
            required_pattern = r'(\w+):\s*{\s*required:\s*true'
            for match in re.finditer(required_pattern, content):
                field = match.group(1)
                validations.append({
                    "field": field,
                    "type": "required",
                    "message": f"{field} is required"
                })

        return validations
```

---

## Test Generation Templates

### Page Object Model Template

```typescript
// templates/playwright/page_object.jinja2
import { Page, Locator, expect } from '@playwright/test';

export class {{ page_name }}Page {
  readonly page: Page;
  {% for interaction in interactions %}
  readonly {{ interaction.name }}: Locator;
  {% endfor %}

  constructor(page: Page) {
    this.page = page;
    {% for interaction in interactions %}
    this.{{ interaction.name }} = page.locator('{{ interaction.selector }}');
    {% endfor %}
  }

  async goto() {
    await this.page.goto('{{ route_path }}');
    await this.page.waitForLoadState('networkidle');
  }

  {% for method in page_methods %}
  async {{ method.name }}({{ method.params | join(', ') }}) {
    {% if method.type == 'fill_form' %}
    {% for field in method.fields %}
    await this.{{ field.name }}.fill({{ field.param }});
    {% endfor %}
    {% elif method.type == 'click_button' %}
    await this.{{ method.button }}.click();
    {% elif method.type == 'select_option' %}
    await this.{{ method.select }}.selectOption({{ method.param }});
    {% endif %}

    {% if method.waits_for_navigation %}
    await this.page.waitForURL('{{ method.expected_url }}');
    {% endif %}
  }
  {% endfor %}

  {% for assertion in page_assertions %}
  async {{ assertion.name }}() {
    {% if assertion.type == 'visible' %}
    await expect(this.{{ assertion.element }}).toBeVisible();
    {% elif assertion.type == 'text_content' %}
    await expect(this.{{ assertion.element }}).toHaveText('{{ assertion.expected_text }}');
    {% elif assertion.type == 'attribute' %}
    await expect(this.{{ assertion.element }}).toHaveAttribute('{{ assertion.attribute }}', '{{ assertion.value }}');
    {% endif %}
  }
  {% endfor %}
}
```

### User Flow Test Template

```typescript
// templates/playwright/user_flow_test.jinja2
import { test, expect } from '@playwright/test';
{% for page in pages %}
import { {{ page.name }}Page } from './pages/{{ page.name }}Page';
{% endfor %}

test.describe('{{ flow_name }}', () => {
  {% for step in flow_steps %}
  test('{{ step.description }}', async ({ page }) => {
    // Arrange
    {% if step.setup %}
    {{ step.setup }}
    {% endif %}

    {% for page_object in step.pages %}
    const {{ page_object.var_name }} = new {{ page_object.class_name }}(page);
    {% endfor %}

    {% for action in step.actions %}
    // {{ action.description }}
    {% if action.type == 'goto' %}
    await {{ action.page }}.goto();
    {% elif action.type == 'fill_form' %}
    await {{ action.page }}.{{ action.method }}({{ action.params | join(', ') }});
    {% elif action.type == 'click' %}
    await {{ action.page }}.{{ action.button }}.click();
    {% elif action.type == 'wait_for_navigation' %}
    await page.waitForURL('{{ action.url }}');
    {% elif action.type == 'assert' %}
    await {{ action.page }}.{{ action.assertion }}();
    {% endif %}
    {% endfor %}

    {% if step.assertions %}
    // Assert
    {% for assertion in step.assertions %}
    {{ assertion }}
    {% endfor %}
    {% endif %}
  });
  {% endfor %}

  {% if flow_has_error_cases %}
  test.describe('Error Handling', () => {
    {% for error_case in error_cases %}
    test('{{ error_case.description }}', async ({ page }) => {
      // Arrange
      {% for page_object in error_case.pages %}
      const {{ page_object.var_name }} = new {{ page_object.class_name }}(page);
      {% endfor %}

      // Act
      {% for action in error_case.actions %}
      await {{ action.page }}.{{ action.method }}({{ action.params | join(', ') }});
      {% endfor %}

      // Assert
      {% for assertion in error_case.assertions %}
      {{ assertion }}
      {% endfor %}
    });
    {% endfor %}
  });
  {% endif %}
});
```

### ecommerce-app Checkout Flow Example

```typescript
// Example generated test for ecommerce-app
import { test, expect } from '@playwright/test';
import { CartPage } from './pages/CartPage';
import { CheckoutPage } from './pages/CheckoutPage';
import { PaymentPage } from './pages/PaymentPage';
import { PaymentSuccessPage } from './pages/PaymentSuccessPage';

test.describe('E-Commerce Checkout Flow', () => {
  test('complete checkout with credit card payment', async ({ page }) => {
    // Arrange
    const cartPage = new CartPage(page);
    const checkoutPage = new CheckoutPage(page);
    const paymentPage = new PaymentPage(page);
    const successPage = new PaymentSuccessPage(page);

    // Step 1: Add items to cart
    await page.goto('/products');
    await page.locator('button:has-text("Add to Cart")').first().click();
    await page.locator('[data-testid="cart-icon"]').click();

    // Step 2: Review cart
    await cartPage.goto();
    await expect(cartPage.cartItems).toHaveCount(1);
    await cartPage.proceedToCheckout();

    // Step 3: Enter checkout details
    await checkoutPage.fillCustomerInfo({
      firstName: 'John',
      lastName: 'Doe',
      email: 'john.doe@example.com',
      phone: '555-1234'
    });
    await checkoutPage.selectPickupLocation('Main Campus');
    await checkoutPage.continueToPayment();

    // Step 4: Complete payment
    await paymentPage.fillPaymentDetails({
      cardNumber: '4111111111111111',
      expiryDate: '12/25',
      cvv: '123',
      zipCode: '12345'
    });
    await paymentPage.submitPayment();

    // Step 5: Verify success
    await successPage.waitForSuccess();
    await expect(successPage.confirmationMessage).toContainText('Payment Successful');
    await expect(successPage.transactionId).toBeVisible();
  });

  test('checkout with missing required fields shows validation errors', async ({ page }) => {
    const checkoutPage = new CheckoutPage(page);

    await checkoutPage.goto();
    await checkoutPage.continueToPayment(); // Without filling form

    // Assert validation errors
    await expect(page.locator('.error-message')).toContainText('Email is required');
    await expect(page.locator('.error-message')).toContainText('Phone is required');
  });

  test('payment failure shows error message', async ({ page }) => {
    const paymentPage = new PaymentPage(page);

    // Navigate to payment page (assume cart and checkout completed)
    await paymentPage.goto();

    // Use invalid card number
    await paymentPage.fillPaymentDetails({
      cardNumber: '4000000000000002', // Card declined
      expiryDate: '12/25',
      cvv: '123',
      zipCode: '12345'
    });
    await paymentPage.submitPayment();

    // Assert error handling
    await expect(page.locator('.payment-error')).toContainText('Payment failed');
  });
});
```

---

## Pattern Learning for E2E Tests

### Playwright-Specific Error Patterns

```python
class PlaywrightPatternLearner:
    """Learns patterns from Playwright test execution"""

    PLAYWRIGHT_ERROR_PATTERNS = {
        "selector_errors": [
            r"Error: locator\.click: Timeout .+ waiting for selector \"([^\"]+)\"",
            r"Error: elementHandle\.fill: Element is not an <input>"
        ],
        "navigation_errors": [
            r"Error: page\.goto: Timeout .+ waiting for navigation to \"([^\"]+)\"",
            r"Error: page\.waitForURL: Timeout"
        ],
        "assertion_errors": [
            r"Error: expect\((.+)\)\.toBeVisible",
            r"Error: expect\((.+)\)\.toHaveText"
        ],
        "timing_errors": [
            r"Error: locator\.click: Element is outside of the viewport",
            r"Error: elementHandle is not attached to the DOM"
        ]
    }

    def learn_from_playwright_tests(self, test_output: str) -> List[Dict[str, Any]]:
        """
        Learn patterns from Playwright test failures

        Example patterns:
        1. "Timeout waiting for selector 'button:has-text(Submit)'"
           → Button text might be dynamic, use data-testid instead

        2. "Element is outside of the viewport"
           → Need to scroll element into view before interaction

        3. "Page goto timeout to '/payment'"
           → Route might require authentication, add login step
        """
        patterns = []

        for error_type, regex_patterns in self.PLAYWRIGHT_ERROR_PATTERNS.items():
            for regex in regex_patterns:
                matches = re.findall(regex, test_output)
                for match in matches:
                    pattern = self._create_playwright_pattern(error_type, match)
                    patterns.append(pattern)

        return patterns

    def _create_playwright_pattern(self, error_type: str, match: str) -> Dict[str, Any]:
        """Create pattern from Playwright error"""
        if error_type == "selector_errors":
            return {
                "type": "selector_improvement",
                "failed_selector": match,
                "recommendation": f"Use data-testid attribute instead of text-based selector",
                "confidence": 0.85
            }
        elif error_type == "navigation_errors":
            return {
                "type": "navigation_timeout",
                "url": match,
                "recommendation": f"Increase timeout or check route guards",
                "confidence": 0.9
            }
        # ... additional patterns
```

---

## Visual Regression Testing

```typescript
// templates/playwright/visual_regression.jinja2
import { test, expect } from '@playwright/test';

test.describe('Visual Regression Tests', () => {
  {% for route in routes %}
  test('{{ route.name }} - visual snapshot', async ({ page }) => {
    await page.goto('{{ route.path }}');
    await page.waitForLoadState('networkidle');

    // Take screenshot
    await expect(page).toHaveScreenshot('{{ route.name }}.png', {
      fullPage: true,
      animations: 'disabled'
    });
  });
  {% endfor %}

  {% for component in critical_components %}
  test('{{ component.name }} - component snapshot', async ({ page }) => {
    await page.goto('{{ component.route }}');
    await page.waitForSelector('{{ component.selector }}');

    // Take component screenshot
    const component = page.locator('{{ component.selector }}');
    await expect(component).toHaveScreenshot('{{ component.name }}.png');
  });
  {% endfor %}
});
```

---

## Cost Estimation

**Per Page Analysis** (GPT-4o-mini):
- Route definition: ~100 lines
- Component analysis: ~300 lines
- User flow detection: ~200 tokens
- Test generation: ~1500 tokens
- **Total per page**: ~2100 tokens
- **Cost per page**: ~$0.0015 (0.15 cents)

**ecommerce-app E2E Suite**:
- Routes: 8 pages
- User flows: 3 flows
- Total cost: (8 + 3) × $0.0015 = **$0.0165** (1.65 cents)
- Pattern learning: ~$0.50
- **Total first run**: **$0.52**

---

## Implementation Roadmap

### Day 1-2: Page Object Generation
- [ ] Implement `RouteAnalyzer`
- [ ] Implement `ComponentInteractionAnalyzer`
- [ ] Create Page Object Model template
- [ ] Test on ecommerce-app routes

### Day 3-4: User Flow Tests
- [ ] Implement `UserFlowAnalyzer`
- [ ] Detect checkout flow in ecommerce-app
- [ ] Generate user flow tests
- [ ] Run tests and capture failures

### Day 5: Pattern Learning + Visual Testing
- [ ] Implement `PlaywrightPatternLearner`
- [ ] Learn patterns from test failures
- [ ] Add visual regression tests
- [ ] Regenerate with learned patterns

---

## Success Criteria

- ✅ Generate Page Objects for 8+ routes
- ✅ Generate 3+ complete user flow tests
- ✅ Total cost < $1.00
- ✅ 70%+ test pass rate after pattern learning
- ✅ Visual regression baseline created

---

## Next Steps

1. Implement route analyzer
2. Test on ecommerce-app router
3. Generate Page Objects
4. Create checkout flow test
