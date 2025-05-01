import { createClient } from "@supabase/supabase-js";

const SUPABASE_URL = "https://ozyffsixezymrsilffef.supabase.co";
const SUPABASE_ANON_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im96eWZmc2l4ZXp5bXJzaWxmZmVmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MjIyNzk3MjgsImV4cCI6MjAzNzg1NTcyOH0.pcTEeuPI-ie1a4lcU-hofVN-XzZI16Ll0-lOLfaEsQg";

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
  auth: {
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: true,
  },
});

export async function updateUserSettings(
  first_name: string,
  last_name: string,
  email: string,
): Promise<boolean> {
  const { error: supabaseError } = await supabase.auth.updateUser({
    email: email,
    data: {
      full_name: `${first_name} ${last_name}`,
      name: `${first_name} ${last_name}`,
      email: email,
    },
  });

  if (supabaseError) {
    console.error("Failed to update Supabase user:", supabaseError);
    return false;
  }

  return true;
}
