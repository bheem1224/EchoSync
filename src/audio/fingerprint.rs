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

    let duration_seconds = (samples.len() as f64) / (original_sample_rate as f64);

    // Convert f32 PCM to 16-bit signed integer samples for Chromaprint
    let i16_samples: Vec<i16> = processed_samples
        .iter()
        .map(|&s| {
            let clamped = s.clamp(-1.0, 1.0);
            (clamped * 32767.0) as i16
        })
        .collect();

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
