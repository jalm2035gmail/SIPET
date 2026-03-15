// Simple auth utility for Vendor Admin (token in localStorage)
export function login(token) {
  localStorage.setItem('vendor_token', token);
}

export function logout() {
  localStorage.removeItem('vendor_token');
}

export function isAuthenticated() {
  return Boolean(localStorage.getItem('vendor_token'));
}
