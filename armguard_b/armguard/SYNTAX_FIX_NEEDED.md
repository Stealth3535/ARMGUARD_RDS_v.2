# Test Python syntax compilation results

## Personnel Model Fix Needed

The personnel/models.py file has syntax errors due to literal `\n` characters instead of actual newlines.

### Error Location:
Line 204 in personnel/models.py contains literal newline characters that need to be converted to actual line breaks.

### Fix Required:
The clean() method section needs to be rewritten with proper line breaks instead of literal `\n` characters.

This is preventing Django from loading and all tests from running.