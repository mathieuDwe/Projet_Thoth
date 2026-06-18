import { useState, useCallback, useRef, useEffect } from 'react';

const initialState = {
  data: null,
  loading: false,
  error: null,
};

export default function useApi(apiFunc, immediate = false) {
  const [state, setState] = useState(initialState);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const execute = useCallback(
    async (...args) => {
      setState({ data: null, loading: true, error: null });

      try {
        const result = await apiFunc(...args);
        if (mountedRef.current) {
          setState({ data: result, loading: false, error: null });
        }
        return result;
      } catch (err) {
        if (mountedRef.current) {
          setState({ data: null, loading: false, error: err.message });
        }
        throw err;
      }
    },
    [apiFunc]
  );

  useEffect(() => {
    if (immediate) {
      execute();
    }
  }, [immediate, execute]);

  const reset = useCallback(() => {
    setState(initialState);
  }, []);

  return {
    ...state,
    execute,
    reset,
  };
}
