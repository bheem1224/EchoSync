use std::fs::File;
use std::path::Path;
use symphonia::core::codecs::CODEC_TYPE_NULL;
use symphonia::core::errors::Error as SymphoniaError;
use symphonia::core::formats::FormatOptions;
use symphonia::core::io::MediaSourceStream;
use symphonia::core::meta::MetadataOptions;
use symphonia::core::probe::Hint;

/// Compute deterministic BLAKE3 hash strictly over raw decoded PCM audio frames,
/// stripping all container headers, ID3 tags, and Vorbis comments.
pub fn hash_pcm_stream(file_path: &str) -> Result<String, String> {
    let path = Path::new(file_path);
    let file = File::open(path).map_err(|e| format!("Failed to open file: {e}"))?;
    let mss = MediaSourceStream::new(Box::new(file), Default::default());

    let mut hint = Hint::new();
    if let Some(ext) = path.extension().and_then(|s| s.to_str()) {
        hint.with_extension(ext);
    }

    let meta_opts: MetadataOptions = Default::default();
    let fmt_opts: FormatOptions = Default::default();

    let probed = symphonia::default::get_probe()
        .format(&hint, mss, &fmt_opts, &meta_opts)
        .map_err(|e| format!("Unsupported format or probe failure: {e}"))?;

    let mut format = probed.format;
    let track = format
        .tracks()
        .iter()
        .find(|t| t.codec_params.codec != CODEC_TYPE_NULL)
        .ok_or_else(|| "No supported audio track found in file".to_string())?;

    let mut decoder = symphonia::default::get_codecs()
        .make(&track.codec_params, &Default::default())
        .map_err(|e| format!("Unsupported codec: {e}"))?;

    let track_id = track.id;
    let mut hasher = blake3::Hasher::new();
    let mut sample_count = 0usize;

    loop {
        let packet = match format.next_packet() {
            Ok(packet) => packet,
            Err(SymphoniaError::IoError(ref err))
                if err.kind() == std::io::ErrorKind::UnexpectedEof =>
            {
                break;
            }
            Err(SymphoniaError::ResetRequired) => {
                decoder.reset();
                continue;
            }
            Err(_) => break,
        };

        if packet.track_id() != track_id {
            continue;
        }

        match decoder.decode(&packet) {
            Ok(decoded) => {
                let spec = *decoded.spec();
                let mut sample_buf =
                    symphonia::core::audio::SampleBuffer::<f32>::new(decoded.capacity() as u64, spec);
                sample_buf.copy_interleaved_ref(decoded);
                for sample in sample_buf.samples() {
                    hasher.update(&sample.to_le_bytes());
                    sample_count += 1;
                }
            }
            Err(SymphoniaError::IoError(_)) => break,
            Err(SymphoniaError::DecodeError(_)) => continue,
            Err(_) => break,
        }
    }

    if sample_count == 0 {
        return Err("No audio samples decoded for PCM hashing".to_string());
    }

    Ok(hasher.finalize().to_hex().to_string())
}

/// Derive canonical content-addressed acoustic proof ECHOSYNC_SIGNATURE.
///
/// Formula: BLAKE3(pcm_hash:title:artist)
/// Normalized with trim and lowercase to be portable and anonymous across instances.
pub fn derive_signature(pcm_hash: &str, title: &str, artist: &str) -> String {
    let payload = format!(
        "{}:{}:{}",
        pcm_hash.trim().to_lowercase(),
        title.trim().to_lowercase(),
        artist.trim().to_lowercase()
    );
    blake3::hash(payload.as_bytes()).to_hex().to_string()
}

/// Verify content-addressed acoustic proof against physical audio file.
pub fn verify_signature(
    file_path: &str,
    title: &str,
    artist: &str,
    expected_sig: &str,
) -> Result<bool, String> {
    let pcm_hash = hash_pcm_stream(file_path)?;
    let actual_sig = derive_signature(&pcm_hash, title, artist);
    Ok(actual_sig.eq_ignore_ascii_case(expected_sig.trim()))
}
