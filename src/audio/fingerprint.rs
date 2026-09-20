use rusty_chromaprint::{Configuration, Fingerprinter};
use std::fs::File;
use std::path::Path;
use symphonia::core::audio::{AudioBufferRef, Signal};
use symphonia::core::codecs::{DecoderOptions, CODEC_TYPE_NULL};
use symphonia::core::errors::Error as SymphoniaError;
use symphonia::core::formats::FormatOptions;
use symphonia::core::io::MediaSourceStream;
use symphonia::core::meta::MetadataOptions;
use symphonia::core::probe::Hint;

const MAX_FINGERPRINT_SECONDS: f64 = 120.0;

pub fn generate_fingerprint(file_path: &str, trim_silence: bool) -> Result<(String, f64), String> {
    let path = Path::new(file_path);

    // Inner scope: all Symphonia format readers, decoders, and packet buffers are
    // dropped here before the chromaprint encoding step crosses the FFI boundary.
    let (samples, original_sample_rate, total_decoded_frames) = {
        let src = File::open(path).map_err(|e| format!("Failed to open file: {e}"))?;
        let mss = MediaSourceStream::new(Box::new(src), Default::default());

        let mut hint = Hint::new();
        if let Some(extension) = path.extension().and_then(|ext| ext.to_str()) {
            hint.with_extension(extension);
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

        let dec_opts: DecoderOptions = Default::default();
        let mut decoder = symphonia::default::get_codecs()
            .make(&track.codec_params, &dec_opts)
            .map_err(|e| format!("Unsupported codec: {e}"))?;

        let track_id = track.id;
        let original_sample_rate = track
            .codec_params
            .sample_rate
            .ok_or_else(|| "Unknown sample rate".to_string())?;

        let max_samples = (original_sample_rate as f64 * MAX_FINGERPRINT_SECONDS) as usize;
        let mut samples: Vec<f32> = Vec::new();
        let mut total_decoded_frames: u64 = 0;
        let mut found_audio_start = !trim_silence;

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
                Err(_) => {
                    break;
                }
            };

            if packet.track_id() != track_id {
                continue;
            }

            match decoder.decode(&packet) {
                Ok(decoded) => {
                    total_decoded_frames += decoded.frames() as u64;
                    append_mono_samples_clamped(
                        &decoded,
                        &mut samples,
                        max_samples,
                        trim_silence,
                        &mut found_audio_start,
                    );
                }
                Err(SymphoniaError::IoError(_)) => break,
                Err(SymphoniaError::DecodeError(_)) => continue,
                Err(_) => break,
            }
        }

        // format, decoder, and all packet/SampleBuffer state drop here.
        (samples, original_sample_rate, total_decoded_frames)
    };

    if total_decoded_frames == 0 {
        return Err("No audio samples decoded".to_string());
    }

    if samples.is_empty() {
        return Err("Audio is completely silent".to_string());
    }

    // Silence trimming: leading silence was already skipped during decoding.
    // Trim any trailing silence from the clamped window if applicable.
    let processed_samples = if trim_silence {
        let silence_threshold = 0.001f32;
        let end = samples
            .iter()
            .rposition(|&s| s.abs() >= silence_threshold)
            .map(|idx| idx + 1)
            .unwrap_or(samples.len());

        &samples[..end]
    } else {
        &samples[..]
    };

    if processed_samples.is_empty() {
        return Err("Audio is completely silent".to_string());
    }

    // Full track duration derived from total decoded frames (unaffected by fingerprint window clamp)
    let duration_seconds = (total_decoded_frames as f64) / (original_sample_rate as f64);

    let trimmed_f32: Vec<f32> = processed_samples.to_vec();
    drop(samples); // Free intermediate decode buffer before next allocation

    // Convert f32 PCM to 16-bit signed integer samples for Chromaprint
    let i16_samples: Vec<i16> = trimmed_f32
        .iter()
        .map(|&s| {
            let clamped = s.clamp(-1.0, 1.0);
            (clamped * 32767.0) as i16
        })
        .collect();
    drop(trimmed_f32); // Free intermediate window buffer

    let config = Configuration::preset_test2();
    let mut printer = Fingerprinter::new(&config);
    printer
        .start(original_sample_rate, 1)
        .map_err(|e| format!("Failed to start fingerprinter: {e:?}"))?;

    printer.consume(&i16_samples);
    printer.finish();

    let raw_fp = printer.fingerprint();
    let compressor = rusty_chromaprint::FingerprintCompressor::from(&config);
    let compressed = compressor.compress(raw_fp);
    let encoded_fingerprint = base64_encode(&compressed);

    Ok((encoded_fingerprint, duration_seconds))
}

