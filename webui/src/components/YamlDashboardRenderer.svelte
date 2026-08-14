<!--
  YamlDashboardRenderer.svelte
  ────────────────────────────────────────────────────────────────────────────
  The core of EchoSync's Sandboxed View Architecture (Lovelace Pattern).

  Responsibilities
  ────────────────
  1. Fetch a YAML dashboard definition from `yamlUrl` (or accept `yamlSource` inline).
  2. Parse it into a structured layout: { views: [ { id, title, icon, sections: [ { cards: [...] } ] } ] }.
  3. For each card that references a Web Component tag:
       a. Inject the bundle <script> into <head> (idempotent).
       b. Await customElements.whenDefined() before rendering.
       c. Render <svelte:element this={card.type} /> with declared props.
  4. Sandbox guarantee: each YAML config is fetched fresh and never eval-ed.
     All plugin-declared values are treated as *data*, not code.

  Props
  ─────
  yamlUrl    : string          – URL to a .yaml file (backend API or static asset).
  yamlSource : string          – Inline YAML string (overrides yamlUrl).
  scripts    : string[]        – Extra bundle URLs to inject before rendering.
               (Plugins pass these; DynamicPluginLoader callers pass their own.)
  activeView : number | string – Default active view index or view id.

  Events
  ──────
  on:ready({ detail: layout })  – Fired once layout is parsed and scripts injected.
  on:error({ detail: message }) – Fired on fetch/parse failure.

  Slot
  ────
  default – Fallback when no views are defined.
