<script>
    import { onMount } from 'svelte';
    import { feedback } from '../stores/feedback';
    import apiClient, { API_BASE_URL } from '../api/client';

    let backups = $state([]);
    let loading = $state(true);
    let creating = $state(false);
    let restoring = $state(false);
    let uploading = $state(false);
    let dropzoneActive = $state(false);

    onMount(async () => {
        await loadBackups();
        
        const handleBeforeUnload = (e) => {
            if (creating || restoring || uploading) {
                e.preventDefault();
                e.returnValue = '';
            }
        };
        
        window.addEventListener('beforeunload', handleBeforeUnload);
        
        return () => {
            window.removeEventListener('beforeunload', handleBeforeUnload);
        };
    });

    async function loadBackups() {
        loading = true;
        try {
            const response = await apiClient.get('/system/backups');
            if (response.data && response.data.success) {
                backups = response.data.backups;
            }
        } catch (error) {
            console.error('Failed to load backups:', error);
            feedback.addToast('Failed to load backup list', 'error');
        } finally {
            loading = false;
        }
    }

    async function handleCreateBackup() {
        creating = true;
        try {
            const response = await apiClient.post('/system/backup');
            if (response.data && response.data.success) {
                feedback.addToast('Backup created successfully', 'success');
                await loadBackups();
            }
        } catch (error) {
            console.error('Backup creation failed:', error);
            feedback.addToast('Backup creation failed', 'error');
        } finally {
            creating = false;
        }
    }

    function handleDownload(filename) {
        window.open(`${API_BASE_URL}/system/backups/${filename}/download`, '_blank');
    }

    async function handleRestore(filename) {
        const confirmed = confirm(`WARNING: Restoring from ${filename} will overwrite your current system state and trigger an immediate restart. Are you sure you want to proceed?`);
        if (!confirmed) return;

        restoring = true;
        try {
            const response = await apiClient.post('/system/restore', { filename });
            if (response.data && response.data.success) {
                feedback.addToast('Restore sequence initiated. System is restarting...', 'success');
                setTimeout(() => window.location.reload(), 5000);
            }
        } catch (error) {
            console.error('Restore failed:', error);
            feedback.addToast('Restore failed: ' + (error.response?.data?.error || error.message), 'error');
        } finally {
            restoring = false;
        }
    }

    async function handleFileUpload(event) {
        const files = event.target.files || event.dataTransfer.files;
        const file = files[0];
        if (!file) return;

        if (!file.name.endsWith('.zip')) {
            feedback.addToast('Invalid file type. Only .zip backups are allowed.', 'error');
            return;
        }

        const confirmed = confirm(`WARNING: Restoring from uploaded backup ${file.name} will overwrite your current system state. Proceed?`);
        if (!confirmed) return;

        uploading = true;
        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await apiClient.post('/system/restore', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });

            if (response.data && response.data.success) {
                feedback.addToast('Restore successful. EchoSync is restarting...', 'success');
                setTimeout(() => window.location.reload(), 5000);
            }
        } catch (error) {
            console.error('Upload restore failed:', error);
            feedback.addToast('Restore failed: ' + (error.response?.data?.error || error.message), 'error');
        } finally {
            uploading = false;
            dropzoneActive = false;
        }
    }

    function formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    function formatDate(isoString) {
        return new Date(isoString).toLocaleString();
    }
</script>

