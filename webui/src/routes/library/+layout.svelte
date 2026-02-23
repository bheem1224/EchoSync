<script>
    import { page } from '$app/stores';
    import Omnibar from '$lib/components/Omnibar.svelte';

    $: activeTab = $page.url.pathname.endsWith('/manager') ? 'manager' : 'collection';
</script>

<div class="library-layout min-h-screen bg-gray-900 text-white p-6">
    <div class="max-w-7xl mx-auto space-y-6">

        <!-- Header: Tabs & Omnibar -->
        <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
            <div class="flex items-center gap-8">
                <div>
                    <h1 class="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-600">Library</h1>
                    <p class="text-gray-400 text-sm">Media Management</p>
                </div>

                <!-- Navigation Tabs -->
                <nav class="flex bg-gray-800 p-1 rounded-lg">
                    <a
                        href="/library"
                        class="px-4 py-1.5 rounded-md text-sm font-medium transition-colors {activeTab === 'collection' ? 'bg-blue-600 text-white shadow' : 'text-gray-400 hover:text-white'}"
                    >
                        Collection
                    </a>
                    <a
                        href="/library/manager"
                        class="px-4 py-1.5 rounded-md text-sm font-medium transition-colors {activeTab === 'manager' ? 'bg-purple-600 text-white shadow' : 'text-gray-400 hover:text-white'}"
                    >
                        Manager
                    </a>
                </nav>
            </div>

            <div class="w-full md:w-1/2 max-w-xl">
                <Omnibar />
            </div>
        </div>

        <!-- Content Slot -->
        <div class="content-area">
            <slot />
        </div>
    </div>
</div>
