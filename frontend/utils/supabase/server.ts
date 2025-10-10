import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

const environment = process.env.ENVIRONMENT || "production";

let supabaseUrl: string;
let supabaseAnonKey: string;

if (environment === "development") {
  supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL_DEV!;
  supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY_DEV!;
} else {
  supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
  supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;
}

export const createClient = async () => {
  const cookieStore = await cookies();

  return createServerClient(supabaseUrl, supabaseAnonKey, {
    cookies: {
      getAll() {
        return cookieStore.getAll();
      },
      setAll(cookiesToSet) {
        try {
          cookiesToSet.forEach(({ name, value, options }) =>
            cookieStore.set(name, value, { ...options, path: "/" }),
          );
        } catch {
          // The `setAll` method was called from a Server Component.
          // This can be ignored if you have middleware refreshing
          // user sessions.
        }
      },
    },
  });
};


