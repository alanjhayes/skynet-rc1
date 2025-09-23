# Skynet RC1 Authentication Configuration

This document describes how to configure authentication for Skynet RC1, including LDAP/Active Directory integration and JWT token authentication.

## Authentication Modes

Skynet RC1 supports flexible authentication with the following configurations:

### 1. Local Users Only (Default)
- **LDAP_ENABLED=false** (default)
- **JWT_ENABLED=true** (default)
- Users authenticate with Django local accounts
- JWT tokens are used for API authentication
- Suitable for small teams or development environments

### 2. LDAP with JWT (Enterprise)
- **LDAP_ENABLED=true**
- **JWT_ENABLED=true**
- Users authenticate with Active Directory credentials
- Falls back to local users if LDAP auth fails
- JWT tokens are used for API authentication
- Suitable for enterprise environments

### 3. LDAP with Sessions (Legacy)
- **LDAP_ENABLED=true**
- **JWT_ENABLED=false**
- Users authenticate with Active Directory credentials
- Falls back to local users if LDAP auth fails
- Django sessions are used for authentication
- Suitable for legacy environments without JWT support

### 4. Local Sessions Only (Minimal)
- **LDAP_ENABLED=false**
- **JWT_ENABLED=false**
- Users authenticate with Django local accounts only
- Django sessions are used for authentication
- Minimal security features

## Configuration Steps

### Step 1: Choose Authentication Mode

Copy the example configuration:
```bash
cp .env.example .env
```

Edit `.env` file and set your authentication mode:

```bash
# For enterprise LDAP + JWT (recommended)
LDAP_ENABLED=true
JWT_ENABLED=true

# For simple local users with JWT
LDAP_ENABLED=false
JWT_ENABLED=true
```

### Step 2: Configure LDAP (if enabled)

If `LDAP_ENABLED=true`, configure these settings in `.env`:

```bash
# LDAP Server Configuration
LDAP_SERVER_URI=ldap://your-ad-server.company.com:389
LDAP_BIND_DN=cn=service-account,ou=service-accounts,dc=company,dc=com
LDAP_BIND_PASSWORD=your-service-account-password

# LDAP Search Configuration
LDAP_USER_BASE=ou=users,dc=company,dc=com
LDAP_USER_FILTER=(sAMAccountName=%(user)s)
LDAP_GROUP_BASE=ou=groups,dc=company,dc=com

# LDAP Group Mappings
LDAP_STAFF_GROUP=cn=skynet-staff,ou=groups,dc=company,dc=com
LDAP_ADMIN_GROUP=cn=skynet-admin,ou=groups,dc=company,dc=com
```

### Step 3: Configure JWT (if enabled)

If `JWT_ENABLED=true`, set a secure secret key:

```bash
# Generate a strong secret key (64+ characters)
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production
```

### Step 4: Set up Active Directory Groups (LDAP only)

Create these groups in your Active Directory:

- **skynet-admin**: Full administrative access
- **skynet-staff**: Staff access (can manage users)
- **skynet-readonly**: Read-only access (cannot upload documents)

### Step 5: Rebuild Containers

After configuration changes, rebuild the containers:

```bash
docker-compose build frontend document
docker-compose up -d
```

## User Permissions

### Role-Based Permissions

| Permission | Admin | Staff | User | Readonly |
|------------|-------|-------|------|----------|
| Upload documents | ✅ | ✅ | ✅ | ❌ |
| View own documents | ✅ | ✅ | ✅ | ✅ |
| View all documents | ✅ | ❌ | ❌ | ❌ |
| Delete any document | ✅ | ❌ | ❌ | ❌ |
| Delete own documents | ✅ | ✅ | ✅ | ❌ |
| Manage users | ✅ | ✅ | ❌ | ❌ |
| View audit logs | ✅ | ❌ | ❌ | ❌ |

### User Isolation

- **Document Collections**: Each user has their own Qdrant collection (`user_username_documents`)
- **Audit Logging**: All document access is logged with user information
- **API Security**: All API endpoints require authentication and validate user permissions

## Security Features

### JWT Token Security
- **Access Tokens**: 60-minute expiration
- **Refresh Tokens**: 7-day expiration with rotation
- **Token Blacklisting**: Logout invalidates refresh tokens
- **Automatic Refresh**: Frontend automatically refreshes tokens

