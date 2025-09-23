// JWT Authentication utilities for Skynet RC1

class SkynetAuth {
    constructor() {
        this.accessTokenKey = 'access_token';
        this.refreshTokenKey = 'refresh_token';
        this.userInfoKey = 'user_info';
    }

    // Get access token
    getAccessToken() {
        return localStorage.getItem(this.accessTokenKey);
    }

    // Get refresh token
    getRefreshToken() {
        return localStorage.getItem(this.refreshTokenKey);
    }

    // Get user info
    getUserInfo() {
        const userInfo = localStorage.getItem(this.userInfoKey);
        return userInfo ? JSON.parse(userInfo) : null;
    }

    // Set tokens
    setTokens(accessToken, refreshToken, userInfo = null) {
        localStorage.setItem(this.accessTokenKey, accessToken);
        localStorage.setItem(this.refreshTokenKey, refreshToken);
        if (userInfo) {
            localStorage.setItem(this.userInfoKey, JSON.stringify(userInfo));
        }
    }

    // Clear tokens (logout)
    clearTokens() {
        localStorage.removeItem(this.accessTokenKey);
        localStorage.removeItem(this.refreshTokenKey);
        localStorage.removeItem(this.userInfoKey);
    }

    // Check if user is authenticated
    isAuthenticated() {
        return !!this.getAccessToken();
    }

    // Get authorization headers
    getAuthHeaders() {
        const token = this.getAccessToken();
        return token ? {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        } : {
            'Content-Type': 'application/json'
        };
    }

    // Refresh access token
    async refreshAccessToken() {
        const refreshToken = this.getRefreshToken();
        if (!refreshToken) {
            this.logout();
            return null;
        }

        try {
            const response = await fetch('/api/auth/refresh/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': SkynetRC1.getCSRFToken()
                },
                body: JSON.stringify({
                    refresh: refreshToken
                })
            });

            if (response.ok) {
                const data = await response.json();
                localStorage.setItem(this.accessTokenKey, data.access);
                return data.access;
            } else {
                this.logout();
                return null;
            }
        } catch (error) {
            console.error('Token refresh failed:', error);
            this.logout();
            return null;
        }
    }

    // Make authenticated API call with automatic token refresh
    async apiCall(url, options = {}) {
        let headers = {
            ...this.getAuthHeaders(),
            ...options.headers
        };

        let response = await fetch(url, {
            ...options,
            headers
        });

        // If token expired, try to refresh
        if (response.status === 401) {
            const newToken = await this.refreshAccessToken();
            if (newToken) {
                headers['Authorization'] = `Bearer ${newToken}`;
                response = await fetch(url, {
                    ...options,
                    headers
                });
            }
        }

        return response;
    }

    // Logout
    async logout() {
        const refreshToken = this.getRefreshToken();
        
        // Try to blacklist the refresh token
        if (refreshToken) {
            try {
                await fetch('/api/auth/logout/', {
                    method: 'POST',
                    headers: this.getAuthHeaders(),
                    body: JSON.stringify({
                        refresh: refreshToken
                    })
                });
            } catch (error) {
                console.error('Logout API call failed:', error);
            }
        }

        this.clearTokens();
        window.location.href = '/auth/login/';
    }

    // Check authentication status and redirect if needed
    requireAuth() {
        if (!this.isAuthenticated()) {
            window.location.href = '/auth/login/';
            return false;
        }
        return true;
    }

    // Initialize authentication check for protected pages
    init() {
        // Update navbar based on authentication status
        this.updateNavbar();
        
        // Check if user is authenticated on protected pages
        const protectedPaths = ['/', '/documents/', '/chat/'];
        const currentPath = window.location.pathname;
        
        if (protectedPaths.includes(currentPath) && !this.isAuthenticated()) {
            window.location.href = '/auth/login/';
            return;
        }

        // Set up automatic token refresh
        this.setupTokenRefresh();
    }

    // Update navbar based on authentication status
    updateNavbar() {
        const navbarContent = document.getElementById('navbar-content');
        if (!navbarContent) return;

        if (this.isAuthenticated()) {
            const userInfo = this.getUserInfo();
            navbarContent.innerHTML = `
                <a class="nav-link" href="/chat/">
                    <i class="fas fa-comments"></i> Chat
                </a>
                <a class="nav-link" href="/documents/">
                    <i class="fas fa-file-alt"></i> Documents
                </a>
                <a class="nav-link" href="#" onclick="SkynetAuth.logout()">
                    <i class="fas fa-sign-out-alt"></i> Logout (${userInfo ? userInfo.username : 'User'})
                </a>
            `;
        } else {
            navbarContent.innerHTML = `
                <a class="nav-link" href="/auth/login/">
                    <i class="fas fa-sign-in-alt"></i> Login
                </a>
            `;
        }
    }

    // Set up automatic token refresh
    setupTokenRefresh() {
        if (!this.isAuthenticated()) return;

        // Refresh token every 50 minutes (tokens expire in 60 minutes)
        setInterval(async () => {
            await this.refreshAccessToken();
        }, 50 * 60 * 1000);
    }

    // Decode JWT payload (for debugging/info only - don't trust this for security)
    decodeToken(token) {
        try {
            const base64Url = token.split('.')[1];
            const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
            const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
                return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
            }).join(''));
            return JSON.parse(jsonPayload);
        } catch (error) {
            return null;
        }
    }
}

// Create global auth instance
window.SkynetAuth = new SkynetAuth();

// Initialize authentication when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    SkynetAuth.init();
});