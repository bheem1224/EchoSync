export interface EchoSyncMedia {
    media_id: string;
    file_path: string;
    file_format?: string;
    bitrate?: number;
    sample_rate?: number;
    bit_depth?: number;
    channels?: number;
    file_size_bytes?: number;
    mtime?: number;
}

export interface EchoSyncTrack {
    sync_id: string;
    id?: number;
    title: string;
    raw_title?: string;
    display_title?: string;
    artist_name?: string;
    artist_id: number;
    album_title?: string;
    album_id: number;
    duration?: number;
    track_number?: number;
    disc_number?: number;
    release_year?: number;
    musicbrainz_id?: string;
    isrc?: string;
    media_ids?: string[];
    media?: EchoSyncMedia[];
}
