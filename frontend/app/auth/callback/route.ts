import { createClient } from '@utils/supabase/server';
import { NextResponse } from 'next/server';

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get('code');
  const next = searchParams.get('next') || '/dashboard';

  console.log('Auth callback received:', {
    code: code ? 'present' : 'missing',
    searchParams: Object.fromEntries(searchParams.entries())
  });

  if (code) {
    const supabase = await createClient();
    
    try {
      const { data, error } = await supabase.auth.exchangeCodeForSession(code);
      
      if (error) {
        console.error('Error exchanging code for session:', error);
        return NextResponse.redirect(`${origin}/sign-in?error=auth_error`);
      }

      if (data?.session) {
        const { user } = data.session;
        
        console.log('Session user details:', {
          id: user.id,
          email: user.email,
          provider: user.app_metadata?.provider,
          identities: user.identities?.length || 0
        });

        console.log('User authenticated successfully, redirecting to:', {
          userId: user.id,
          userEmail: user.email,
          redirectPath: next
        });

        return NextResponse.redirect(`${origin}${next}`);
      } else {
        throw new Error('No session data received after code exchange');
      }
    } catch (err) {
      console.error('Error in auth callback:', err);
      console.error('Error details:', {
        message: err instanceof Error ? err.message : 'Unknown error',
        stack: err instanceof Error ? err.stack : 'No stack trace'
      });
      return NextResponse.redirect(`${origin}/sign-in?error=callback_error`);
    }
  }

  console.error('Auth callback error: No authorization code received', {
    searchParams: Object.fromEntries(searchParams.entries()),
    origin
  });
  return NextResponse.redirect(`${origin}/sign-in?error=no_code`);
}