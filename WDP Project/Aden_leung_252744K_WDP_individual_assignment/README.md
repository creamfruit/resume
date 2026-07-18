# Re:Connect SG

## Authentication Routing
- API authentication is centralized in `views/routes/user_routes.py` (`/api/users/login`, `/api/users/logout`, `/api/users/current`).
- HTML login/logout pages remain in `views/routes/auth_routes.py` (`/login`, `/logout`) for form-based access.
