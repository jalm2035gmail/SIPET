import dynamic from 'next/dynamic';

const MessagingInterface = dynamic(() => import('../components/messaging/MessagingInterface'), { ssr: false });

export default function MessagesPage() {
  // TODO: Replace with real user context/auth
  const currentUser = {
    id: 1,
    first_name: 'Demo',
    last_name: 'User',
    avatar_url: null,
    is_vendor: false
  };
  return <MessagingInterface currentUser={currentUser} />;
}