fn append_mono_samples_clamped(
    decoded: &AudioBufferRef,
    out: &mut Vec<f32>,
    max_samples: usize,
    trim_silence: bool,
    found_audio_start: &mut bool,
) {
    if out.len() >= max_samples {
        return;
    }

    let silence_threshold = 0.001f32;
    let mut packet_samples = Vec::with_capacity(decoded.frames());
    append_mono_samples(decoded, &mut packet_samples);

    let to_take = if trim_silence && !*found_audio_start {
        // Look for the first non-silent sample in this packet
        if let Some(pos) = packet_samples
            .iter()
            .position(|&s| s.abs() >= silence_threshold)
        {
            *found_audio_start = true;
            &packet_samples[pos..]
        } else {
            // Entire packet is leading silence, skip it
            return;
        }
    } else {
        &packet_samples[..]
    };

    let remaining_capacity = max_samples.saturating_sub(out.len());
    if to_take.len() <= remaining_capacity {
        out.extend_from_slice(to_take);
    } else {
        out.extend_from_slice(&to_take[..remaining_capacity]);
    }
}

fn append_mono_samples(decoded: &AudioBufferRef, out: &mut Vec<f32>) {
    match decoded {
        AudioBufferRef::F32(buf) => {
            let num_channels = buf.spec().channels.count();
            let num_frames = buf.frames();
            if num_channels == 1 {
                out.extend_from_slice(buf.chan(0));
            } else {
                for frame in 0..num_frames {
                    let mut sum = 0.0f32;
                    for ch in 0..num_channels {
                        sum += buf.chan(ch)[frame];
                    }
                    out.push(sum / (num_channels as f32));
                }
            }
        }
        AudioBufferRef::U8(buf) => {
            let num_channels = buf.spec().channels.count();
            let num_frames = buf.frames();
            for frame in 0..num_frames {
                let mut sum = 0.0f32;
                for ch in 0..num_channels {
                    let val = (buf.chan(ch)[frame] as f32 - 128.0) / 128.0;
                    sum += val;
                }
                out.push(sum / (num_channels as f32));
            }
        }
        AudioBufferRef::U16(buf) => {
            let num_channels = buf.spec().channels.count();
            let num_frames = buf.frames();
            for frame in 0..num_frames {
                let mut sum = 0.0f32;
                for ch in 0..num_channels {
                    let val = (buf.chan(ch)[frame] as f32 - 32768.0) / 32768.0;
                    sum += val;
                }
                out.push(sum / (num_channels as f32));
            }
        }
        AudioBufferRef::U24(buf) => {
            let num_channels = buf.spec().channels.count();
            let num_frames = buf.frames();
            for frame in 0..num_frames {
                let mut sum = 0.0f32;
                for ch in 0..num_channels {
                    let val = (buf.chan(ch)[frame].0 as f32 - 8388608.0) / 8388608.0;
                    sum += val;
                }
                out.push(sum / (num_channels as f32));
            }
        }
        AudioBufferRef::U32(buf) => {
            let num_channels = buf.spec().channels.count();
            let num_frames = buf.frames();
            for frame in 0..num_frames {
                let mut sum = 0.0f32;
                for ch in 0..num_channels {
                    let val = (buf.chan(ch)[frame] as f32 - 2147483648.0) / 2147483648.0;
                    sum += val;
                }
                out.push(sum / (num_channels as f32));
            }
        }
        AudioBufferRef::S8(buf) => {
            let num_channels = buf.spec().channels.count();
            let num_frames = buf.frames();
            for frame in 0..num_frames {
                let mut sum = 0.0f32;
                for ch in 0..num_channels {
                    let val = (buf.chan(ch)[frame] as f32) / 128.0;
                    sum += val;
                }
                out.push(sum / (num_channels as f32));
            }
        }
        AudioBufferRef::S16(buf) => {
            let num_channels = buf.spec().channels.count();
            let num_frames = buf.frames();
            if num_channels == 1 {
                for &sample in buf.chan(0) {
                    out.push((sample as f32) / 32768.0);
                }
            } else {
                for frame in 0..num_frames {
                    let mut sum = 0.0f32;
                    for ch in 0..num_channels {
                        sum += (buf.chan(ch)[frame] as f32) / 32768.0;
                    }
                    out.push(sum / (num_channels as f32));
                }
            }
        }
        AudioBufferRef::S24(buf) => {
            let num_channels = buf.spec().channels.count();
            let num_frames = buf.frames();
            for frame in 0..num_frames {
                let mut sum = 0.0f32;
                for ch in 0..num_channels {
                    sum += (buf.chan(ch)[frame].0 as f32) / 8388608.0;
                }
                out.push(sum / (num_channels as f32));
            }
        }
        AudioBufferRef::S32(buf) => {
            let num_channels = buf.spec().channels.count();
            let num_frames = buf.frames();
            for frame in 0..num_frames {
                let mut sum = 0.0f32;
                for ch in 0..num_channels {
                    sum += (buf.chan(ch)[frame] as f32) / 2147483648.0;
                }
                out.push(sum / (num_channels as f32));
            }
        }
        AudioBufferRef::F64(buf) => {
            let num_channels = buf.spec().channels.count();
            let num_frames = buf.frames();
            for frame in 0..num_frames {
                let mut sum = 0.0f32;
                for ch in 0..num_channels {
                    sum += buf.chan(ch)[frame] as f32;
                }
                out.push(sum / (num_channels as f32));
            }
        }
    }
}

