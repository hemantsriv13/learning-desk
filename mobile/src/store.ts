// Everything the learner does is saved on the phone only (AsyncStorage). Nothing is sent anywhere.
import AsyncStorage from '@react-native-async-storage/async-storage';
import { createContext, useCallback, useContext, useEffect, useState } from 'react';

export type Place = { status: 'started' | 'completed'; section: number };
export type State = {
  progress: Record<string, Place>;
  notes: Record<string, string>;
  answers: Record<string, Record<string, string>>; // lesson id -> check id -> chosen option
  current: string | null; // the lesson Continue opens
};

const KEY = 'learning-desk/state/v1';
const EMPTY: State = { progress: {}, notes: {}, answers: {}, current: null };

export function useStore() {
  const [state, setState] = useState<State>(EMPTY);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    AsyncStorage.getItem(KEY)
      .then((text) => text && setState({ ...EMPTY, ...JSON.parse(text) }))
      .catch(() => undefined) // unreadable storage: start fresh rather than crash
      .finally(() => setReady(true));
  }, []);

  const update = useCallback((change: (s: State) => State) => {
    setState((prev) => {
      const next = change(prev);
      AsyncStorage.setItem(KEY, JSON.stringify(next)).catch(() => undefined);
      return next;
    });
  }, []);

  return { state, ready, update };
}

export type Store = ReturnType<typeof useStore>;
export const StoreContext = createContext<Store | null>(null);

export function useApp(): Store {
  const store = useContext(StoreContext);
  if (!store) throw new Error('useApp outside StoreContext');
  return store;
}

/** Open a lesson: it becomes the current activity and is marked started (never un-completes it). */
export function openLesson(store: Store, id: string) {
  store.update((s) => ({
    ...s,
    current: id,
    progress: { ...s.progress, [id]: s.progress[id] ?? { status: 'started', section: 0 } },
  }));
}
