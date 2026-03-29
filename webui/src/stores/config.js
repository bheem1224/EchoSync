import apiClient from '../api/client';

/**
 * Fetch the current configuration from the backend
 */
export async function getConfig() {
  try {
    const response = await apiClient.get('/config');
    return response.data || {};
  } catch (error) {
    console.error('Failed to fetch config:', error);
    return {
      playlist_algorithm: 'DefaultPlaylistAlgorithm',
      available_algorithms: []
    };
  }
}

/**
 * Update a specific configuration value on the backend
 */
export async function setConfig(configUpdates) {
  try {
    const response = await apiClient.post('/config', configUpdates);
    return response.data || configUpdates;
  } catch (error) {
    console.error('Failed to save config:', error);
    throw error;
  }
}

/**
 * Fetch available playlist algorithms from the backend
 */
export async function getAvailableAlgorithms() {
  try {
    const response = await apiClient.get('/api/playlist-algorithms');
    return response.data || [];
  } catch (error) {
    console.error('Failed to fetch algorithms:', error);
    return ['DefaultPlaylistAlgorithm'];
  }
}
