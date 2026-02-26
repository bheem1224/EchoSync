<script>
    import { page } from '$app/stores';
    import Omnibar from '$lib/components/Omnibar.svelte';

    // Simple active tab logic based on path
    $: activeTab = $page.url.pathname.includes('/library/manager') ? 'manager' :
                   $page.url.pathname.includes('/library/suggestions') ? 'suggestions' : 'collection';
</script>

<div class="page">
    <div class="page-container">

        <!-- Header: Tabs & Omnibar -->
        <div class="page__header flex-row items-center gap-4">
            <div class="flex items-center gap-8">
                <div>
                    <p class="eyebrow">Media Management</p>
                    <h1>Library</h1>
                </div>

                <!-- Navigation Tabs -->
                <nav class="flex bg-black/20 p-1 rounded-lg border border-white/5">
                    <a
                        href="/library"
                        class="px-4 py-1.5 rounded-md text-sm font-medium transition-colors {activeTab === 'collection' ? 'bg-primary text-black shadow' : 'text-gray-400 hover:text-white'}"
                    >
                        Collection
                    </a>
                    <a
                        href="/library/manager"
                        class="px-4 py-1.5 rounded-md text-sm font-medium transition-colors {activeTab === 'manager' ? 'bg-purple-600 text-white shadow' : 'text-gray-400 hover:text-white'}"
                    >
                        Manager
                    </a>
                    <a
                        href="/library/suggestions"
                        class="px-4 py-1.5 rounded-md text-sm font-medium transition-colors {activeTab === 'suggestions' ? 'bg-blue-600 text-white shadow' : 'text-gray-400 hover:text-white'}"
                    >
                        Suggestions
                    </a>
                </nav>
            </div>

            <div class="w-full md:w-1/2 max-w-xl ml-auto">
                <Omnibar />
            </div>
        </div>

        <!-- Content Slot -->
        <div class="content-area">
            <slot />
        </div>
    </div>
</div>

<style>
    .page {
        min-height: 100vh;
        padding: 24px;
        background: transparent; /* Allow layout background */
    }

    .page-container {
        max-width: 1400px;
        margin: 0 auto;
        display: flex;
        flex-direction: column;
        gap: 24px;
    }

    .page__header {
        display: flex;
        justify-content: space-between;
        margin-bottom: 0;
    }

    h1 {
        font-size: 28px;
        font-weight: 700;
        margin: 0;
        color: var(--text);
    }

    .eyebrow {
        color: var(--accent);
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin: 0 0 4px 0;
    }

    .bg-primary { background-color: var(--accent, #0fef88); }
</style>
