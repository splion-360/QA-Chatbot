import { createBrowserClient } from '@supabase/ssr';

const environment = process.env.ENVIRONMENT || 'production';

let supabaseUrl: string;
let supabaseAnonKey: string;

if (environment === 'development') {
  supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL_DEV!;
  supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY_DEV!;
} else {
  supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
  supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;
}

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error(`Missing Supabase config for environment: ${environment}`);
}


export const createClient = () =>
  createBrowserClient(supabaseUrl, supabaseAnonKey, {
    auth: {
      persistSession: true,
      detectSessionInUrl: true,
      flowType: 'pkce'
    }
  });