fn base64_encode(data: &[u8]) -> String {
    const URL_SAFE_CHARS: &[u8; 64] =
        b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
    let mut result = String::with_capacity((data.len() + 2) / 3 * 4);
    let mut chunks = data.chunks_exact(3);

    for chunk in &mut chunks {
        let b = ((chunk[0] as u32) << 16) | ((chunk[1] as u32) << 8) | (chunk[2] as u32);
        result.push(URL_SAFE_CHARS[((b >> 18) & 0x3F) as usize] as char);
        result.push(URL_SAFE_CHARS[((b >> 12) & 0x3F) as usize] as char);
        result.push(URL_SAFE_CHARS[((b >> 6) & 0x3F) as usize] as char);
        result.push(URL_SAFE_CHARS[(b & 0x3F) as usize] as char);
    }

    let rem = chunks.remainder();
    if rem.len() == 1 {
        let b = (rem[0] as u32) << 16;
        result.push(URL_SAFE_CHARS[((b >> 18) & 0x3F) as usize] as char);
        result.push(URL_SAFE_CHARS[((b >> 12) & 0x3F) as usize] as char);
    } else if rem.len() == 2 {
        let b = ((rem[0] as u32) << 16) | ((rem[1] as u32) << 8);
        result.push(URL_SAFE_CHARS[((b >> 18) & 0x3F) as usize] as char);
        result.push(URL_SAFE_CHARS[((b >> 12) & 0x3F) as usize] as char);
        result.push(URL_SAFE_CHARS[((b >> 6) & 0x3F) as usize] as char);
    }

    result
}

