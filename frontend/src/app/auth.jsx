import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

const ME = ["me"];

/** The logged-in user, or null. Role checks here are for UX; the backend enforces access. */
export function useAuth() {
  const queryClient = useQueryClient();
  const { data: user, isLoading, error, refetch } = useQuery({
    queryKey: ME,
    queryFn: async () => {
      try {
        return await api("/auth/me");
      } catch (err) {
        if (err.status === 401) return null;
        throw err;
      }
    },
    staleTime: 5 * 60 * 1000,
  });

  return {
    user: user ?? null,
    isLoading,
    error,
    refetch,
    login: async (credentials) => {
      const me = await api("/auth/login", { method: "POST", body: credentials });
      queryClient.setQueryData(ME, me);
      return me;
    },
    signup: async (details) => {
      const me = await api("/auth/signup", { method: "POST", body: details });
      queryClient.setQueryData(ME, me);
      return me;
    },
    logout: async () => {
      await api("/auth/logout", { method: "POST" });
      queryClient.clear();
      queryClient.setQueryData(ME, null);
    },
  };
}

export function homeFor(user) {
  return user.role === "customer" ? "/portal" : "/";
}
