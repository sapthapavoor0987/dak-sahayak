'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '../lib/supabase';

export default function RootPage() {
  const router = useRouter();

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        router.replace('/chat');
      } else {
        router.replace('/login');
      }
    });
  }, [router]);

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: '#131314' }}>
      <div style={{ color: '#e3e3e3', display: 'flex', alignItems: 'center', gap: '12px' }}>
        <i className="fa-solid fa-spinner fa-spin" style={{ color: '#c4122f', fontSize: '1.5rem' }}></i>
        <span>Loading Dak Sahayak...</span>
      </div>
    </div>
  );
}