pub fn fingerprint_and_hash_audio(
    file_path: &str,
    trim_silence: bool,
) -> Result<(String, f64, String), String> {
    let path = Path::new(file_path);

    // Inner scope: all Symphonia format readers, decoders, packet buffers, and
    // BLAKE3 state are dropped here before the chromaprint encoding step.
    let (samples, original_sample_rate, total_decoded_frames, pcm_hash) = {
        let src = File::open(path).map_err(|e| format!("Failed to open file: {e}"))?;
        let mss = MediaSourceStream::new(Box::new(src), Default::default());

        let mut hint = Hint::new();
        if let Some(extension) = path.extension().and_then(|ext| ext.to_str()) {
            hint.with_extension(extension);
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

        let dec_opts: DecoderOptions = Default::default();
        let mut decoder = symphonia::default::get_codecs()
            .make(&track.codec_params, &dec_opts)
            .map_err(|e| format!("Unsupported codec: {e}"))?;

        let track_id = track.id;
        let original_sample_rate = track
            .codec_params
            .sample_rate
            .ok_or_else(|| "Unknown sample rate".to_string())?;

        let max_samples = (original_sample_rate as f64 * MAX_FINGERPRINT_SECONDS) as usize;
        let mut samples: Vec<f32> = Vec::new();
        let mut total_decoded_frames: u64 = 0;
        let mut found_audio_start = !trim_silence;
        let mut hasher = blake3::Hasher::new();
        let mut hash_sample_count = 0usize;

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
                Err(_) => {
                    break;
                }
            };

            if packet.track_id() != track_id {
                continue;
            }

            match decoder.decode(&packet) {
                Ok(decoded) => {
                    total_decoded_frames += decoded.frames() as u64;

                    append_mono_samples_clamped(
                        &decoded,
                        &mut samples,
                        max_samples,
                        trim_silence,
                        &mut found_audio_start,
                    );

                    let spec = *decoded.spec();
                    let mut sample_buf = symphonia::core::audio::SampleBuffer::<f32>::new(
                        decoded.capacity() as u64,
                        spec,
                    );
                    sample_buf.copy_interleaved_ref(decoded);
                    for sample in sample_buf.samples() {
                        hasher.update(&sample.to_le_bytes());
                        hash_sample_count += 1;
                    }
                    // sample_buf drops at end of this arm — no heap retention per packet
                }
                Err(SymphoniaError::IoError(_)) => break,
                Err(SymphoniaError::DecodeError(_)) => continue,
                Err(_) => break,
            }
        }

        if total_decoded_frames == 0 {
            return Err("No audio samples decoded".to_string());
        }

        if hash_sample_count == 0 {
            return Err("No audio samples decoded for PCM hashing".to_string());
        }

        let pcm_hash = hasher.finalize().to_hex().to_string();
        // format, decoder, hasher, and all packet/SampleBuffer state drop here.
        (
            samples,
            original_sample_rate,
            total_decoded_frames,
            pcm_hash,
        )
    };

    if samples.is_empty() {
        return Err("Audio is completely silent".to_string());
    }

    // Silence trimming: leading silence was already skipped during decoding.
    // Trim any trailing silence from the clamped window if applicable.
    let processed_samples = if trim_silence {
        let silence_threshold = 0.001f32;
        let end = samples
            .iter()
            .rposition(|&s| s.abs() >= silence_threshold)
            .map(|idx| idx + 1)
            .unwrap_or(samples.len());

        &samples[..end]
    } else {
        &samples[..]
    };

    if processed_samples.is_empty() {
        return Err("Audio is completely silent".to_string());
    }

    // Full track duration derived from total decoded frames (unaffected by fingerprint window clamp)
    let duration_seconds = (total_decoded_frames as f64) / (original_sample_rate as f64);

    let trimmed_f32: Vec<f32> = processed_samples.to_vec();
    drop(samples); // Free intermediate decode buffer before next allocation

    // Convert f32 PCM to 16-bit signed integer samples for Chromaprint
    let i16_samples: Vec<i16> = trimmed_f32
        .iter()
        .map(|&s| {
            let clamped = s.clamp(-1.0, 1.0);
            (clamped * 32767.0) as i16
        })
        .collect();
    drop(trimmed_f32); // Free intermediate window buffer

    let config = Configuration::preset_test2();
    let mut printer = Fingerprinter::new(&config);
    printer
        .start(original_sample_rate, 1)
        .map_err(|e| format!("Failed to start fingerprinter: {e:?}"))?;

    printer.consume(&i16_samples);
    printer.finish();

    let raw_fp = printer.fingerprint();
    let compressor = rusty_chromaprint::FingerprintCompressor::from(&config);
    let compressed = compressor.compress(raw_fp);
    let encoded_fingerprint = base64_encode(&compressed);

    Ok((encoded_fingerprint, duration_seconds, pcm_hash))
}

