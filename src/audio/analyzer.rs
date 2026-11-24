//! Standalone PCM audio quality analyzer for EchoSync.
//!
//! Single-entry-point analysis over decoded `f32` mono PCM samples:
//! 1. **Spectral brick-wall transcode detection** (fake lossless FLAC/WAV/ALAC)
//!    using a zero-dependency radix-2 Cooley-Tukey FFT with Hann windowing.
//! 2. **Mid-track digital-zero silence dropout detection** (corrupt rip / P2P drop).
//!
//! Designed to run in parallel with Chromaprint via `rayon::join` over the exact
//! same decoded PCM buffer already in memory, and reusable by any subsystem.

use std::f32::consts::PI;

/// Result of analyzing a decoded PCM audio stream.
#[derive(Debug, Clone)]
pub struct AudioAnalysisReport {
    pub is_fake_lossless: bool,
    pub estimated_cutoff_hz: f32,
    pub high_freq_drop_db: f32,
    pub has_interior_silence_dropout: bool,
    pub max_interior_silence_ms: u64,
    pub decode_error_count: u32,
    pub is_corrupt: bool,
}

const FFT_SIZE: usize = 4096;
/// Hard digital-zero threshold (-120 dBFS) to distinguish corrupt P2P dropouts
/// from natural quiet musical passages / reverb tails (-60 to -85 dBFS).
const DIGITAL_ZERO_THRESHOLD: f32 = 1e-6;
/// Minimum continuous interior digital-zero gap (ms) considered a corrupt dropout.
const DROPOUT_MIN_MS: u64 = 1500;

/// Analyze a decoded mono `f32` PCM buffer for spectral transcode shelves and
/// interior digital-zero silence dropouts.
pub fn analyze_pcm(samples: &[f32], sample_rate: u32, check_spectral: bool) -> AudioAnalysisReport {
    if samples.is_empty() || sample_rate == 0 {
        return AudioAnalysisReport {
            is_fake_lossless: false,
            estimated_cutoff_hz: 0.0,
            high_freq_drop_db: 0.0,
            has_interior_silence_dropout: false,
            max_interior_silence_ms: 0,
            decode_error_count: 0,
            is_corrupt: true,
        };
    }

    let max_interior_silence_ms = detect_interior_digital_zero_ms(samples, sample_rate);
    let has_interior_silence_dropout = max_interior_silence_ms >= DROPOUT_MIN_MS;

    let (is_fake_lossless, estimated_cutoff_hz, high_freq_drop_db) =
        if check_spectral && sample_rate >= 44100 && samples.len() >= FFT_SIZE {
            detect_spectral_transcode(samples, sample_rate)
        } else {
            (false, (sample_rate as f32) / 2.0, 0.0)
        };

    AudioAnalysisReport {
        is_fake_lossless,
        estimated_cutoff_hz,
        high_freq_drop_db,
        has_interior_silence_dropout,
        max_interior_silence_ms,
        decode_error_count: 0,
        is_corrupt: false,
    }
}

/// Measure the longest contiguous run of hard digital-zero samples (`|s| < 1e-6`)
/// strictly between the first and last non-silent sample in the buffer.
pub fn detect_interior_digital_zero_ms(samples: &[f32], sample_rate: u32) -> u64 {
    if samples.is_empty() || sample_rate == 0 {
        return 0;
    }
    let active_threshold = 0.001f32; // -60 dBFS for outer active boundaries
    let first = match samples.iter().position(|&s| s.abs() >= active_threshold) {
        Some(idx) => idx,
        None => return 0,
    };
    let last = match samples.iter().rposition(|&s| s.abs() >= active_threshold) {
        Some(idx) => idx,
        None => return 0,
    };
    if last <= first {
        return 0;
    }

    let mut current_zero_run: u64 = 0;
    let mut max_zero_run: u64 = 0;
    for &s in &samples[first..=last] {
        if s.abs() < DIGITAL_ZERO_THRESHOLD {
            current_zero_run += 1;
            if current_zero_run > max_zero_run {
                max_zero_run = current_zero_run;
            }
        } else {
            current_zero_run = 0;
        }
    }

    ((max_zero_run as f64) * 1000.0 / (sample_rate as f64)).round() as u64
}

