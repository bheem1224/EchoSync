const SYNC_PREFIX = 'ss:track:meta:';

function titleCase(text) {
  return String(text || '')
    .split(/\s+/)
    .filter(Boolean)
    .map((word) => {
      const first = word.charAt(0);
      const rest = word.slice(1);
      return `${first.toLocaleUpperCase()}${rest.toLocaleLowerCase()}`;
    })
    .join(' ');
}

function decodeBase64Utf8(value) {
  const normalized = String(value || '').replace(/-/g, '+').replace(/_/g, '/');
  const padded = normalized + '='.repeat((4 - (normalized.length % 4 || 4)) % 4);

  if (typeof atob === 'function') {
    const bytes = Uint8Array.from(atob(padded), (c) => c.charCodeAt(0));
    return new TextDecoder('utf-8').decode(bytes);
  }

  if (typeof Buffer !== 'undefined') {
    return Buffer.from(padded, 'base64').toString('utf-8');
  }

  throw new Error('No base64 decoder available in this environment');
}

export function decodeSyncId(syncId) {
  if (typeof syncId !== 'string' || !syncId.startsWith(SYNC_PREFIX)) {
    return syncId || '';
  }

  const encoded = syncId.slice(SYNC_PREFIX.length).split('?')[0].trim();
  if (!encoded) {
    return syncId;
  }

  try {
    const decoded = decodeBase64Utf8(encoded);
    const [artistRaw, titleRaw] = decoded.split('|');

    if (artistRaw && titleRaw) {
      return `${titleCase(artistRaw)} - ${titleCase(titleRaw)}`;
    }

    return titleCase(decoded.replace('|', ' - '));
  } catch {
    return syncId;
  }
}
