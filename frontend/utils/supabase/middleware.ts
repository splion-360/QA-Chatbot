import { createServerClient } from '@supabase/ssr';
import { type NextRequest, NextResponse } from 'next/server';

const environment = process.env.ENVIRONMENT || 'production';

export const updateSession = async (request: NextRequest) => {
  // This `try/catch` block is only here for the interactive tutorial.
  // Feel free to remove once you have Supabase connected.
  try {
    // Create an unmodified response
    let response = NextResponse.next({
      request: {
        headers: request.headers
      }
    });

    // Use environment-specific Supabase configuration
    let supabaseUrl: string;
    let supabaseAnonKey: string;

    if (environment === 'development') {
      supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL_DEV!;
      supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY_DEV!;
    } else {
      supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
      supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;
    }

    // Skip auth checks for now

    // Skip middleware for auth callback routes
    if (request.nextUrl.pathname.startsWith('/auth/callback')) {
      return response;
    }

    // Redirect home page to dashboard
    if (request.nextUrl.pathname === '/') {
      return NextResponse.redirect(new URL('/dashboard', request.url));
    }

    return response;
  } catch (e) {
    // If you are here, a Supabase client could not be created!
    // This is likely because you have not set up environment variables.
    // Check out http://localhost:3000 for Next Steps.
    return NextResponse.next({
      request: {
        headers: request.headers
      }
    });
  }
};
