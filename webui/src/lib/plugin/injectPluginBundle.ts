/**
 * Injects a plugin bundle script into the DOM.
 * Includes strict cache-busting using an exact URL match guard.
 */

const _injectedUrls = new Set<string>();

export function injectPluginBundle(url: string, version: string | null = null): Promise<void> {
    const separator = url.includes('?') ? '&' : '?';
    const finalUrl = version ? `${url}${separator}v=${version}` : url;

    // Check module-level state guard
    if (_injectedUrls.has(finalUrl)) {
        return Promise.resolve();
    }

    // Check DOM state guard - strict exact match on finalUrl to allow version bumps
    if (Array.from(document.getElementsByTagName('script')).some(s => s.getAttribute('src') === finalUrl)) {
        _injectedUrls.add(finalUrl);
        return Promise.resolve();
    }

    return new Promise((resolve, reject) => {
        const el = document.createElement('script');
        el.type = 'module';
        el.src = finalUrl;
        el.onload = () => {
            _injectedUrls.add(finalUrl);
            resolve();
        };
        el.onerror = () => {
            console.error(`[PluginLoader] Script injection failed for path: ${finalUrl}`);
            reject(new Error(`Failed to load plugin bundle: ${finalUrl}`));
        };
        document.head.appendChild(el);
    });
}
