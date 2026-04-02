# Personal Finance Tracker (Flask + MySQL)

Backend for a finance dashboard with REST APIs and role-based access control (RBAC).

## Features

- Role-based access control with 3 roles: `admin`, `analyst`, `viewer`
- Users CRUD
- Financial records CRUD (admin only)
- Summary/analytics endpoints (income, expense, balance, category totals)
- Validation + consistent JSON error responses
- JWT minting endpoint for easier Postman testing

## Tech Stack

- Flask (REST APIs)
- MySQL (persistence)
- `mysql-connector-python` (DB driver)
- `flask-cors` (CORS)
- `python-dotenv` (environment config)
- `PyJWT` (JWT support)

## Project Structure

- `app.py`: Flask app + JSON error handlers + `POST /auth/token` 
- `db.py`: MySQL connection + `init_db()` table creation
- `routes/`: REST endpoints
  - `users.py`
  - `records.py`
  - `summary.py`
- `middleware/`: RBAC + JWT helpers
  - `auth.py`
- `static/dashboard.html`: optional browser dashboard (calls `/summary/*` and `/records`)

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment variables

Update `.env` with your MySQL credentials:

- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`
- `JWT_SECRET` (used to sign tokens in the flow)

### 3. Ensure the database exists

`db.py` creates tables, but it expects `DB_NAME` to already exist in MySQL.

Example:

```sql
CREATE DATABASE finance_tracker;
```

### 4. Run the server

```bash
python app.py
```

The server listens on `PORT` (default `5000`).

### Web dashboard (optional UI)

Open in your browser:

- `http://127.0.0.1:5000/` or `http://127.0.0.1:5000/dashboard`

The page loads summary totals and records using the same REST APIs. Use the **Role** dropdown to see RBAC behavior (e.g. viewer cannot call income/expense totals).

## RBAC Model

RBAC is enforced by `authorize(allowed_roles)`:

- Reads `role` from the request headers
- If `role` is missing: returns `401`
- If `role` is not allowed for the endpoint: returns `403`

Role capabilities:

- `admin`: full access to users + record CRUD + analytics
- `analyst`: can view records + analytics (`income`/`expense` only)
- `viewer`: read-only analytics + records list

## JWT Flow (for `POST /records`)

`POST /records` requires:

- Header `role: admin` (RBAC)
- Header `Authorization: Bearer <token>` (JWT)

JWT is minted via:

### `POST /auth/token` 

Header:
- `role: admin | analyst | viewer`

Body:

```json
{ "email": "user@example.com" }
```

Rules:
- JWT `sub` claim is the user's `id`
- JWT minting verifies the request `role` matches the stored user role

Response:

```json
{ "access_token": "..." }
```

## API Endpoints

### Users

`POST /users`
- Allowed role: `admin`
- Body: `name`, `email`, `role` (required), optional `status`

`GET /users`
- Allowed roles: `admin`, `analyst`, `viewer`

### Records

`POST /records`
- Allowed role: `admin`
- Requires `Authorization: Bearer <token>`
- Body: `amount` (positive), `type` (`income`|`expense`), `category`, `date` (YYYY-MM-DD), optional `note`

`GET /records`
- Allowed roles: `admin`, `analyst`, `viewer`
- Optional query params: `user_id`, `type`, `category`, `start_date`, `end_date`

`PUT /records/<id>`
- Allowed role: `admin`
- Body validation same as `POST /records`

`DELETE /records/<id>`
- Allowed role: `admin`

### Summary / Dashboard

`GET /summary/income`
- Allowed roles: `admin`, `analyst`

`GET /summary/expense`
- Allowed roles: `admin`, `analyst`

`GET /summary/balance`
- Allowed roles: `admin`, `analyst`, `viewer`

`GET /summary/category`
- Allowed roles: `admin`, `analyst`, `viewer`
- Returns `income_by_category` and `expense_by_category`

## Postman Quick Test

### Create an admin user

1. Header: `role: admin`
2. Body:

```json
{
  "name": "Alice Admin",
  "email": "alice@example.com",
  "role": "admin"
}
```

3. Request: `POST /users`

### Mint JWT

1. Header: `role: admin`
2. Body: `{ "email": "alice@example.com" }`
3. Request: `POST /auth/token`

### Create a record

1. Header: `role: admin`
2. Header: `Authorization: Bearer <access_token>`
3. Body:

```json
{
  "amount": 1200.50,
  "type": "income",
  "category": "Salary",
  "date": "2026-04-02",
  "note": "April salary"
}
```

4. Request: `POST /records`

## Notes / Assumptions

- `amount` is stored as a positive number for both `income` and `expense`
- Summary calculations compute net balance as `income - expense`
- `init_db()` creates the tables automatically on app startup


- **User and role management:** Implemented in `routes/users.py` with user creation/listing, role assignment (`admin`, `analyst`, `viewer`), and status handling.
- **Financial records management:** Implemented in `routes/records.py` with create/read/update/delete and filtering by `user_id`, `type`, `category`, `start_date`, `end_date`.
- **Dashboard summary APIs:** Implemented in `routes/summary.py` for total income, total expense, net balance, and category-wise totals.
- **Access control logic:** Implemented in `middleware/auth.py` via role-based authorization checks; JWT verification added for protected record creation flow.
- **Validation and error handling:** Input validation and clear JSON error responses are used across routes with appropriate HTTP status codes.
- **Data persistence:** MySQL persistence via `db.py` and automatic table initialization through `init_db()` on app startup.

