# Changelog

All notable changes to the QUANTARA web application are documented
in this file. Dates are in YYYY-MM-DD format.

## 2026-06-12

### Fixed
- **#29**: Removed duplicate FastAPI application instance in
  `web_app/api/referal.py`. The module was creating its own
  `FastAPI()` instance and calling `app.include_router(router)`,
  which was unused since the main application already includes
  the referal router.
- **#31**: Changed `liquidate_position` and `get_position_by_id`
  parameter type from `int` to `UUID`, aligning with the Position
  model's primary key type. Updated callers in
  `contract_tools/mixins/dashboard.py` accordingly.
- **#25**: Added a global exception handler in `web_app/api/main.py`
  that masks internal exception details (stack traces, database
  errors, file paths) from API consumers. Also updated the
  `get_stats` endpoint in `web_app/api/user.py` to return a
  sanitized 500 response.

### Added
- **#32**: Added a `NotFound` page component and catch-all 404
  route in `quantara/frontend/src/App.jsx`. Users navigating to
  an undefined path now see a friendly 404 message with a link
  back to the home page instead of a blank page.
- **#34**: Added `web_app/config_validator.py` to validate required
  environment variables at application startup. The app fails fast
  with a clear error message in production if any required variable
  is missing. Added `docs/environment_variables.md` documenting the
  required and optional variables.

### Tests
- Added `web_app/tests/test_exception_handler.py` covering the
  global exception handler behaviour.
- Added `web_app/tests/test_config_validator.py` covering the
  startup configuration validator.
- Added `frontend/src/pages/not-found/NotFound.test.jsx` and
  `frontend/src/pages/not-found/NotFound.integration.test.jsx`
  covering the new 404 page and route.
