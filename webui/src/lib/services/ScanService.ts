import { scanStore, type ScanStatePayload } from '../stores/scanStore';

export class ScanService {
  private eventSource: EventSource | null = null;

  /**
   * Connect to the SSE endpoint and listen for scanning progress events.
   * @param streamUrl Optional override for the SSE endpoint URL.
   */
  public connect(streamUrl: string = '/api/v1/library/scan/stream'): void {
    this.disconnect(); // Close existing connection if any

    scanStore.reset();

    try {
      this.eventSource = new EventSource(streamUrl);

      this.eventSource.addEventListener('scan_progress', (event: MessageEvent) => {
        try {
          const payload: ScanStatePayload = JSON.parse(event.data);
          scanStore.setScanProgress(payload);
        } catch (err) {
          console.error('Failed to parse scan_progress SSE event payload:', err);
        }
      });

      this.eventSource.addEventListener('scan_complete', (event: MessageEvent) => {
        try {
          const payload: ScanStatePayload = JSON.parse(event.data);
          scanStore.setScanComplete(payload);
        } catch (err) {
          console.error('Failed to parse scan_complete SSE event payload:', err);
        } finally {
          this.disconnect();
        }
      });

      this.eventSource.addEventListener('scan_error', (event: MessageEvent) => {
        try {
          const payload: ScanStatePayload = JSON.parse(event.data);
          const errorMsg = payload.error_message || 'An unknown error occurred during scanning.';
          scanStore.setScanError(errorMsg);
        } catch (err) {
          scanStore.setScanError('Error parsing scan failure details.');
        } finally {
          this.disconnect();
        }
      });

      this.eventSource.addEventListener('scan_idle', () => {
        scanStore.reset();
      });

      this.eventSource.onerror = (error) => {
        console.error('EventSource connection error:', error);
        if (this.eventSource?.readyState === EventSource.CLOSED) {
          this.disconnect();
        }
      };
    } catch (err) {
      console.error('Failed to initialize EventSource connection:', err);
      scanStore.setScanError('Failed to establish connection to server telemetry.');
    }
  }

  /**
   * Disconnect and close the EventSource connection safely to prevent memory leaks.
   */
  public disconnect(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }
}

export const scanService = new ScanService();