/// Decompress a Chromaprint compressed byte slice into a vector of u32 subfingerprints.
pub fn decompress_chromaprint(compressed: &[u8]) -> Result<Vec<u32>, String> {
    if compressed.len() < 4 {
        return Err("Compressed fingerprint data too short (must be at least 4 bytes)".to_string());
    }

    let num_subfingerprints = ((compressed[1] as usize) << 16)
        | ((compressed[2] as usize) << 8)
        | (compressed[3] as usize);

    if num_subfingerprints == 0 {
        return Ok(Vec::new());
    }

    // Helper bit reader
    struct BitReader<'a> {
        data: &'a [u8],
        bit_pos: usize,
    }

    impl<'a> BitReader<'a> {
        fn new(data: &'a [u8]) -> Self {
            Self { data, bit_pos: 0 }
        }

        fn read_bits(&mut self, n: usize) -> Option<u32> {
            let mut val = 0u32;
            for i in 0..n {
                let byte_idx = self.bit_pos / 8;
                let bit_idx = self.bit_pos % 8;
                if byte_idx >= self.data.len() {
                    return None;
                }
                let bit = (self.data[byte_idx] >> bit_idx) & 1;
                val |= (bit as u32) << i;
                self.bit_pos += 1;
            }
            Some(val)
        }
    }

    // 1. Read normal 3-bit values until we encounter `num_subfingerprints` zeros
    let mut normal_reader = BitReader::new(&compressed[4..]);
    let mut normal_values = Vec::new();
    let mut zero_count = 0;

    while zero_count < num_subfingerprints {
        let bits = normal_reader
            .read_bits(3)
            .ok_or_else(|| "Unexpected end of normal bits stream".to_string())?;
        if bits == 0 {
            zero_count += 1;
        }
        normal_values.push(bits as u8);
    }

    let normal_bytes = (normal_values.len() * 3 + 7) / 8;
    let exceptional_offset = 4 + normal_bytes;
    if exceptional_offset > compressed.len() {
        return Err("Exceptional bits offset exceeds buffer size".to_string());
    }

    let mut exp_reader = BitReader::new(&compressed[exceptional_offset..]);

    let mut fingerprint = Vec::with_capacity(num_subfingerprints);
    let mut last_subfp: u32 = 0;
    let mut current_xor: u32 = 0;
    let mut last_bit_index: u32 = 0;

    for val in normal_values {
        if val == 0 {
            let current_subfp = last_subfp ^ current_xor;
            fingerprint.push(current_subfp);
            last_subfp = current_subfp;
            current_xor = 0;
            last_bit_index = 0;
        } else {
            let delta = if val == 7 {
                let exp = exp_reader
                    .read_bits(5)
                    .ok_or_else(|| "Unexpected end of exceptional bits stream".to_string())?;
                7 + exp
            } else {
                val as u32
            };
            let bit_index = last_bit_index + delta;
            last_bit_index = bit_index;
            if bit_index >= 1 && bit_index <= 32 {
                current_xor |= 1 << (bit_index - 1);
            }
        }
    }

    Ok(fingerprint)
}

/// Decode a base64 string (URL-safe or standard, with or without padding) into bytes.
pub fn base64_decode(input: &str) -> Result<Vec<u8>, String> {
    let mut clean_bytes = Vec::with_capacity(input.len());
    for b in input.bytes() {
        if b.is_ascii_whitespace() || b == b'=' {
            continue;
        }
        let val = match b {
            b'A'..=b'Z' => b - b'A',
            b'a'..=b'z' => b - b'a' + 26,
            b'0'..=b'9' => b - b'0' + 52,
            b'+' | b'-' => 62,
            b'/' | b'_' => 63,
            _ => return Err(format!("Invalid base64 character: {}", b as char)),
        };
        clean_bytes.push(val);
    }

    let mut out = Vec::with_capacity(clean_bytes.len() * 3 / 4);
    let chunks = clean_bytes.chunks_exact(4);
    let rem = chunks.remainder();

    for c in chunks {
        let b =
            ((c[0] as u32) << 18) | ((c[1] as u32) << 12) | ((c[2] as u32) << 6) | (c[3] as u32);
        out.push(((b >> 16) & 0xFF) as u8);
        out.push(((b >> 8) & 0xFF) as u8);
        out.push((b & 0xFF) as u8);
    }

    match rem.len() {
        0 => {}
        2 => {
            let b = ((rem[0] as u32) << 18) | ((rem[1] as u32) << 12);
            out.push(((b >> 16) & 0xFF) as u8);
        }
        3 => {
            let b = ((rem[0] as u32) << 18) | ((rem[1] as u32) << 12) | ((rem[2] as u32) << 6);
            out.push(((b >> 16) & 0xFF) as u8);
            out.push(((b >> 8) & 0xFF) as u8);
        }
        1 => return Err("Invalid base64 length (1 trailing character)".to_string()),
        _ => unreachable!(),
    }

    Ok(out)
}