-->
<script>
  import apiClient from '../api/client';
  import { onMount, createEventDispatcher, tick } from 'svelte';

  const dispatch = createEventDispatcher();

  // ── Props ─────────────────────────────────────────────────────────────
  export let yamlUrl    = '';
  export let yamlSource = '';
  /** Extra bundle script URLs to pre-inject (from plugin manifest). */
  export let scripts    = [];
  /** Default view to show: 0-based index or view id string. */
  export let activeView = 0;

  // ── Internal state ────────────────────────────────────────────────────
  let layout     = null;   // { title, views: [ { id, title, icon, sections } ] }
  let loading    = true;
  let parseError = null;
  let activeIdx  = 0;      // resolved integer index

  // Track injected script URLs so we never double-inject across renders.
  const _injected = new Set();

  // ── Lifecycle ─────────────────────────────────────────────────────────
  onMount(async () => {
    await loadDashboard();
  });

  // ── Core pipeline ─────────────────────────────────────────────────────

  async function loadDashboard() {
    loading    = true;
    parseError = null;

    try {
      // 1. Obtain raw YAML text
      let rawYaml = yamlSource;

      if (!rawYaml && yamlUrl) {
        if (yamlUrl.startsWith('/api/')) {
          const res = await apiClient.get(yamlUrl.replace(/^\/api\/v1/, ''));
          if (res.status !== 200) {
            throw new Error(`[YamlDashboardRenderer] Failed to fetch ${yamlUrl}: ${res.status}`);
          }
          rawYaml = res.data;
        } else {
          const res = await fetch(yamlUrl);
          if (!res.ok) {
            throw new Error(`[YamlDashboardRenderer] Failed to fetch ${yamlUrl}: ${res.status} ${res.statusText}`);
          }
          rawYaml = await res.text();
        }
      }

      if (!rawYaml) {
        layout = { views: [] };
        dispatch('ready', layout);
        return;
      }

      // 2. Parse YAML
      layout = parseYaml(rawYaml);

      // 3. Resolve active view
      if (typeof activeView === 'string') {
        const found = layout.views.findIndex(v => v.id === activeView);
        activeIdx = found >= 0 ? found : 0;
      } else {
        activeIdx = Math.max(0, Math.min(activeView, layout.views.length - 1));
      }

      // 4. Inject all bundle scripts declared in layout + prop scripts
      const bundleUrls = collectBundleUrls(layout);
      const allUrls    = [...new Set([...scripts, ...bundleUrls])];
      await injectScripts(allUrls);

      dispatch('ready', layout);
    } catch (err) {
      parseError = err?.message ?? String(err);
      console.error('[YamlDashboardRenderer]', err);
      dispatch('error', parseError);
    } finally {
      loading = false;
    }
  }

  // ── YAML mini-parser ──────────────────────────────────────────────────
  /**
   * Minimal YAML parser sufficient for EchoSync dashboard configs.
   * Supports:
   *   - Scalar key: value
   *   - Block sequences (- item)
   *   - Nested maps via indentation
   *   - Quoted strings: "..." and '...'
   *   - # comments
   *   - Multi-line strings using | or > (passthrough as joined text)
   *
   * Does NOT support:
   *   - Anchors/aliases (&, *)
   *   - Complex YAML tags (!!)
   *   - Inline JSON maps/arrays ({ }, [ ])
   *
   * For production use at scale, swap this with `js-yaml` or `yaml` npm package.
   */
  function parseYaml(text) {
    const lines = text
      .split('\n')
      .map((l, i) => ({ raw: l, n: i }));

    const root = parseBlock(lines, 0, -1);
    return normalizeDashboardLayout(root);
  }

  /**
   * Recursively parse a block of YAML lines starting at `startIdx` with
   * indentation > `parentIndent`.  Returns { value, nextIdx }.
   */
  function parseBlock(lines, startIdx, parentIndent) {
    const result = {};
    let i = startIdx;

    // Detect if this block is a sequence
    let firstContentLine = null;
    for (let j = startIdx; j < lines.length; j++) {
      const s = lines[j].raw.trimStart();
      if (s === '' || s.startsWith('#')) continue;
      firstContentLine = { line: lines[j], idx: j };
      break;
    }

    const isSeq = firstContentLine && firstContentLine.line.raw.trimStart().startsWith('- ');
    if (isSeq) {
      return parseSequence(lines, startIdx, parentIndent);
    }

    while (i < lines.length) {
      const line = lines[i];
      const raw  = line.raw;

      // Skip blank / comment lines
      if (raw.trim() === '' || raw.trimStart().startsWith('#')) { i++; continue; }

      const indent = raw.search(/\S/);
      if (indent <= parentIndent && parentIndent >= 0) break; // dedented out of block

      // Parse key: value
      const colonIdx = findKeyColon(raw);
      if (colonIdx === -1) { i++; continue; }

      const key   = raw.slice(indent, colonIdx).trim();
      const after = raw.slice(colonIdx + 1).trim();

      if (after === '' || after === '|' || after === '>') {
        // Value is the next block
        const { value, nextIdx } = parseBlockValue(lines, i + 1, indent);
        result[key] = value;
        i = nextIdx;
      } else {
        result[key] = parseScalar(after);
        i++;
      }
    }

    return result;
  }

  function parseSequence(lines, startIdx, parentIndent) {
    const arr = [];
    let i = startIdx;

    while (i < lines.length) {
      const raw = lines[i].raw;
      if (raw.trim() === '' || raw.trimStart().startsWith('#')) { i++; continue; }

      const indent = raw.search(/\S/);
      if (indent <= parentIndent && parentIndent >= 0) break;

      if (raw.trimStart().startsWith('- ')) {
        const itemIndent = indent;
        const itemText   = raw.slice(indent + 2).trim(); // text after "- "

        if (itemText === '' || itemText.startsWith('#')) {
          // Multi-line map item
          const { value, nextIdx } = parseBlockValue(lines, i + 1, itemIndent);
          arr.push(value);
          i = nextIdx;
        } else if (findKeyColon(itemText) !== -1) {
          // Inline key: val as first key in a map
          const obj    = {};
          const colon  = findKeyColon(itemText);
          const k      = itemText.slice(0, colon).trim();
          const v      = itemText.slice(colon + 1).trim();
          obj[k]       = v ? parseScalar(v) : null;
          // Continue reading rest of this map block
          const { value: rest, nextIdx } = parseBlockValue(lines, i + 1, itemIndent, obj);
          arr.push(rest);
          i = nextIdx;
        } else {
          arr.push(parseScalar(itemText));
          i++;
        }
      } else {
        break;
      }
    }

    return arr;
  }

  function parseBlockValue(lines, startIdx, parentIndent, base = null) {
    // Peek: is the next content line a sequence or a map?
    let j = startIdx;
    while (j < lines.length && (lines[j].raw.trim() === '' || lines[j].raw.trimStart().startsWith('#'))) j++;

    if (j >= lines.length) return { value: base || {}, nextIdx: j };

    const nextRaw    = lines[j].raw;
    const nextIndent = nextRaw.search(/\S/);

    if (nextIndent <= parentIndent && parentIndent >= 0) return { value: base || {}, nextIdx: j };

    if (nextRaw.trimStart().startsWith('- ')) {
      const arr     = parseSequence(lines, j, parentIndent);
      const nextIdx = findNextIdx(lines, j, parentIndent, true);
      return { value: arr, nextIdx };
    }

    // It's a map
    const obj     = Object.assign({}, base);
    let   i       = j;

    while (i < lines.length) {
      const raw = lines[i].raw;
      if (raw.trim() === '' || raw.trimStart().startsWith('#')) { i++; continue; }

      const indent = raw.search(/\S/);
      if (indent <= parentIndent && parentIndent >= 0) break;

      const colon = findKeyColon(raw);
      if (colon === -1) { i++; continue; }

      const key   = raw.slice(indent, colon).trim();
      const after = raw.slice(colon + 1).trim();

      if (after === '' || after === '|' || after === '>') {
        const { value, nextIdx } = parseBlockValue(lines, i + 1, indent);
        obj[key] = value;
        i = nextIdx;
      } else {
        obj[key] = parseScalar(after);
        i++;
      }
    }

    return { value: obj, nextIdx: i };
  }

  function findNextIdx(lines, startIdx, parentIndent, afterSeq = false) {
    let i = startIdx;
    while (i < lines.length) {
      const raw = lines[i].raw;
      if (raw.trim() === '' || raw.trimStart().startsWith('#')) { i++; continue; }
      const indent = raw.search(/\S/);
      if (indent <= parentIndent && parentIndent >= 0) return i;
      i++;
    }
    return i;
  }

  /** Find the colon index for a key, ignoring colons inside quoted strings. */
  function findKeyColon(str) {
    let inSingle = false, inDouble = false;
    for (let i = 0; i < str.length; i++) {
      const c = str[i];
      if (c === "'" && !inDouble) inSingle = !inSingle;
      if (c === '"' && !inSingle) inDouble = !inDouble;
      if (c === ':' && !inSingle && !inDouble) {
        const next = str[i + 1];
        if (next === ' ' || next === undefined || next === '\t') return i;
      }
    }
    return -1;
  }

  function parseScalar(v) {
    if (!v || v === 'null' || v === '~') return null;
    if (v === 'true') return true;
    if (v === 'false') return false;
    if (/^-?\d+$/.test(v)) return parseInt(v, 10);
    if (/^-?\d+\.\d+$/.test(v)) return parseFloat(v);
    // Strip quotes
    if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) {
      return v.slice(1, -1);
    }
    return v;
  }

  // ── Dashboard layout normalizer ────────────────────────────────────────
  /**
   * Converts raw parsed YAML into the canonical layout shape:
   * {
   *   title: string,
   *   views: [{
   *     id: string, title: string, icon: string,
   *     sections: [{ cards: [{ type: string, ...props }] }]
   *   }]
   * }
   */
  function normalizeDashboardLayout(raw) {
    const layout = {
      title: raw.title ?? 'Dashboard',
      views: [],
    };

    if (Array.isArray(raw.views)) {
      layout.views = raw.views.map(normalizeView);
    } else if (Array.isArray(raw.cards)) {
      // Flat list of cards → single anonymous view with one section
      layout.views = [{ id: 'default', title: raw.title ?? 'View', icon: null, sections: [{ cards: raw.cards.map(normalizeCard) }] }];
    } else if (Array.isArray(raw.sections)) {
      layout.views = [{ id: 'default', title: raw.title ?? 'View', icon: null, sections: raw.sections.map(normalizeSection) }];
    }

    return layout;
  }

  function normalizeView(v) {
    return {
      id:       v.id ?? v.title?.toLowerCase().replace(/\s+/g, '_') ?? 'view',
      title:    v.title ?? '',
      icon:     v.icon ?? null,
      sections: Array.isArray(v.sections)
        ? v.sections.map(normalizeSection)
        : Array.isArray(v.cards)
          ? [{ cards: v.cards.map(normalizeCard) }]
          : [],
    };
  }

  function normalizeSection(s) {
    return {
      title: s.title ?? null,
      cards: Array.isArray(s.cards) ? s.cards.map(normalizeCard) : [],
    };
  }

  function normalizeCard(c) {
    if (typeof c === 'string') return { type: c, props: {} };
    const { type, ...props } = c;
    return { type: type ?? 'unknown-card', props };
  }

  // ── Bundle collection ─────────────────────────────────────────────────
  function collectBundleUrls(layout) {
    const urls = [];
    for (const view of layout.views ?? []) {
      for (const section of view.sections ?? []) {
        for (const card of section.cards ?? []) {
          if (card.props?.bundle_url) urls.push(card.props.bundle_url);
        }
      }
    }
    return urls;
  }

  // ── Script injection ──────────────────────────────────────────────────
  function injectScripts(urls) {
    return Promise.allSettled(
      urls.map(url => {
        if (!url || _injected.has(url)) return Promise.resolve();
        return new Promise((resolve, reject) => {
          const el   = document.createElement('script');
          el.type    = 'module';
          el.src     = url;
          el.onload  = () => { _injected.add(url); resolve(); };
          el.onerror = () => {
            console.warn(`[YamlDashboardRenderer] Failed to load bundle: ${url}`);
            resolve(); // resolve anyway — don't block the rest of the layout
          };
          document.head.appendChild(el);
        });
      })
    );
  }

  // ── customElements readiness helper ──────────────────────────────────
  function waitForElement(tagName, timeoutMs = 4000) {
    if (typeof customElements === 'undefined') return Promise.resolve(true);
    return Promise.race([
      customElements.whenDefined(tagName).then(() => true),
      new Promise((_, reject) =>
        setTimeout(() => reject(new Error(`Timeout: <${tagName}> not defined after ${timeoutMs}ms`)), timeoutMs)
      ),
    ]);
  }

  // ── View switching ────────────────────────────────────────────────────
  function switchView(idx) {
    activeIdx = idx;
  }

  $: currentView = layout?.views?.[activeIdx] ?? null;