/// Detect brick-wall low-pass frequency cutoffs characteristic of lossy MP3/AAC
/// transcodes disguised inside lossless containers (FLAC/WAV/ALAC).
///
/// Samples up to 24 evenly spaced active 4096-sample Hann-windowed frames,
/// computes their average magnitude spectrum, and compares `11–15 kHz` energy
/// against `16.5–19.5 kHz` and `19.5–21.5 kHz`.
fn detect_spectral_transcode(samples: &[f32], sample_rate: u32) -> (bool, f32, f32) {
    let nyquist = (sample_rate as f32) / 2.0;
    let num_windows = 24usize;
    let available = samples.len().saturating_sub(FFT_SIZE);
    let step = (available / num_windows.max(1)).max(FFT_SIZE);

    // Precompute Hann window once
    let mut hann = [0.0f32; FFT_SIZE];
    for (i, w) in hann.iter_mut().enumerate() {
        *w = 0.5 * (1.0 - (2.0 * PI * (i as f32) / ((FFT_SIZE - 1) as f32)).cos());
    }

    let half_bins = FFT_SIZE / 2;
    let mut avg_power = vec![0.0f64; half_bins];
    let mut valid_frames = 0usize;

    let mut re = vec![0.0f32; FFT_SIZE];
    let mut im = vec![0.0f32; FFT_SIZE];

    let mut offset = 0usize;
    while offset + FFT_SIZE <= samples.len() && valid_frames < num_windows {
        let slice = &samples[offset..offset + FFT_SIZE];
        // Skip silent or near-silent frames (RMS < -45 dBFS)
        let energy: f32 = slice.iter().map(|&x| x * x).sum::<f32>() / (FFT_SIZE as f32);
        if energy > 3.16e-5 {
            for i in 0..FFT_SIZE {
                re[i] = slice[i] * hann[i];
                im[i] = 0.0;
            }
            fft_radix2_in_place(&mut re, &mut im);
            let scale = 1.0f64 / ((FFT_SIZE as f64) * (FFT_SIZE as f64));
            for bin in 0..half_bins {
                let p = ((re[bin] as f64) * (re[bin] as f64) + (im[bin] as f64) * (im[bin] as f64))
                    * scale;
                avg_power[bin] += p;
            }
            valid_frames += 1;
        }
        offset += step;
    }

    if valid_frames < 3 {
        return (false, nyquist, 0.0);
    }

    for p in &mut avg_power {
        *p /= valid_frames as f64;
    }

    let hz_per_bin = (sample_rate as f32) / (FFT_SIZE as f32);
    let band_db = |low_hz: f32, high_hz: f32| -> f32 {
        let b0 = ((low_hz / hz_per_bin).floor() as usize).clamp(1, half_bins - 1);
        let b1 = ((high_hz / hz_per_bin).ceil() as usize).clamp(b0 + 1, half_bins);
        let sum: f64 = avg_power[b0..b1].iter().sum();
        let mean = sum / ((b1 - b0) as f64);
        if mean <= 1e-12 {
            -120.0
        } else {
            (10.0 * mean.log10()) as f32
        }
    };

    let mid_high_db = band_db(11000.0, 15000.0);
    let shelf_16_db = band_db(16500.0, 19500.0);
    let upper_19_db = band_db(19500.0, nyquist.min(21500.0));

    // Audiophile guard: warm vintage recordings, solo piano, or lo-fi tracks lack
    // strong energy even in 11–15 kHz. Only flag brick-wall cutoffs when 11–15 kHz
    // is clearly active (> -58 dBFS).
    if mid_high_db <= -58.0 {
        return (false, nyquist, 0.0);
    }

    let drop_16 = mid_high_db - shelf_16_db;
    let drop_19 = mid_high_db - upper_19_db;

    // 128–160 kbps MP3 / AAC transcode brick-wall at ~16 kHz
    if shelf_16_db < -80.0 && drop_16 > 35.0 {
        return (true, 16000.0, drop_16);
    }

    // 192 kbps MP3 transcode brick-wall at ~18–19 kHz
    if mid_high_db > -50.0 && upper_19_db < -85.0 && drop_19 > 40.0 && shelf_16_db < -72.0 {
        return (true, 18500.0, drop_19);
    }

    let est_cutoff = if upper_19_db > -75.0 {
        nyquist
    } else if shelf_16_db > -75.0 {
        19500.0
    } else {
        16000.0
    };

    (false, est_cutoff, drop_16.max(0.0))
}

