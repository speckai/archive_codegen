import { Session, User } from "@supabase/supabase-js";

import { useEffect, useState } from "react";

import { createClient, EmailOtpType } from "@supabase/supabase-js";
import { useRouter } from "next/navigation";
import posthog from "posthog-js";

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

export function useAuth() {
  const [session, setSession] = useState<Session | null>(null);
  const [loaded, setLoaded] = useState<boolean>(false);
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [hasSignedIn, setHasSignedIn] = useState<boolean>(false);
  const [unauthorized, setUnauthorized] = useState<boolean | null>(null);
  const router = useRouter();

  useEffect(() => {
    supabase.auth
      .getSession()
      .then(async ({ data: { session } }) => {
        setSession(session);
        setToken(session?.access_token ?? null);
        setUser(session?.user ?? null);
        setLoaded(true);
        setUnauthorized(session === null);
      })
      .catch(() => {
        setLoaded(true);
        setUnauthorized(true);
      });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      setToken(session?.access_token ?? null);
      setUser(session?.user ?? null);
      setHasSignedIn(true);
      setUnauthorized(session === null);
      if (session?.user) {
        posthog.identify(session.user.id, {
          name: session.user.user_metadata.name,
          email: session.user.email,
        });
      }
    });
    return () => subscription.unsubscribe();
  }, []);

  const signInWithGoogle = async (): Promise<{
    success: boolean;
    error?: any;
  }> => {
    let redirectUrl = "https://app.speck.sh";
    if (process.env.NEXT_PUBLIC_API_URL?.includes("localhost")) {
      redirectUrl = "http://localhost:3000";
    }

    const { data, error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: redirectUrl,
      },
    });

    if (error) {
      console.error("Error during Google sign-in:", error);
      return { success: false, error };
    }

    return { success: true };
  };

  const signInWithEmail = async (email: string, password: string) => {
    const {
      data: { session },
      error,
    } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    let success = true;
    if (error) {
      success = false;
    }
    return { success, session, error };
  };

  const signUpWithEmail = async (email: string, password: string) => {
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        emailRedirectTo: process.env.NEXT_PUBLIC_API_URL?.includes("localhost")
          ? "http://localhost:3000/home"
          : "https://app.speck.sh/home",
      },
    });
    const { session, user } = data;

    if (error) {
      console.error("Error during email sign-up:", error);
      return { success: false, session: null, error };
    }

    const requiresEmailConfirmation = !session;

    return {
      success: true,
      session,
      user,
      requiresEmailConfirmation,
      error: error,
    };
  };

  const signOut = async () => {
    setSession(null);
    setToken(null);
    setUser(null);
    setHasSignedIn(false);
    posthog.reset();
    localStorage.clear();
    router.push("/");

    const { error } = await supabase.auth.signOut();
    if (error) {
      console.error("Error during sign out:", error);
      return { success: false, error };
    }
    return { success: true };
  };

  const signInWithGithub = async (): Promise<{
    success: boolean;
    error?: any;
    provider_token?: string;
  }> => {
    let redirectUrl = "https://app.speck.sh";
    if (process.env.NEXT_PUBLIC_API_URL?.includes("localhost")) {
      redirectUrl = "http://localhost:3000";
    }

    const { data, error } = await supabase.auth.signInWithOAuth({
      provider: "github",
      options: {
        redirectTo: redirectUrl,
        scopes: "repo",
      },
    });

    if (error) {
      console.error("Error during GitHub sign-in:", error);
      return { success: false, error };
    }

    return { success: true };
  };

  const verifyPasswordResetToken = async (token_hash: string, type: string) => {
    try {
      const { error, data } = await supabase.auth.verifyOtp({
        token_hash: token_hash,
        type: type as EmailOtpType,
      });

      if (error) {
        return { success: false, error };
      }

      return {
        success: true,
        email: data.user?.email,
        error: null,
      };
    } catch (error) {
      return { success: false, error };
    }
  };

  const resetPassword = async (newPassword: string) => {
    try {
      const { error } = await supabase.auth.updateUser({
        password: newPassword,
      });

      if (error) {
        return { success: false, error };
      }

      return { success: true, error: null };
    } catch (error) {
      return { success: false, error };
    }
  };

  return {
    session,
    token,
    user,
    loaded,
    hasSignedIn,
    unauthorized,
    signInWithGoogle,
    signInWithEmail,
    signUpWithEmail,
    signOut,
    signInWithGithub,
    verifyPasswordResetToken,
    resetPassword,
  };
}
