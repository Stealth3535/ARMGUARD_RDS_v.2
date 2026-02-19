# ARMGUARD RDS v.2 - Design System Testing Guide

## Overview

This testing framework validates that all Django app templates correctly implement the unified design system. Tests cover component usage, accessibility, responsive design, and visual consistency across the entire application.

---

## Test Structure

### Test Files Per App

Each Django app has its own `tests_design_system.py` file:

```
armguard/
├── admin/tests_design_system.py
├── inventory/tests_design_system.py
├── personnel/tests_design_system.py
├── transactions/tests_design_system.py
├── users/tests_design_system.py
└── test_all_design_system.py (master runner)
```

### Test Categories

Each app's tests are organized into categories:

1. **Design System Tests** - Verify design system classes are used
2. **Component Tests** - Test specific UI components (buttons, cards, badges)
3. **Accessibility Tests** - Verify WCAG compliance and semantic HTML
4. **Responsive Tests** - Test mobile-friendly layouts
5. **Integration Tests** - Test with real data scenarios
6. **Performance Tests** - Verify CSS loading and optimization

---

## Running Tests

### Quick Sanity Check

Run a fast validation of core components:

```powershell
cd armguard
python test_all_design_system.py --quick
```

Expected output:
```
Dashboard Component Check:
  ✓ Design System CSS Loaded
  ✓ Card Component
  ✓ Button Component
  ✓ Stat Card Component
  ✓ Grid Layout
  ✓ Form Components
  ✓ Badge Component

Passed: 7/7
✓ Quick test PASSED!
```

### Test Single App

Test a specific Django app:

```powershell
python test_all_design_system.py --app admin
python test_all_design_system.py --app inventory
python test_all_design_system.py --app personnel
python test_all_design_system.py --app transactions
python test_all_design_system.py --app users
```

### Test All Apps

Run comprehensive test suite across all apps:

```powershell
python test_all_design_system.py
```

Expected output:
```
======================================================================
               ARMGUARD RDS v.2
          Design System Test Suite
======================================================================
Date: February 19, 2026 14:30:00
Testing 5 applications
======================================================================

──────────────────────────────────────────────────────────────────────
Testing ADMIN App
──────────────────────────────────────────────────────────────────────

test_dashboard_loads_with_design_system (admin.tests_design_system.AdminDesignSystemTests) ... ok
test_dashboard_stats_display (admin.tests_design_system.AdminDesignSystemTests) ... ok
...

✓ ADMIN tests passed

[... continues for all apps ...]

======================================================================
                    TEST SUMMARY
======================================================================
✓ ADMIN            - PASS
✓ INVENTORY        - PASS
✓ PERSONNEL        - PASS
✓ TRANSACTIONS     - PASS
✓ USERS            - PASS
──────────────────────────────────────────────────────────────────────
Total: 5 apps | Passed: 5 | Failed: 0
Duration: 12.34 seconds
======================================================================

🎉 ALL TESTS PASSED! Design system is working correctly.
```

### Component Usage Matrix

View which design system components are used in each app:

```powershell
python test_all_design_system.py --matrix
```

Expected output:
```
===============================================================================
               DESIGN SYSTEM COMPONENT MATRIX
===============================================================================

Component Usage Across Apps:

Component      Admin          Inventory      Personnel      Transactions   Users          
─────────────────────────────────────────────────────────────────────────────────────────
Card           ✓              ✓              ✓              ✓              ✓              
Button         ✓              ✓              ✓              ✓              ✓              
Stat Card      ✓              ✓              ✓              ✓              —              
Badge          ✓              ✓              ✓              ✓              —              
Table          ✓              ✓              ✓              ✓              —              
Form Input     ✓              ✓              —              —              ✓              
Alert          ✓              —              —              —              ✓              
Grid           ✓              ✓              ✓              ✓              ✓              
Pills          ✓              ✓              ✓              ✓              —              

✓ = Implemented | — = Not applicable
```

### Django Test Runner

You can also use Django's built-in test command:

```powershell
# Test all design system tests
python manage.py test --pattern="tests_design_system.py"

# Test specific app
python manage.py test admin.tests_design_system
python manage.py test inventory.tests_design_system
python manage.py test personnel.tests_design_system
python manage.py test transactions.tests_design_system
python manage.py test users.tests_design_system

# Verbose output
python manage.py test admin.tests_design_system -v 2

# Keep database between test runs (faster)
python manage.py test --keepdb
```

