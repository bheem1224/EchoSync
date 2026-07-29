import { writable } from 'svelte/store';

export type ScanStatus = 'idle' | 'scanning' | 'complete' | 'failed';

export interface ScanStatePayload {
  status: ScanStatus;
  tracks_processed?: number;
  batch_size?: number;
  errors_encountered?: number;
  current_phase?: string;
  total_tracks?: number;
  total_errors?: number;
  elapsed_time_ms?: number;
  error_message?: string | null;
}

const initialScanState: ScanStatePayload = {
  status: 'idle',
  tracks_processed: 0,
  batch_size: 0,
  errors_encountered: 0,
  current_phase: 'idle',
  total_tracks: 0,
  total_errors: 0,
  elapsed_time_ms: 0,
  error_message: null
};

function createScanStore() {
  const { subscribe, set, update } = writable<ScanStatePayload>(initialScanState);

  return {
    subscribe,
    setScanProgress: (payload: Partial<ScanStatePayload>) => {
      update((state) => ({
        ...state,
        ...payload,
        status: 'scanning'
      }));
    },
    setScanComplete: (payload: Partial<ScanStatePayload>) => {
      update((state) => ({
        ...state,
        ...payload,
        status: 'complete'
      }));
    },
    setScanError: (errorMsg: string) => {
      update((state) => ({
        ...state,
        status: 'failed',
        error_message: errorMsg
      }));
    },
    reset: () => set(initialScanState)
  };
}

export const scanStore = createScanStore();