</script>

<!-- ── Render ──────────────────────────────────────────────────────────── -->
{#if loading}
  <slot name="loading">
    <div class="ydr-spinner" aria-label="Loading dashboard…">
      <div class="ydr-ring"></div>
    </div>
  </slot>

{:else if parseError}
  <div class="ydr-error" role="alert">
    <span class="ydr-error__icon">⚠</span>
    <div>
      <strong>Dashboard failed to load</strong>
      <pre class="ydr-error__trace">{parseError}</pre>
    </div>
  </div>

{:else if layout && layout.views.length > 0}

  <!-- Tab bar (only when >1 view) -->
  {#if layout.views.length > 1}
    <nav class="ydr-tabs" aria-label="Dashboard views">
      {#each layout.views as view, i}
        <button
          id="ydr-tab-{view.id}"
          class="ydr-tab {i === activeIdx ? 'ydr-tab--active' : ''}"
          on:click={() => switchView(i)}
          aria-selected={i === activeIdx}
        >
          {#if view.icon}<span class="ydr-tab__icon" aria-hidden="true">{view.icon}</span>{/if}
          {view.title}
        </button>
      {/each}
    </nav>
  {/if}

  <!-- Active view -->
  {#if currentView}
    <div class="ydr-view" data-view-id={currentView.id}>
      <div class="ydr-sections">
        {#each currentView.sections as section}
          <div class="ydr-section">
            {#if section.title}
              <h3 class="ydr-section__title">{section.title}</h3>
            {/if}
            <div class="ydr-cards">
              {#each section.cards as card (card.type + JSON.stringify(card.props))}
                <div class="ydr-card-shell">
                  {#await waitForElement(card.type)}
                    <!-- Skeleton while the Web Component registers -->
                    <div class="ydr-skeleton" aria-busy="true">
                      <div class="ydr-skeleton__bar ydr-skeleton__bar--half"></div>
                      <div class="ydr-skeleton__bar"></div>
                      <div class="ydr-skeleton__bar ydr-skeleton__bar--wide"></div>
                    </div>
                  {:then _}
                    <!-- Sandboxed Web Component -->
                    <svelte:element
                      this={card.type}
                      class="ydr-web-component"
                      {...card.props}
                    />
                  {:catch err}
                    <div class="ydr-card-error" role="alert">
                      <span>⚠</span>
                      <div>
                        <strong>&lt;{card.type}&gt; failed</strong>
                        <p class="ydr-card-error__msg">{err.message}</p>
                      </div>
                    </div>
                  {/await}
                </div>
              {/each}
            </div>
          </div>
        {/each}
      </div>
    </div>
  {/if}

{:else}
  <!-- Empty / no views slot -->
  <slot>
    <div class="ydr-empty">
      <p>No dashboard views are configured.</p>
    </div>
  </slot>
{/if}

<style>
  /* ── Spinner ─────────────────────────────────────────────────────── */
  .ydr-spinner {
    display: flex; align-items: center; justify-content: center; padding: 48px 0;
  }
  .ydr-ring {
    width: 32px; height: 32px;
    border: 3px solid rgba(255,255,255,0.06);
    border-top-color: var(--color-primary, #1db954);
    border-radius: 50%;
    animation: ydr-spin 0.7s linear infinite;
  }
  @keyframes ydr-spin { to { transform: rotate(360deg); } }

  /* ── Error ───────────────────────────────────────────────────────── */
  .ydr-error {
    display: flex; align-items: flex-start; gap: 12px;
    padding: 16px 20px;
    background: rgba(239,68,68,0.1);
    border: 1px solid rgba(239,68,68,0.3);
    border-radius: 12px;
    color: #ef4444; font-size: 14px;
  }
  .ydr-error__icon { font-size: 20px; flex-shrink: 0; }
  .ydr-error__trace { margin: 6px 0 0; font-size: 11px; opacity: 0.75; white-space: pre-wrap; }

  /* ── Tabs ────────────────────────────────────────────────────────── */
  .ydr-tabs {
    display: flex; gap: 4px; flex-wrap: wrap;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    margin-bottom: 24px; padding-bottom: 0;
  }
  .ydr-tab {
    display: flex; align-items: center; gap: 6px;
    padding: 10px 18px; border: none; background: none;
    color: rgba(255,255,255,0.5); font-size: 13px; font-weight: 600;
    cursor: pointer; border-bottom: 2px solid transparent;
    transition: color 0.2s, border-color 0.2s;
    margin-bottom: -1px;
  }
  .ydr-tab:hover { color: rgba(255,255,255,0.85); }
  .ydr-tab--active { color: var(--color-primary, #1db954); border-bottom-color: var(--color-primary, #1db954); }
  .ydr-tab__icon { font-size: 16px; }

  /* ── Layout ──────────────────────────────────────────────────────── */
  .ydr-sections { display: flex; flex-direction: column; gap: 32px; }
  .ydr-section__title {
    font-size: 11px; font-weight: 900; text-transform: uppercase;
    letter-spacing: 0.2em; color: rgba(255,255,255,0.4);
    margin: 0 0 12px;
  }
  .ydr-cards { display: flex; flex-wrap: wrap; gap: 16px; }
  .ydr-card-shell {
    flex: 1 1 300px; min-width: 280px;
    border-radius: 16px; overflow: hidden;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.06);
    transition: border-color 0.2s, transform 0.2s;
  }
  .ydr-card-shell:hover { border-color: rgba(255,255,255,0.1); transform: translateY(-2px); }

  /* ── Skeleton ────────────────────────────────────────────────────── */
  .ydr-skeleton { padding: 20px; display: flex; flex-direction: column; gap: 10px; }
  .ydr-skeleton__bar {
    height: 12px; border-radius: 6px;
    background: linear-gradient(90deg,
      rgba(255,255,255,0.04) 0%,
      rgba(255,255,255,0.09) 50%,
      rgba(255,255,255,0.04) 100%);
    background-size: 200% 100%;
    animation: ydr-shimmer 1.4s ease-in-out infinite;
  }
  .ydr-skeleton__bar--half  { width: 45%; }
  .ydr-skeleton__bar--wide  { width: 80%; }
  @keyframes ydr-shimmer {
    0%   { background-position: 200% 0; }
    100% { background-position: -200% 0; }
  }

  /* ── Web Component host ──────────────────────────────────────────── */
  .ydr-web-component { display: block; width: 100%; min-height: 80px; }

  /* ── Card error ──────────────────────────────────────────────────── */
  .ydr-card-error {
    display: flex; align-items: flex-start; gap: 10px;
    padding: 16px; color: #f87171; font-size: 13px;
  }
  .ydr-card-error__msg { margin: 4px 0 0; font-size: 11px; opacity: 0.7; }

  /* ── Empty ───────────────────────────────────────────────────────── */
  .ydr-empty {
    padding: 40px 24px; text-align: center;
    border-radius: 12px; background: rgba(255,255,255,0.02);
    border: 1px dashed rgba(255,255,255,0.07);
    color: rgba(255,255,255,0.4); font-size: 14px;
  }
</style>