/// Iterative in-place radix-2 Cooley-Tukey FFT (`re.len()` must be a power of 2).
fn fft_radix2_in_place(re: &mut [f32], im: &mut [f32]) {
    let n = re.len();
    debug_assert!(n.is_power_of_two() && im.len() == n);

    // Bit-reversal permutation
    let mut j = 0usize;
    for i in 1..n {
        let mut bit = n >> 1;
        while j & bit != 0 {
            j ^= bit;
            bit >>= 1;
        }
        j ^= bit;
        if i < j {
            re.swap(i, j);
            im.swap(i, j);
        }
    }

    // Butterfly stages
    let mut len = 2usize;
    while len <= n {
        let half = len >> 1;
        let angle = -2.0 * PI / (len as f32);
        let wlen_re = angle.cos();
        let wlen_im = angle.sin();

        let mut start = 0usize;
        while start < n {
            let mut w_re = 1.0f32;
            let mut w_im = 0.0f32;
            for k in 0..half {
                let u_idx = start + k;
                let v_idx = start + k + half;
                let u_re = re[u_idx];
                let u_im = im[u_idx];
                let v_re = re[v_idx] * w_re - im[v_idx] * w_im;
                let v_im = re[v_idx] * w_im + im[v_idx] * w_re;

                re[u_idx] = u_re + v_re;
                im[u_idx] = u_im + v_im;
                re[v_idx] = u_re - v_re;
                im[v_idx] = u_im - v_im;

                let next_w_re = w_re * wlen_re - w_im * wlen_im;
                w_im = w_re * wlen_im + w_im * wlen_re;
                w_re = next_w_re;
            }
            start += len;
        }
        len <<= 1;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn lcg_noise(count: usize) -> Vec<f32> {
        let mut state: u64 = 0x1234_5678_9abc_def0;
        (0..count)
            .map(|_| {
                state = state.wrapping_mul(6364136223846793005).wrapping_add(1);
                let bits = ((state >> 33) as u32) as f32 / (u32::MAX as f32);
                (bits * 2.0 - 1.0) * 0.5
            })
            .collect()
    }

    #[test]
    fn test_broadband_signal_passes_spectral_check() {
        let sr = 44100u32;
        let samples = lcg_noise((sr as usize) * 3);
        let report = analyze_pcm(&samples, sr, true);
        assert!(!report.is_fake_lossless, "Broadband lossless signal should pass: {:?}", report);
        assert!(!report.has_interior_silence_dropout);
    }

    #[test]
    fn test_brickwall_16khz_transcode_flagged_fake() {
        let sr = 44100u32;
        let n = (sr as usize) * 3;
        // Synthesize active tones at 1 kHz, 12 kHz, and 14 kHz with zero energy above 16 kHz
        let samples: Vec<f32> = (0..n)
            .map(|i| {
                let t = (i as f32) / (sr as f32);
                0.3 * (2.0 * PI * 1000.0 * t).sin()
                    + 0.25 * (2.0 * PI * 12000.0 * t).sin()
                    + 0.25 * (2.0 * PI * 14000.0 * t).sin()
            })
            .collect();
        let report = analyze_pcm(&samples, sr, true);
        assert!(report.is_fake_lossless, "Brick-wall 14kHz cutoff should be flagged fake: {:?}", report);
        assert!(report.estimated_cutoff_hz <= 16500.0);
    }

    #[test]
    fn test_warm_low_freq_signal_not_false_positive() {
        let sr = 44100u32;
        let n = (sr as usize) * 3;
        // Pure 440 Hz tone (simulates solo piano / warm vintage recording with no 12-15 kHz energy)
        let samples: Vec<f32> = (0..n)
            .map(|i| 0.4 * (2.0 * PI * 440.0 * (i as f32) / (sr as f32)).sin())
            .collect();
        let report = analyze_pcm(&samples, sr, true);
        assert!(!report.is_fake_lossless, "Warm low-frequency track must not false-flag: {:?}", report);
    }

    #[test]
    fn test_mid_track_digital_zero_dropout_detected() {
        let sr = 44100u32;
        let mut samples = lcg_noise((sr as usize) * 5);
        // Inject a 2.0-second exact digital-zero dropout in the middle
        let start = (sr as usize) * 2;
        let end = (sr as usize) * 4;
        for s in &mut samples[start..end] {
            *s = 0.0;
        }
        let report = analyze_pcm(&samples, sr, false);
        assert!(report.has_interior_silence_dropout);
        assert!(report.max_interior_silence_ms >= 1950);
    }

    #[test]
    fn test_leading_and_trailing_silence_ignored() {
        let sr = 44100u32;
        let mut samples = vec![0.0f32; (sr as usize) * 2];
        samples.extend(lcg_noise((sr as usize) * 2));
        samples.extend(vec![0.0f32; (sr as usize) * 2]);
        let report = analyze_pcm(&samples, sr, false);
        assert!(!report.has_interior_silence_dropout);
    }
}