---

## Test Coverage

### Admin App Tests (admin/tests_design_system.py)

**Classes:**
- `AdminDesignSystemTests` - Dashboard design system validation
- `AdminComponentTests` - Button, card, badge components
- `AdminResponsiveTests` - Mobile-friendly layouts
- `AdminPerformanceTests` - CSS loading optimization
- `AdminIntegrationTests` - Real data scenarios

**Key Tests:**
- ✅ Dashboard uses stat-card, card, btn, grid, form components
- ✅ Filter and search box functionality
- ✅ Typography and spacing system usage
- ✅ Color system implementation
- ✅ Minimal inline styles (CSS system reliance)
- ✅ Accessibility features (ARIA, semantic HTML)

### Inventory App Tests (inventory/tests_design_system.py)

**Classes:**
- `InventoryDesignSystemTests` - Item list design validation
- `InventoryComponentTests` - Component variations
- `InventoryAccessibilityTests` - A11y compliance
- `InventoryIntegrationTests` - Multiple items scenarios

**Key Tests:**
- ✅ Inventory list uses design system components
- ✅ Status badges color-coded correctly
- ✅ Filter UI components
- ✅ Table component styling
- ✅ Responsive grid layout
- ✅ Item detail page design

### Personnel App Tests (personnel/tests_design_system.py)

**Classes:**
- `PersonnelDesignSystemTests` - Profile list validation
- `PersonnelProfileDetailTests` - Detail view components
- `PersonnelComponentTests` - Badge and card variants
- `PersonnelAccessibilityTests` - Semantic HTML
- `PersonnelIntegrationTests` - Multiple personnel scenarios

**Key Tests:**
- ✅ Personnel list design system usage
- ✅ Officer/Enlisted classification badges
- ✅ Profile card layout
- ✅ Transaction history display
- ✅ Responsive table design
- ✅ Filter and search components

### Transactions App Tests (transactions/tests_design_system.py)

**Classes:**
- `TransactionsDesignSystemTests` - List view validation
- `TransactionFilterTests` - DEFCON/NORMAL filtering
- `TransactionComponentTests` - Badge color coding
- `TransactionAccessibilityTests` - Proper table structure
- `TransactionIntegrationTests` - Real transaction data

**Key Tests:**
- ✅ Transaction list design system implementation
- ✅ DEFCON badge (danger) styling
- ✅ NORMAL badge (primary) styling
- ✅ Action type badges (Take/Return)
- ✅ Time range filtering
- ✅ Statistics accuracy
- ✅ Responsive grid for stats

### Users App Tests (users/tests_design_system.py)

**Classes:**
- `UsersDesignSystemTests` - Login page validation
- `UsersFormTests` - Form component usage
- `UsersAccessibilityTests` - Form accessibility
- `UsersComponentTests` - Alert and button components
- `UsersIntegrationTests` - Login/logout flow
- `UsersResponsiveTests` - Mobile login layout

**Key Tests:**
- ✅ Login page card layout
- ✅ Form input and label styling
- ✅ Button component usage
- ✅ Form validation messages
- ✅ Authentication flow
- ✅ Mobile-friendly design

---

## Interpreting Test Results

### Success Output

```
test_dashboard_loads_with_design_system ... ok
test_dashboard_stats_display ... ok
test_dashboard_filter_functionality ... ok

Ran 15 tests in 2.34s

OK
```

All tests passed! The design system is correctly implemented.

### Failure Output

```
test_dashboard_loads_with_design_system ... FAIL
test_dashboard_stats_display ... ok

======================================================================
FAIL: test_dashboard_loads_with_design_system
----------------------------------------------------------------------
AssertionError: False is not true : Should use stat-card component
```

**How to fix:**
1. Open the failing template (e.g., `admin/templates/admin/dashboard.html`)
2. Find instances where old classes are used
3. Replace with design system classes (e.g., change custom `.stat-card` to `.stat-card`)
4. Re-run test to verify fix

### Common Failures and Fixes

