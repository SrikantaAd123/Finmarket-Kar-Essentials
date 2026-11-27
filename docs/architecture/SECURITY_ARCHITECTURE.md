
# Finmarket Kart Essentials – Security Architecture

## 1. Introduction

Security is an important part of the Finmarket Kart Essentials backend.

The application uses authentication, authorization, request validation, database constraints, and secure configuration practices to protect application resources.

The security architecture covers:

- User authentication.
- JWT validation.
- Role-based authorization.
- API endpoint protection.
- Database security.
- Payment security.
- Environment variable management.
- Application deployment security.
- Error handling and logging.

## 2. Security Technology Stack

| Component | Technology |
| --- | --- |
| Backend Framework | FastAPI |
| Authentication Provider | ZITADEL |
| Token Format | JWT |
| JWT Algorithm | RS256 |
| Token Signing Keys | ZITADEL JWKS |
| Database | MySQL |
| ORM | SQLAlchemy |
| Request Validation | Pydantic |
| Payment Provider | Razorpay |
| Deployment | Docker |

## 3. Authentication Architecture

The application uses ZITADEL for identity management and JWT-based authentication.

The backend validates access tokens rather than managing user passwords directly.

The authentication implementation is maintained in:

```text
backend/auth/
├── zitadel.py
└── dependencies.py
```

### 3.1 Authentication Flow

The authentication process follows these steps:

1. The user authenticates through the configured identity provider.
2. ZITADEL issues an access token.
3. The client sends the token to the backend.
4. FastAPI receives the request.
5. The authentication dependency extracts the Bearer token.
6. The backend validates the JWT signature and claims.
7. The authenticated user information becomes available to the protected endpoint.
8. The endpoint performs the requested operation if authorization succeeds.

### 3.2 Authorization Header

Protected API requests use the Bearer authentication scheme.

Example:

```http
Authorization: Bearer YOUR_ACCESS_TOKEN
```

The access token must be obtained through the configured authentication flow.

## 4. JWT Validation

The backend validates JWT access tokens using the configured ZITADEL issuer and public signing keys.

The validation implementation includes:

- JWT signature verification.
- Issuer validation.
- Audience validation.
- Expiration validation.
- Issued-at claim validation.
- Subject claim validation.
- Supported signing algorithm validation.

### 4.1 Signing Algorithm

The application uses:

```text
RS256
```

The backend uses the public signing keys provided through the ZITADEL JSON Web Key Set endpoint.

### 4.2 JWKS Endpoint

The public key endpoint follows this format:

```text
{ZITADEL_ISSUER}/oauth/v2/keys
```

The backend uses the configured issuer to retrieve the signing keys.

### 4.3 Token Claims

Important JWT claims include:

| Claim | Purpose |
| --- | --- |
| `iss` | Identifies the token issuer |
| `aud` | Identifies the intended audience |
| `exp` | Token expiration timestamp |
| `iat` | Token issuance timestamp |
| `sub` | Authenticated subject identifier |

The backend must reject invalid, expired, or incorrectly signed tokens.

## 5. Authorization Architecture

Authentication verifies who is making a request.

Authorization determines whether the authenticated user is permitted to perform the requested operation.

The application uses authentication dependencies and administrative role checks to protect API functionality.

### 5.1 Customer Authorization

Customer endpoints require an authenticated customer.

The backend resolves the authenticated customer through the configured customer dependency.

Customer operations should be restricted to resources belonging to the authenticated customer.

### 5.2 Administrative Authorization

Administrative endpoints require appropriate administrative permissions.

The authorization implementation uses the configured role or claim information.

Administrative operations must not be accessible to ordinary customer accounts.

### 5.3 Resource Ownership

The backend must verify resource ownership when accessing customer-specific information.

For example:

- Customers should access their own orders.
- Customers should access their own order tracking information.
- Customers should not retrieve another customer's private order details.
- Administrative operations should require appropriate authorization.

## 6. API Security

FastAPI provides dependency injection and request validation mechanisms that support API security.

Security controls include:

- Authentication dependencies.
- Authorization checks.
- Request schema validation.
- Path parameter validation.
- Query parameter validation.
- Business rule validation.
- Controlled HTTP error responses.

Protected endpoints must use the appropriate authentication dependencies.

Sensitive administrative operations must use administrative authorization.

## 7. Input Validation

The application uses Pydantic schemas to validate request data.

Validation should be applied to:

- Customer input.
- Order checkout information.
- Payment information.
- Inventory quantities.
- Delivery information.
- Administrative requests.

Validation should reject malformed data before it reaches database operations.

SQLAlchemy parameterized queries should be used for database access instead of manually constructing SQL with untrusted input.

## 8. Database Security

The application uses MySQL and SQLAlchemy ORM.

Database security requirements include:

1. Store database credentials in environment variables.
2. Never commit database passwords to source control.
3. Use a dedicated database account for the application.
4. Grant only the permissions required by the application.
5. Restrict database network access.
6. Use secure database connections where supported.
7. Apply database constraints to maintain data integrity.
8. Back up important database information securely.

### 8.1 Database Configuration

An example database URL format is:

```env
DATABASE_URL=mysql+pymysql://USER:PASSWORD@HOST:3306/DATABASE_NAME
```

The actual connection configuration must match the project's database connection implementation.

### 8.2 Database Access

