import { useEffect } from 'react';
import { useRouter } from 'next/router';
import { isAuthenticated } from '../utils/auth';

export default function Dashboard() {
  const router = useRouter();

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace('/login');
    }
  }, []);

  return (
    <div>
      <h2>Dashboard Vendedor</h2>
      <p>Solo visible si estás autenticado como vendedor.</p>
    </div>
  );
}
