import { useState } from 'react';
import { useRouter } from 'next/router';
import { login, isAuthenticated } from '../utils/auth';

export default function SuperAdminLogin() {
  const [user, setUser] = useState('');
  const [pass, setPass] = useState('');
  const [error, setError] = useState('');
  const router = useRouter();

  const handleSubmit = async (e) => {
    e.preventDefault();
    // Simulación de login: acepta cualquier usuario/contraseña
    if (user && pass) {
      login('fake-jwt-token');
      router.push('/dashboard');
    } else {
      setError('Usuario y contraseña requeridos');
    }
  };

  if (isAuthenticated()) {
    router.replace('/dashboard');
    return null;
  }

  return (
    <div>
      <h1>Login Super Admin</h1>
      <form onSubmit={handleSubmit}>
        <input type="text" placeholder="Usuario" value={user} onChange={e => setUser(e.target.value)} />
        <input type="password" placeholder="Contraseña" value={pass} onChange={e => setPass(e.target.value)} />
        <button type="submit">Entrar</button>
      </form>
      {error && <p style={{color:'red'}}>{error}</p>}
    </div>
  );
}