/// Compares two Chromaprint base64 fingerprint strings using native Rust rusty_chromaprint.
/// Returns a similarity confidence score in [0.0, 1.0].
pub fn compare_chromaprints(fp1_str: &str, fp2_str: &str) -> Result<f64, String> {
    let s1 = fp1_str.trim();
    let s2 = fp2_str.trim();

    if s1.is_empty() || s2.is_empty() {
        return Ok(0.0);
    }

    if s1 == s2 {
        return Ok(1.0);
    }

    let b1 = match base64_decode(s1) {
        Ok(b) => b,
        Err(_) => return Ok(0.0),
    };
    let b2 = match base64_decode(s2) {
        Ok(b) => b,
        Err(_) => return Ok(0.0),
    };

    let subfps1 = match decompress_chromaprint(&b1) {
        Ok(fps) => fps,
        Err(_) => return Ok(0.0),
    };
    let subfps2 = match decompress_chromaprint(&b2) {
        Ok(fps) => fps,
        Err(_) => return Ok(0.0),
    };

    if subfps1.is_empty() || subfps2.is_empty() {
        return Ok(0.0);
    }

    if subfps1 == subfps2 {
        return Ok(1.0);
    }

    let config = Configuration::preset_test2();
    let segments = match rusty_chromaprint::match_fingerprints(&subfps1, &subfps2, &config) {
        Ok(segs) => segs,
        Err(_) => return Ok(0.0),
    };

    if segments.is_empty() {
        return Ok(0.0);
    }

    let min_len = subfps1.len().min(subfps2.len()) as f64;
    let mut total_matched_score = 0.0;

    for seg in &segments {
        let bit_similarity = (1.0 - (seg.score / 32.0)).clamp(0.0, 1.0);
        total_matched_score += bit_similarity * (seg.items_count as f64);
    }

    let confidence = (total_matched_score / min_len).clamp(0.0, 1.0);
    Ok(confidence)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_chromaprint_length_bounded_to_120s() {
        let sample_rate = 44100;
        let config = Configuration::preset_test2();
        let mut printer = Fingerprinter::new(&config);
        printer.start(sample_rate, 1).unwrap();

        // 120 seconds of test audio at 44.1 kHz = 5,292,000 samples
        let max_samples = (sample_rate as f64 * MAX_FINGERPRINT_SECONDS) as usize;
        let test_samples: Vec<i16> = (0..max_samples)
            .map(|i| ((i as f32 * 0.05).sin() * 15000.0) as i16)
            .collect();

        printer.consume(&test_samples);
        printer.finish();

        let raw_fp = printer.fingerprint();
        let compressor = rusty_chromaprint::FingerprintCompressor::from(&config);
        let compressed = compressor.compress(raw_fp);
        let encoded = base64_encode(&compressed);

        assert!(
            encoded.len() <= 4000,
            "Fingerprint length ({}) exceeded 4,000 characters for 120s of audio",
            encoded.len()
        );
    }

    #[test]
    fn test_decompress_chromaprint() {
        const INPUT: [u32; 32] = [
            0x0FCAF446, 0xE3519E89, 0xD3494DD6, 0x8F219806, 0x9200D530, 0x06B1D52F, 0xB48CC681,
            0x428991C3, 0x59AFBD6B, 0x6ECFB2E5, 0xE8EB7BC3, 0x99A44270, 0x31FFEC13, 0x4A4D81DA,
            0x53887C82, 0x2BB7BEC2, 0xAB895A65, 0x9D7C0AE4, 0xDA356857, 0xE030F7D8, 0x4D428EEE,
            0x0558E019, 0xC3278998, 0xA1D035E4, 0x582E98E5, 0x44C8B708, 0x2E8BA9E2, 0xCB13BC48,
            0xB169A3D8, 0x861274AF, 0x1213EF1C, 0x1F9F06B8,
        ];

        const OUTPUT: [u8; 220] = [
            0x01, 0x00, 0x00, 0x20, 0x0A, 0xA9, 0x24, 0xD2, 0x92, 0x24, 0x48, 0x92, 0x45, 0x52,
            0x14, 0x65, 0x8B, 0x12, 0x24, 0x49, 0xA4, 0x4C, 0x61, 0x1E, 0x54, 0x89, 0xA4, 0x50,
            0x61, 0x22, 0x28, 0xCA, 0x94, 0xA9, 0x53, 0x82, 0x24, 0xC9, 0x19, 0x4D, 0x83, 0x12,
            0x29, 0x19, 0x95, 0x84, 0x8B, 0xA0, 0x2A, 0x91, 0xA4, 0x47, 0x49, 0x40, 0x69, 0x11,
            0xB3, 0x45, 0x81, 0x12, 0x26, 0xC9, 0xA3, 0x44, 0x81, 0xB2, 0x6D, 0xD9, 0x98, 0x22,
            0x59, 0x94, 0x25, 0x4B, 0x32, 0x31, 0x41, 0xC2, 0x2C, 0x91, 0x12, 0x45, 0x95, 0x90,
            0x2D, 0x51, 0x94, 0x2D, 0x4A, 0x94, 0x04, 0x8C, 0xA4, 0x24, 0x49, 0xC4, 0x64, 0xC1,
            0xD7, 0x24, 0x49, 0xE2, 0x24, 0x48, 0x32, 0x6D, 0x89, 0x92, 0xE4, 0xC8, 0x2B, 0x49,
            0x49, 0x14, 0x05, 0xC9, 0x22, 0x31, 0xDA, 0x94, 0x10, 0x49, 0xC2, 0x24, 0xC9, 0xA2,
            0x2B, 0x81, 0xA2, 0x6C, 0x49, 0xB6, 0x44, 0x8A, 0x84, 0x24, 0x4A, 0xA2, 0x44, 0x99,
            0xF2, 0x21, 0xCF, 0x14, 0x25, 0x49, 0xB2, 0x30, 0x58, 0x92, 0x30, 0x89, 0x92, 0x28,
            0x89, 0x18, 0xE4, 0x8A, 0xA4, 0x24, 0x49, 0xB2, 0x24, 0x41, 0x14, 0x25, 0x49, 0x22,
            0x66, 0xC9, 0x12, 0x48, 0x4A, 0x94, 0x84, 0xE9, 0xA4, 0x40, 0x92, 0x22, 0x3D, 0x8B,
            0x96, 0xA0, 0x4B, 0x92, 0x54, 0x49, 0xA6, 0x24, 0x48, 0xA2, 0x44, 0x89, 0x94, 0x44,
            0x49, 0x94, 0x28, 0x48, 0x16, 0x25, 0xCA, 0x72, 0x0D, 0x9B, 0x32, 0x25, 0x0B, 0xA3,
            0x00, 0xA1, 0x80, 0x01, 0x06, 0x00, 0x00, 0x04, 0x30, 0x00,
        ];

        let decompressed = decompress_chromaprint(&OUTPUT).expect("Decompression failed");
        assert_eq!(decompressed, INPUT);
    }

    #[test]
    fn test_match_fingerprints_behavior() {
        const INPUT: [u32; 32] = [
            0x0FCAF446, 0xE3519E89, 0xD3494DD6, 0x8F219806, 0x9200D530, 0x06B1D52F, 0xB48CC681,
            0x428991C3, 0x59AFBD6B, 0x6ECFB2E5, 0xE8EB7BC3, 0x99A44270, 0x31FFEC13, 0x4A4D81DA,
            0x53887C82, 0x2BB7BEC2, 0xAB895A65, 0x9D7C0AE4, 0xDA356857, 0xE030F7D8, 0x4D428EEE,
            0x0558E019, 0xC3278998, 0xA1D035E4, 0x582E98E5, 0x44C8B708, 0x2E8BA9E2, 0xCB13BC48,
            0xB169A3D8, 0x861274AF, 0x1213EF1C, 0x1F9F06B8,
        ];
        let config = Configuration::preset_test2();
        let segments = rusty_chromaprint::match_fingerprints(&INPUT, &INPUT, &config).unwrap();
        println!("Segments for identical fingerprints: {:?}", segments);
        assert!(!segments.is_empty());
    }

    #[test]
    fn test_base64_encode_decode_roundtrip() {
        let original = b"Hello, Chromaprint world! 1234567890_+/-=";
        let encoded = base64_encode(original);
        let decoded = base64_decode(&encoded).expect("base64_decode failed");
        assert_eq!(decoded, original);
    }

    #[test]
    fn test_compare_chromaprints() {
        const OUTPUT: [u8; 220] = [
            0x01, 0x00, 0x00, 0x20, 0x0A, 0xA9, 0x24, 0xD2, 0x92, 0x24, 0x48, 0x92, 0x45, 0x52,
            0x14, 0x65, 0x8B, 0x12, 0x24, 0x49, 0xA4, 0x4C, 0x61, 0x1E, 0x54, 0x89, 0xA4, 0x50,
            0x61, 0x22, 0x28, 0xCA, 0x94, 0xA9, 0x53, 0x82, 0x24, 0xC9, 0x19, 0x4D, 0x83, 0x12,
            0x29, 0x19, 0x95, 0x84, 0x8B, 0xA0, 0x2A, 0x91, 0xA4, 0x47, 0x49, 0x40, 0x69, 0x11,
            0xB3, 0x45, 0x81, 0x12, 0x26, 0xC9, 0xA3, 0x44, 0x81, 0xB2, 0x6D, 0xD9, 0x98, 0x22,
            0x59, 0x94, 0x25, 0x4B, 0x32, 0x31, 0x41, 0xC2, 0x2C, 0x91, 0x12, 0x45, 0x95, 0x90,
            0x2D, 0x51, 0x94, 0x2D, 0x4A, 0x94, 0x04, 0x8C, 0xA4, 0x24, 0x49, 0xC4, 0x64, 0xC1,
            0xD7, 0x24, 0x49, 0xE2, 0x24, 0x48, 0x32, 0x6D, 0x89, 0x92, 0xE4, 0xC8, 0x2B, 0x49,
            0x49, 0x14, 0x05, 0xC9, 0x22, 0x31, 0xDA, 0x94, 0x10, 0x49, 0xC2, 0x24, 0xC9, 0xA2,
            0x2B, 0x81, 0xA2, 0x6C, 0x49, 0xB6, 0x44, 0x8A, 0x84, 0x24, 0x4A, 0xA2, 0x44, 0x99,
            0xF2, 0x21, 0xCF, 0x14, 0x25, 0x49, 0xB2, 0x30, 0x58, 0x92, 0x30, 0x89, 0x92, 0x28,
            0x89, 0x18, 0xE4, 0x8A, 0xA4, 0x24, 0x49, 0xB2, 0x24, 0x41, 0x14, 0x25, 0x49, 0x22,
            0x66, 0xC9, 0x12, 0x48, 0x4A, 0x94, 0x84, 0xE9, 0xA4, 0x40, 0x92, 0x22, 0x3D, 0x8B,
            0x96, 0xA0, 0x4B, 0x92, 0x54, 0x49, 0xA6, 0x24, 0x48, 0xA2, 0x44, 0x89, 0x94, 0x44,
            0x49, 0x94, 0x28, 0x48, 0x16, 0x25, 0xCA, 0x72, 0x0D, 0x9B, 0x32, 0x25, 0x0B, 0xA3,
            0x00, 0xA1, 0x80, 0x01, 0x06, 0x00, 0x00, 0x04, 0x30, 0x00,
        ];

        let fp_str = base64_encode(&OUTPUT);

        // Identical fingerprints must return 1.0
        let score_same = compare_chromaprints(&fp_str, &fp_str).unwrap();
        assert!((score_same - 1.0).abs() < 1e-6);

        // Empty fingerprints must return 0.0
        let score_empty = compare_chromaprints(&fp_str, "").unwrap();
        assert_eq!(score_empty, 0.0);

        let score_empty2 = compare_chromaprints("", "").unwrap();
        assert_eq!(score_empty2, 0.0);
    }
}