Database operations are performed through SQLAlchemy sessions and repository classes.

Repositories should use parameterized SQLAlchemy expressions and avoid unsafe query construction.

## 9. Payment Security

The application supports Razorpay and Cash on Delivery.

Payment security is especially important because payment operations involve financial transactions.

Security requirements include:

- Keep Razorpay secrets on the backend.
- Never expose private payment credentials to the frontend.
- Verify payment signatures on the backend.
- Validate transaction amounts against trusted order data.
- Verify webhook signatures before processing events.
- Use idempotency protection for retryable payment operations.
- Record payment failures appropriately.
- Restrict refund operations.
- Avoid logging sensitive payment information.

### 9.1 Razorpay Credentials

Payment credentials should be supplied through secure environment configuration.

Example variable names:

```env
RAZORPAY_KEY_ID=your_key_id
RAZORPAY_KEY_SECRET=your_key_secret
```

Use actual credentials only in the local environment or a secure production secret manager.

Never commit real credentials to Git.

### 9.2 Webhook Verification

Payment webhook requests must be verified before processing.

The backend should validate the provider signature using the configured webhook secret.

Unverified webhook events must not be trusted to change payment or order state.

## 10. Environment Variable Security

Application secrets and configuration values should be stored outside the source code.

Examples include:

| Configuration | Purpose |
| --- | --- |
| `DATABASE_URL` | Database connection |
| `ZITADEL_ISSUER` | ZITADEL issuer |
| `ZITADEL_PROJECT_ID` | ZITADEL project configuration |
| `ZITADEL_SCOPES` | Configured identity scopes |
| `RAZORPAY_KEY_ID` | Razorpay public key identifier |
| `RAZORPAY_KEY_SECRET` | Razorpay private secret |
| `RAZORPAY_WEBHOOK_SECRET` | Webhook signature verification |

The actual environment variable names must match the application configuration code.

### 10.1 Git Protection

The following files should not be committed when they contain real secrets:

```text
.env
.env.local
.env.production
.streamlit/secrets.toml
```

A suitable `.gitignore` should exclude local secret files.

## 11. CORS Security

Cross-Origin Resource Sharing controls which browser origins can access the backend.

The application should configure CORS according to the frontend environments.

Recommended practices:

- Allow only trusted frontend origins.
- Avoid unrestricted origins in production.
- Configure allowed HTTP methods appropriately.
- Configure allowed headers appropriately.
- Enable credentials only when required.
- Keep development and production CORS settings separate.

CORS is a browser security mechanism. It does not replace authentication or authorization.

## 12. Error Handling and Information Protection

Error responses should provide useful information without exposing sensitive implementation details.

The application should avoid returning:

- Database credentials.
- Access tokens.
- Private signing keys.
- Payment secrets.
- Internal stack traces.
- Sensitive customer information.

Detailed exceptions should be recorded in controlled application logs.

## 13. Logging and Monitoring

Logging helps identify application errors and suspicious activity.

Recommended monitoring information includes:

- Authentication failures.
- Authorization failures.
- Payment failures.
- API errors.
- Database connectivity errors.
- Unexpected application exceptions.
- Administrative operations.

Sensitive information must be excluded from logs.

Access to production logs should be restricted to authorized personnel.

## 14. Docker Deployment Security

The application uses Docker for deployment.

Recommended Docker security practices include:

1. Use trusted base images.
2. Keep dependencies updated.
3. Avoid storing secrets in Docker images.
4. Supply secrets through secure runtime configuration.
5. Expose only required network ports.
6. Restrict container permissions.
7. Avoid running production containers as root where possible.
8. Keep production configuration separate from development configuration.

## 15. Backup and Recovery Security

Database backups should be protected against unauthorized access.

Recommended practices include:

- Encrypt backups where supported.
- Restrict backup access.
- Store backups separately from the application host.
- Maintain backup retention policies.
- Test recovery procedures.
- Monitor backup completion.

## 16. Security Checklist

The following checklist can be used during deployment reviews.

- [ ] JWT signature verification is enabled.
- [ ] JWT issuer and audience validation are configured.
- [ ] Expired tokens are rejected.
- [ ] Customer endpoints require authentication.
- [ ] Administrative endpoints require authorization.
- [ ] Customer resource ownership is checked.
- [ ] Database credentials are not committed.
- [ ] Razorpay secrets are protected.
- [ ] Payment signatures are verified.
- [ ] Webhook signatures are verified.
- [ ] Idempotency is applied to appropriate payment operations.
- [ ] Production CORS origins are restricted.
- [ ] Sensitive information is excluded from logs.
- [ ] HTTPS is enabled in production.
- [ ] Database backups are protected.
- [ ] Docker deployment secrets are supplied securely.

## 17. Security Architecture Summary

Finmarket Kart Essentials uses a layered security architecture.

| Security Area | Main Responsibility |
| --- | --- |
| ZITADEL | Identity and token issuance |
| JWT Validation | Access token verification |
| FastAPI Dependencies | Authentication and authorization |
| Pydantic | Request validation |
| SQLAlchemy | Database access |
| MySQL | Persistent data storage |
| Razorpay | Online payment processing |
| Docker | Application containerization |

Security controls should be reviewed regularly as application functionality and deployment requirements evolve.

---

**Project:** Finmarket Kart Essentials

**Document:** Security Architecture

**Version:** 1.0.0
