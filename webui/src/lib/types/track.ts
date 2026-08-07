export interface EchoSyncTrack {
    sync_id: string;
    id?: number;
    title: string;
    raw_title?: string;
    display_title?: string;
    artist_name?: string;
    artist_id?: number;
    album_title?: string;
    album_id?: number;
    duration?: number;
    track_number?: number;
    disc_number?: number;
    release_year?: number;
    musicbrainz_id?: string;
    isrc?: string;
    media_ids?: string[];
}
