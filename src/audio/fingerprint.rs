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
}