| Failure | Cause | Fix |
|---------|-------|-----|
| "Should use stat-card component" | Old custom stat card classes | Use `.stat-card` with modifiers `.stat-card-primary`, `.stat-card-success` |
| "Should use card component" | Missing card wrapper | Wrap content in `<div class="card">` |
| "Should use btn component" | Old button classes | Replace with `.btn .btn-primary`, `.btn .btn-success`, etc. |
| "Should use form-input" | Old input styling | Add `.form-input` class to `<input>` elements |
| "Should use badge component" | Custom badge classes | Use `.badge .badge-success`, `.badge-danger`, etc. |
| "Should use grid layout" | Old float/flex layout | Use `.grid .grid-cols-4 .gap-4` for grids |

---

## Adding New Tests

### Template for New Test Class

```python
from django.test import TestCase, Client
from django.contrib.auth import get_user_model

User = get_user_model()

class MyNewFeatureTests(TestCase):
    """Test my new feature uses design system"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_login(self.user)
        
    def test_new_feature_design_system(self):
        """Test that new feature uses design system classes"""
        response = self.client.get('/my-new-feature/')
        self.assertEqual(response.status_code, 200)
        
        html = response.content.decode('utf-8')
        
        # Check for design system components
        self.assertIn('card', html, "Should use card component")
        self.assertIn('btn', html, "Should use button component")
        self.assertIn('grid', html, "Should use grid layout")
```

### Running Your New Test

```powershell
python manage.py test myapp.tests_design_system.MyNewFeatureTests
```

---

## Continuous Integration

### Integrating with CI/CD

Add to your CI pipeline (e.g., GitHub Actions, GitLab CI):

```yaml
test-design-system:
  script:
    - cd armguard
    - python test_all_design_system.py
  artifacts:
    reports:
      junit: test-results.xml
```

### Pre-commit Hook

Add to `.git/hooks/pre-commit`:

```bash
#!/bin/bash
cd armguard
python test_all_design_system.py --quick
if [ $? -ne 0 ]; then
    echo "❌ Design system tests failed. Fix issues before committing."
    exit 1
fi
```

---

## Troubleshooting

### Issue: Tests can't find templates

**Solution:** Ensure you're running tests from the `armguard/` directory:
```powershell
cd armguard
python test_all_design_system.py
```

### Issue: Import errors

**Solution:** Make sure Django is properly configured:
```powershell
$env:DJANGO_SETTINGS_MODULE="core.settings"
python test_all_design_system.py
```

### Issue: Database errors

**Solution:** Run migrations before testing:
```powershell
python manage.py migrate
python test_all_design_system.py
```

### Issue: Tests pass but visual issues exist

**Solution:** Tests verify class usage, not visual rendering. Manually inspect pages in a browser alongside automated tests.

---

## Test Maintenance

### When to Update Tests

- **After adding new pages:** Add tests for new templates
- **After design system changes:** Update expected class names
- **After component additions:** Add tests for new components
- **After accessibility improvements:** Add new a11y checks

### Test Review Checklist

- [ ] All apps have test coverage
- [ ] Tests check for design system classes
- [ ] Accessibility tests included
- [ ] Integration tests with real data
- [ ] Quick test runs fast (< 5 seconds)
- [ ] Full test suite completes (< 30 seconds)

---

## Performance Benchmarks

| Test Suite | Target Time | Acceptable Range |
|------------|-------------|------------------|
| Quick Test | 2-3 seconds | < 5 seconds |
| Single App | 3-5 seconds | < 10 seconds |
| Full Suite | 15-25 seconds | < 60 seconds |

If tests exceed acceptable ranges, consider:
- Using `--keepdb` flag
- Reducing test data volume
- Parallelizing test execution

---

## Best Practices

1. **Run quick test frequently** - Fast feedback during development
2. **Run full suite before commits** - Ensure no regressions
3. **Test on actual devices** - Automated tests + manual review
4. **Keep tests simple** - Focus on class presence, not complex logic
5. **Document failures** - Help future developers understand issues
6. **Update tests with design changes** - Keep tests synchronized with design system

---

## Resources

- [Design System Documentation](../docs/ARMGUARD_DESIGN_SYSTEM.md)
- [Implementation Guide](../docs/ARMGUARD_IMPLEMENTATION_GUIDE.md)
- [Visual Mockups](../docs/ARMGUARD_VISUAL_MOCKUPS.md)
- [Django Testing Documentation](https://docs.djangoproject.com/en/stable/topics/testing/)
- [WCAG Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)

---

**Last Updated:** February 19, 2026  
**Version:** 1.0  
**Maintained by:** 9533 R&D Squadron