### LDAP Security
- **Secure Binding**: Service account for LDAP queries
- **Group Mapping**: AD groups mapped to Django permissions
- **Fallback Authentication**: Local users available if LDAP fails
- **Group Caching**: LDAP groups cached for 1 hour

### Additional Security
- **CSRF Protection**: All forms protected against CSRF attacks
- **Security Headers**: XSS protection and content type sniffing prevention
- **Audit Trail**: Complete logging of user actions
- **Permission Checks**: Document-level access control

## Troubleshooting

### LDAP Connection Issues

1. **Check LDAP server connectivity**:
   ```bash
   docker exec skynet-rc1-frontend python manage.py shell
   >>> import ldap
   >>> conn = ldap.initialize('ldap://your-server:389')
   >>> conn.simple_bind_s('cn=service,ou=users,dc=company,dc=com', 'password')
   ```

2. **Verify LDAP settings**:
   - Ensure `LDAP_BIND_DN` has read access to user and group containers
   - Verify `LDAP_USER_FILTER` matches your AD schema
   - Check `LDAP_USER_BASE` and `LDAP_GROUP_BASE` paths

3. **Test user authentication**:
   ```bash
   # Check Django logs for LDAP authentication attempts
   docker logs skynet-rc1-frontend | grep -i ldap
   ```

### JWT Issues

1. **Token validation errors**:
   - Ensure `JWT_SECRET_KEY` is consistent across services
   - Check token expiration times in browser developer tools
   - Verify API endpoints are using correct authentication headers

2. **Missing JWT packages**:
   ```bash
   # Rebuild containers to install JWT dependencies
   docker-compose build frontend
   ```

### Permission Issues

1. **Users can't upload documents**:
   - Check user's role assignment in LDAP groups
   - Verify `LDAP_STAFF_GROUP` and `LDAP_ADMIN_GROUP` settings
   - Check document service permissions in logs

2. **Access denied errors**:
   - Review audit logs in `document_audit_log` table
   - Check user's group memberships
   - Verify JWT token contains correct user information

## Login URLs

- **Universal Login**: `/auth/login/` (recommended)
- **Legacy Login**: `/login/` (Django admin style)
- **API Login**: `/api/auth/login/` (for API clients)

## API Authentication

### Using JWT Tokens

```javascript
// Get access token from login
const response = await fetch('/api/auth/login/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'user', password: 'pass' })
});
const { access, refresh } = await response.json();

// Use token in API calls
const apiResponse = await fetch('/frontend/upload/', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${access}` },
    body: formData
});
```

### Using Session Authentication

```javascript
// Login with credentials (sets session cookie)
const response = await fetch('/api/auth/login/', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'user', password: 'pass' })
});

// Use session in API calls
const apiResponse = await fetch('/frontend/upload/', {
    method: 'POST',
    credentials: 'include',
    body: formData
});
```

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `LDAP_ENABLED` | `false` | Enable/disable LDAP authentication |
| `JWT_ENABLED` | `true` | Enable/disable JWT token authentication |
| `LDAP_SERVER_URI` | - | LDAP server URL |
| `LDAP_BIND_DN` | - | Service account DN for LDAP binding |
| `LDAP_BIND_PASSWORD` | - | Service account password |
| `LDAP_USER_BASE` | - | Base DN for user searches |
| `LDAP_USER_FILTER` | `(sAMAccountName=%(user)s)` | LDAP user search filter |
| `LDAP_GROUP_BASE` | - | Base DN for group searches |
| `LDAP_STAFF_GROUP` | - | LDAP group for staff permissions |
| `LDAP_ADMIN_GROUP` | - | LDAP group for admin permissions |
| `JWT_SECRET_KEY` | `SECRET_KEY` | Secret key for JWT token signing |

## Migration from Basic to LDAP

1. **Export existing users** (optional):
   ```bash
   docker exec skynet-rc1-frontend python manage.py dumpdata auth.user > users_backup.json
   ```

2. **Configure LDAP settings** in `.env`

3. **Rebuild containers**:
   ```bash
   docker-compose build frontend
   docker-compose up -d
   ```

4. **Test LDAP authentication** with existing AD users

5. **Migrate local users to LDAP** or keep as fallback accounts

The system will gracefully handle mixed authentication scenarios where some users authenticate via LDAP and others use local accounts.