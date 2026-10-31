import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "./api";

/** One object from the API. */
export function useRecord(path, options = {}) {
  return useQuery({ queryKey: [path], queryFn: () => api(path), ...options });
}

/** A short list for dropdowns. Not for anything that can grow beyond 100 rows. */
export function useOptions(path, params = {}) {
  const merged = { page_size: 100, ...params };
  const query = useQuery({
    queryKey: [path, merged],
    queryFn: () => api(path, { params: merged }),
    staleTime: 60 * 1000,
  });
  return query.data?.results ?? [];
}

/**
 * A server-paginated list whose page, search, sort and filters live in the URL, so a
 * filtered view can be shared or reloaded. `fixed` params can't be changed by the user.
 */
export function useListPage(path, fixed = {}) {
  const [searchParams, setSearchParams] = useSearchParams();
  const params = { ...Object.fromEntries(searchParams), ...fixed };
  const query = useQuery({
    queryKey: [path, params],
    queryFn: () => api(path, { params }),
    placeholderData: keepPreviousData,
  });

  const setParam = (name, value) => {
    setSearchParams((current) => {
      const next = new URLSearchParams(current);
      if (value) next.set(name, value);
      else next.delete(name);
      if (name !== "page") next.delete("page");
      return next;
    }, { replace: true });
  };

  return { ...query, params, setParam, page: Number(params.page || 1) };
}

/** A local list with its own state, for several tables on one page. */
export function useLocalList(path, params = {}) {
  const [page, setPage] = useState(1);
  const merged = { ...params, page };
  const query = useQuery({
    queryKey: [path, merged],
    queryFn: () => api(path, { params: merged }),
    placeholderData: keepPreviousData,
  });
  return { ...query, page, setPage };
}

/** A write. Everything is refetched after it, so every number on screen stays true. */
export function useAction(fn, { onSuccess } = {}) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: async (data) => {
      await queryClient.invalidateQueries();
      onSuccess?.(data);
    },
  });
}

export function useDebounced(value, delay = 250) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}
