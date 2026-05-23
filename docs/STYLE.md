# LEAP Style Guide

This document outlines the coding style and conventions used in this Flask template.

## Python Style

### Functions
- Use clear Subject-Verb-Object names
- Keep functions short and focused
- Add Google-style docstrings with Args, Returns, and Raises sections
- One job per function

### Imports
- Import only what you use
- Order: standard library, third-party, local
- Remove unused imports

### Structure
- Every script has `if __name__ == "__main__":`
- Use functions over inline code
- Keep modules single-purpose

### DataFrames
- Avoid multi-level columns
- Use clean, simple column names

## Plot Styling (Kyle Style)

### Matplotlib Configuration
- Use serif fonts only
- Remove top and right spines
- Offset left and bottom spines outward
- X-axis uses 50-year intervals including the final year
- Y-axis shows mean, 20%, and 80% percentiles
- Data points marked with subtle black and white markers
- Always call `plt.savefig()` before `plt.show()`

### Plot Elements
- Black lines and markers
- Gray reference lines (mean, percentiles)
- Clean, minimal design
- Consistent sizing and spacing

## Flask Structure

### Blueprints
- Use Blueprints for organization
- Keep routes thin
- Put business logic in `app/services/`
- Put styling in `app/style/` and `app/static/css/`

### Templates
- Use base template for layout
- Keep templates clean and readable
- Use Jinja2 macros for reusable components

### Static Files
- CSS in `app/static/css/site.css`
- Images in `app/static/img/`
- Avoid inline styles

## Writing Style

### Documentation
- Short Subject-Verb-Object sentences
- No gerunds
- No subordinate clauses
- Clear and concise

### Comments
- Explain why, not what
- Use docstrings for functions and classes
- Keep comments up to date

## File Organization

### Services
- One service per file
- Pure Python classes when possible
- Keep Flask dependencies minimal

### Templates
- One template per page
- Use template inheritance
- Keep logic out of templates

### Static Assets
- Organized by type (css, img, js)
- Minified for production
- Versioned for cache busting

## Error Handling

### Exceptions
- Catch specific exceptions
- Log errors appropriately
- Return meaningful error messages
- Fail gracefully

### Validation
- Validate input data
- Use appropriate HTTP status codes
- Provide helpful error messages

## Testing

### Test Structure
- One test file per module
- Test both success and failure cases
- Use descriptive test names
- Mock external dependencies

### Coverage
- Aim for high test coverage
- Test critical paths
- Test error conditions
- Test edge cases

## Security

### Best Practices
- Never commit secrets
- Use environment variables
- Validate all input
- Use HTTPS in production
- Implement proper authentication

### Databricks
- Use Personal Access Tokens
- Rotate tokens regularly
- Follow principle of least privilege
- Monitor access logs

## Performance

### Optimization
- Use connection pooling
- Cache expensive operations
- Minimize database queries
- Optimize static assets

### Monitoring
- Log important events
- Monitor response times
- Track error rates
- Set up alerts

## Deployment

### Environment
- Use environment variables for configuration
- Separate development and production settings
- Use proper logging levels
- Implement health checks
