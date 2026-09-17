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

pub fn generate_fingerprint(file_path: &str, trim_silence: bool) -> Result<(String, f64), String> {
    let path = Path::new(file_path);

    // Inner scope: all Symphonia format readers, decoders, and packet buffers are
    // dropped here before the chromaprint encoding step crosses the FFI boundary.
    let (samples, original_sample_rate) = {
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

        let mut samples: Vec<f32> = Vec::new();

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
                    append_mono_samples(&decoded, &mut samples);
                }
                Err(SymphoniaError::IoError(_)) => break,
                Err(SymphoniaError::DecodeError(_)) => continue,
                Err(_) => break,
            }
        }

        // format, decoder, and all packet/SampleBuffer state drop here.
        (samples, original_sample_rate)
    };

    if samples.is_empty() {
        return Err("No audio samples decoded".to_string());
    }

    // Silence trimming (< -60 dBFS = amplitude < 0.001)
    let processed_samples = if trim_silence {
        let silence_threshold = 0.001f32;
        let start = samples
            .iter()
            .position(|&s| s.abs() >= silence_threshold)
            .unwrap_or(0);
        let end = samples
            .iter()
            .rposition(|&s| s.abs() >= silence_threshold)
            .map(|idx| idx + 1)
            .unwrap_or(samples.len());

        if start < end {
            &samples[start..end]
        } else {
            &samples[..]
        }
    } else {
        &samples[..]
    };

    if processed_samples.is_empty() {
        return Err("Audio is completely silent".to_string());
    }

    // Full track duration derived from total decoded samples (unaffected by fingerprint window)
    let duration_seconds = (samples.len() as f64) / (original_sample_rate as f64);

    let trimmed_f32: Vec<f32> = processed_samples.to_vec();
    drop(samples); // Free ~52 MiB monolithic decode buffer before next allocation

    // Convert f32 PCM to 16-bit signed integer samples for Chromaprint
    let i16_samples: Vec<i16> = trimmed_f32
        .iter()
        .map(|&s| {
            let clamped = s.clamp(-1.0, 1.0);
            (clamped * 32767.0) as i16
        })
        .collect();
    drop(trimmed_f32); // Free intermediate window buffer

    // AcoustID / fpcalc standard: fingerprint only the first 120 seconds of audio.
    // Feeding more samples produces a hash that diverges from the AcoustID cluster index.
    const CHROMAPRINT_MAX_SECONDS: f64 = 120.0;
    let max_samples = (CHROMAPRINT_MAX_SECONDS * original_sample_rate as f64) as usize;
    let fingerprint_window: &[i16] = if i16_samples.len() > max_samples {
        &i16_samples[..max_samples]
    } else {
        &i16_samples[..]
    };

    let config = Configuration::preset_test2();
    let mut printer = Fingerprinter::new(&config);
    printer
        .start(original_sample_rate, 1)
        .map_err(|e| format!("Failed to start fingerprinter: {e:?}"))?;

    printer.consume(fingerprint_window);
    printer.finish();

    let raw_fp = printer.fingerprint();
    let compressor = rusty_chromaprint::FingerprintCompressor::from(&config);
    let compressed = compressor.compress(raw_fp);
    let encoded_fingerprint = base64_encode(&compressed);

    Ok((encoded_fingerprint, duration_seconds))
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
    let (samples, original_sample_rate, pcm_hash) = {
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

        let mut samples: Vec<f32> = Vec::new();
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
                    append_mono_samples(&decoded, &mut samples);

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

        if samples.is_empty() {
            return Err("No audio samples decoded".to_string());
        }

        if hash_sample_count == 0 {
            return Err("No audio samples decoded for PCM hashing".to_string());
        }

        let pcm_hash = hasher.finalize().to_hex().to_string();
        // format, decoder, hasher, and all packet/SampleBuffer state drop here.
        (samples, original_sample_rate, pcm_hash)
    };

    // Silence trimming (< -60 dBFS = amplitude < 0.001)
    let processed_samples = if trim_silence {
        let silence_threshold = 0.001f32;
        let start = samples
            .iter()
            .position(|&s| s.abs() >= silence_threshold)
            .unwrap_or(0);
        let end = samples
            .iter()
            .rposition(|&s| s.abs() >= silence_threshold)
            .map(|idx| idx + 1)
            .unwrap_or(samples.len());

        if start < end {
            &samples[start..end]
        } else {
            &samples[..]
        }
    } else {
        &samples[..]
    };

    if processed_samples.is_empty() {
        return Err("Audio is completely silent".to_string());
    }

    // Full track duration derived from total decoded samples (unaffected by fingerprint window)
    let duration_seconds = (samples.len() as f64) / (original_sample_rate as f64);

    let trimmed_f32: Vec<f32> = processed_samples.to_vec();
    drop(samples); // Free ~52 MiB monolithic decode buffer before next allocation

    // Convert f32 PCM to 16-bit signed integer samples for Chromaprint
    let i16_samples: Vec<i16> = trimmed_f32
        .iter()
        .map(|&s| {
            let clamped = s.clamp(-1.0, 1.0);
            (clamped * 32767.0) as i16
        })
        .collect();
    drop(trimmed_f32); // Free intermediate window buffer

    // AcoustID / fpcalc standard: fingerprint only the first 120 seconds of audio.
    // Feeding more samples produces a hash that diverges from the AcoustID cluster index.
    const CHROMAPRINT_MAX_SECONDS: f64 = 120.0;
    let max_samples = (CHROMAPRINT_MAX_SECONDS * original_sample_rate as f64) as usize;
    let fingerprint_window: &[i16] = if i16_samples.len() > max_samples {
        &i16_samples[..max_samples]
    } else {
        &i16_samples[..]
    };

    let config = Configuration::preset_test2();
    let mut printer = Fingerprinter::new(&config);
    printer
        .start(original_sample_rate, 1)
        .map_err(|e| format!("Failed to start fingerprinter: {e:?}"))?;

    printer.consume(fingerprint_window);
    printer.finish();

    let raw_fp = printer.fingerprint();
    let compressor = rusty_chromaprint::FingerprintCompressor::from(&config);
    let compressed = compressor.compress(raw_fp);
    let encoded_fingerprint = base64_encode(&compressed);

    Ok((encoded_fingerprint, duration_seconds, pcm_hash))
}
