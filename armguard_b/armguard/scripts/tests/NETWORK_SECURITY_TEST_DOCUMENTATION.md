# Network Security Test Documentation

## Overview

The `test_network_security.py` script provides comprehensive testing for ArmGuard's military-grade LAN/WAN hybrid security architecture implementation.

## Test Categories

### 1. Network Type Detection Tests
- **Purpose**: Validate automatic network type detection based on server ports
- **Tests**: LAN port (8443), WAN port (443), unknown port defaults
- **Coverage**: Core network identification functionality

### 2. LAN-Only Access Tests
- **Purpose**: Ensure sensitive operations are restricted to LAN access
- **Tests**: Admin panel access, transaction creation, user registration
- **Coverage**: Critical security enforcement

### 3. WAN Read-Only Tests
- **Purpose**: Verify status checking operations work via WAN
- **Tests**: Personnel viewing, inventory viewing, report access
- **Coverage**: External access functionality

### 4. Middleware Tests
- **Purpose**: Validate middleware components function correctly
- **Tests**: NetworkBasedAccessMiddleware, UserRoleNetworkMiddleware
- **Coverage**: Core security infrastructure

### 5. Decorator Tests
- **Purpose**: Ensure security decorators work as expected
- **Tests**: @lan_required, @read_only_on_wan, @network_aware_permission_required
- **Coverage**: View-level security controls

### 6. Role-Based Network Tests
- **Purpose**: Verify user role network restrictions
- **Tests**: Admin WAN blocking, staff dual access, user WAN-only
- **Coverage**: Military role-based security

### 7. Template Context Tests
- **Purpose**: Validate network-aware template functionality
- **Tests**: Context processor integration, network variable availability
- **Coverage**: UI security integration

### 8. Security Integration Tests
- **Purpose**: Test complete security stack
- **Tests**: Full middleware stack, security logging, session management
- **Coverage**: End-to-end security validation

### 9. Configuration Tests
- **Purpose**: Verify all security settings are properly configured
- **Tests**: Port configuration, path restrictions, role settings
- **Coverage**: Configuration validation

## Usage Instructions

### Running Individual Tests

```bash
# Run specific test class
python manage.py test scripts.tests.test_network_security.NetworkTypeDetectionTest

# Run specific test method
python manage.py test scripts.tests.test_network_security.NetworkTypeDetectionTest.test_lan_port_detection

# Run all network security tests
python manage.py test scripts.tests.test_network_security
```

### Running Comprehensive Test Suite

```bash
# Run standalone comprehensive test
cd /path/to/armguard
python scripts/tests/test_network_security.py

# Or run with Django test runner
python manage.py test scripts.tests.test_network_security --pattern="test_network_security.py"
```

### Running with Coverage

```bash
# Install coverage if not already installed
pip install coverage

# Run with coverage analysis
coverage run --source='.' manage.py test scripts.tests.test_network_security
coverage report -m
coverage html
```

## Test Data Requirements

The test suite automatically creates:
- Test users (admin, staff, regular)
- Test groups and permissions
- Sample personnel records
- Mock network requests

No external test data files required.

## Expected Test Results

### Successful Test Run Output

```
================================================================================
ArmGuard Network Security Implementation Test Suite
================================================================================

1. Testing Configuration...
   ✅ Network ports configured correctly
   ✅ LAN-only paths configured correctly
   ✅ WAN read-only paths configured correctly
   ✅ Role network restrictions configured correctly

2. Testing Network Detection...
   ✅ LAN port detection working
   ✅ WAN port detection working
   ✅ Unknown port defaults working

3. Testing Middleware...
   ✅ Network-based access middleware working
   ✅ User role network middleware working

4. Testing Decorators...
   ✅ @lan_required decorator working
   ✅ @read_only_on_wan decorator working

5. Testing Role-Based Access...
   ✅ Admin WAN restriction working
   ✅ Staff dual access working
   ✅ Regular user WAN-only restriction working

6. Testing Template Context...
   ✅ Network context processor working

================================================================================
Network Security Test Suite Complete
================================================================================

Security Implementation Status:
✅ LAN/WAN network detection
✅ Path-based access control
✅ Role-based network restrictions
✅ Middleware integration
✅ Decorator application
✅ Template context integration
✅ Configuration management

🔒 Military-grade network security architecture is OPERATIONAL
```

## Troubleshooting

### Common Test Failures

#### Network Detection Issues
```
❌ LAN port detection failed: AttributeError: 'MagicMock' object has no attribute 'is_lan_access'
```
**Solution**: Ensure middleware is properly installed and configured in settings.py

#### Configuration Missing
```
❌ Network ports configuration failed: AttributeError: 'Settings' object has no attribute 'NETWORK_PORTS'
```
**Solution**: Add network security settings to core/settings.py

#### Import Errors
```
❌ ImportError: No module named 'core.network_middleware'
```
**Solution**: Ensure all network security modules are created and properly imported

#### Database Issues
```
❌ Database error during test setup
```
**Solution**: Run migrations and ensure test database is properly configured

### Debug Mode

To run tests in debug mode with detailed output:

```python
# Add to test file
import logging
logging.basicConfig(level=logging.DEBUG)

# Or set environment variable
export DJANGO_LOG_LEVEL=DEBUG
```

### Manual Verification

After tests pass, manually verify:

1. **LAN Access (Port 8443)**:
   ```bash
   curl -k https://armguard.local:8443/admin/
   # Should allow access to admin functions
   ```

2. **WAN Access (Port 443)**:
   ```bash
   curl -k https://armguard.example.com:443/admin/
   # Should block admin access
   
   curl -k https://armguard.example.com:443/personnel/
   # Should allow read-only access
   ```

## Security Validation Checklist

After running tests, verify:

- [ ] All test categories pass
- [ ] Network detection works correctly
- [ ] LAN-only operations are properly restricted
- [ ] WAN read-only operations function correctly
- [ ] Role-based restrictions are enforced
- [ ] Middleware is functioning
- [ ] Decorators are applied correctly
- [ ] Template context is working
- [ ] Configuration is complete
- [ ] Security logging is active

## Integration with CI/CD

### GitHub Actions Integration

```yaml
name: Network Security Tests
on: [push, pull_request]

jobs:
  security-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run network security tests
        run: python manage.py test scripts.tests.test_network_security
```

### Pre-deployment Validation

```bash
#!/bin/bash
# pre_deploy_security_check.sh

echo "Running network security validation..."
python scripts/tests/test_network_security.py

if [ $? -eq 0 ]; then
    echo "✅ Security tests passed - deployment approved"
    exit 0
else
    echo "❌ Security tests failed - deployment blocked"
    exit 1
fi
```

## Continuous Monitoring

### Security Test Schedule

- **Pre-commit**: Run decorator and configuration tests
- **Daily**: Full security test suite
- **Weekly**: Integration tests with real network conditions
- **Monthly**: Comprehensive security audit including penetration testing

### Alerting

Set up monitoring to alert on:
- Security test failures
- Network access violations
- Configuration drift
- Unauthorized access attempts

---

**Test Suite Version**: 1.0  
**Last Updated**: February 1, 2026  
**Classification**: Internal Use  
**Approved By**: ArmGuard Security Team