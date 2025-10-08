import { createClient } from '@utils/supabase/server';
import { NextResponse } from 'next/server';

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get('code');
  const next = searchParams.get('next') || '/dashboard';

  if (code) {
    const supabase = await createClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (error) {
      console.error('Error exchanging code for session:', error);
      return NextResponse.redirect(`${origin}/sign-in`);
    }
    if (!error) {
      let userId: string | undefined;
      let userEmail: string | undefined;
      try {
        const { data: session, error: sessionError } =
          await supabase.auth.getSession();
        if (sessionError) {
          throw sessionError;
        }

        userId = session.session?.user.id || undefined;
        userEmail = session.session?.user.email || undefined;

        console.log('Session user details:', {
          id: userId,
          email: userEmail,
          provider: session.session?.user.app_metadata?.provider,
          identities: session.session?.user.identities?.length || 0
        });

        if (!userId || !userEmail) {
          throw new Error('Missing user ID or email from session');
        }

        // Store provider tokens in the database
        try {
          const providerToken = session.session?.provider_token;
          const providerRefreshToken = session.session?.provider_refresh_token;
          
          if (providerToken) {
            const providerTokens = {
              google: {
                access_token: providerToken,
                refresh_token: providerRefreshToken || null,
                expires_at: session.session?.expires_at || null,
                updated_at: new Date().toISOString(),
              }
            }

            const { error: updateError } = await supabase
              .from('users')
              .upsert({
                id: userId,
                email: userEmail,
                provider_tokens: providerTokens,
                updated_at: new Date().toISOString(),
              })
              .eq('id', userId)

            if (updateError) {
              console.warn('Failed to store provider tokens:', updateError)
            }
          }
        } catch (tokenError) {
          console.warn('Error handling provider tokens:', tokenError)
        }

        console.log('User authenticated successfully, redirecting to:', next);
        return NextResponse.redirect(`${origin}${next}`);
      } catch (err) {
        console.error('Error in auth callback:', err);
        console.error('Error details:', {
          message: err instanceof Error ? err.message : 'Unknown error',
          stack: err instanceof Error ? err.stack : 'No stack trace',
          userId: userId || 'undefined',
          userEmail: userEmail || 'undefined'
        });
        return NextResponse.redirect(`${origin}/sign-in`);
      }
    }
  }

  console.error('Auth callback error: No authorization code received', {
    searchParams: Object.fromEntries(searchParams.entries()),
    origin
  });
  return NextResponse.redirect(`${origin}/sign-in`);
}