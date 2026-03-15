// Simple auth utility for Super Admin (token in localStorage)
export function login(token) {
  localStorage.setItem('superadmin_token', token);
}

export function logout() {
  localStorage.removeItem('superadmin_token');
}

export function isAuthenticated() {
  return Boolean(localStorage.getItem('superadmin_token'));
}