<div class="space-y-6">
    <div class="flex items-center justify-between">
        <div>
            <h2 class="text-lg font-semibold text-white">System Backups</h2>
            <p class="text-sm text-gray-400">Full captures of your vault, analytics, and library metadata.</p>
        </div>
        <button 
            on:click={handleCreateBackup}
            disabled={creating}
            class="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-gray-700 disabled:opacity-50 text-white rounded-lg font-medium transition-all flex items-center gap-2 active:scale-95"
        >
            {#if creating}
                <svg class="animate-spin h-4 w-4" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                Creating...
            {:else}
                <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                Create New Backup
            {/if}
        </button>
    </div>

    <div class="bg-gray-800/50 border border-gray-700/60 rounded-xl overflow-hidden">
        <table class="w-full text-left text-sm">
            <thead class="bg-gray-800 text-gray-400 font-medium uppercase tracking-wider text-[10px]">
                <tr>
                    <th class="px-4 py-3">Filename</th>
                    <th class="px-4 py-3">Created At</th>
                    <th class="px-4 py-3">Size</th>
                    <th class="px-4 py-3 text-right">Actions</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-gray-700/50">
                {#if loading}
                    {#each Array(3) as _}
                        <tr class="animate-pulse">
                            <td class="px-4 py-4"><div class="h-4 bg-gray-700 rounded w-48"></div></td>
                            <td class="px-4 py-4"><div class="h-4 bg-gray-700 rounded w-32"></div></td>
                            <td class="px-4 py-4"><div class="h-4 bg-gray-700 rounded w-16"></div></td>
                            <td class="px-4 py-4 text-right"><div class="h-8 bg-gray-700 rounded w-24 ml-auto"></div></td>
                        </tr>
                    {/each}
                {:else if backups.length === 0}
                    <tr>
                        <td colspan="4" class="px-4 py-12 text-center text-gray-500 italic">
                            No backups found on server.
                        </td>
                    </tr>
                {:else}
                    {#each backups as backup}
                        <tr class="hover:bg-gray-700/30 transition-colors group">
                            <td class="px-4 py-4 font-mono text-gray-300">{backup.filename}</td>
                            <td class="px-4 py-4 text-gray-400">{formatDate(backup.created_at)}</td>
                            <td class="px-4 py-4 text-gray-400">{formatBytes(backup.size_bytes)}</td>
                            <td class="px-4 py-4 text-right">
                                <div class="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <button 
                                        on:click={() => handleDownload(backup.filename)}
                                        title="Download to PC"
                                        class="p-2 hover:bg-gray-600 rounded-lg text-blue-400 transition-colors"
                                    >
                                        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                                    </button>
                                    <button 
                                        on:click={() => handleRestore(backup.filename)}
                                        disabled={restoring}
                                        class="px-3 py-1 bg-amber-600/10 hover:bg-amber-600 border border-amber-600/30 text-amber-400 hover:text-white rounded-md text-xs font-semibold transition-all active:scale-95 disabled:opacity-50"
                                    >
                                        Restore
                                    </button>
                                </div>
                            </td>
                        </tr>
                    {/each}
                {/if}
            </tbody>
        </table>
    </div>

    <!-- Manual Upload Dropzone -->
    <div 
        class="relative group"
        on:dragover|preventDefault={() => dropzoneActive = true}
        on:dragleave|preventDefault={() => dropzoneActive = false}
        on:drop|preventDefault={handleFileUpload}
    >
        <div class="flex items-center gap-2 mb-2 text-xs font-bold text-gray-500 uppercase tracking-widest">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
            Manual Migration
        </div>
        <label 
            class="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed rounded-xl cursor-pointer transition-all duration-300
            {dropzoneActive ? 'border-emerald-500 bg-emerald-500/10' : 'border-gray-700 bg-gray-800/40 hover:bg-gray-800/60 hover:border-gray-600'}"
        >
            <div class="flex flex-col items-center justify-center pt-5 pb-6">
                {#if uploading}
                    <svg class="animate-spin h-8 w-8 text-emerald-500 mb-2" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                    <p class="text-sm text-emerald-400 font-medium">Uploading & Restoring...</p>
                {:else}
                    <svg class="w-8 h-8 mb-3 text-gray-500 group-hover:text-gray-400" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 20 16">
                        <path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 13h3a3 3 0 0 0 0-6h-.025A5.56 5.56 0 0 0 16 6.5 5.5 5.5 0 0 0 5.207 5.021C5.137 5.017 5.071 5 5 5a4 4 0 0 0 0 8h2.167M10 15V6m0 0L8 8m2-2 2 2"/>
                    </svg>
                    <p class="mb-2 text-sm text-gray-400"><span class="font-semibold">Click to upload</span> or drag and drop</p>
                    <p class="text-xs text-gray-500">ZIP Backup File (from another server)</p>
                {/if}
            </div>
            <input type="file" class="hidden" accept=".zip" on:change={handleFileUpload} disabled={uploading} />
        </label>
    </div>
</div>

<style>
    /* Add any custom styles here if needed */
</style>
