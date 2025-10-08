import { createClient } from './client';

export async function clearInvalidSession() {
  const supabase = createClient();
  try {
    await supabase.auth.signOut();
  } catch (error) {
    // Even if signOut fails, clear local storage
    if (typeof window !== 'undefined') {
      localStorage.removeItem('supabase.auth.token');
      // Clear all supabase-related items
      Object.keys(localStorage).forEach(key => {
        if (key.startsWith('sb-') || key.includes('supabase')) {
          localStorage.removeItem(key);
        }
      });
    }
  }
}

export async function handleAuthError(error: any) {
  if (error?.code === 'refresh_token_not_found' || 
      error?.message?.includes('refresh_token_not_found') ||
      error?.message?.includes('Invalid Refresh Token')) {
    await clearInvalidSession();
    if (typeof window !== 'undefined') {
      window.location.href = '/sign-in';
    }
  }
}