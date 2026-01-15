use pyo3::prelude::*;
use std::time::{Instant, Duration};
use std::thread;
use std::sync::Mutex;

#[pyclass]
pub struct RateLimiter {
    capacity: f64,
    refill_rate: f64,
    state: Mutex<LimiterState>,
}

struct LimiterState {
    tokens: f64,
    last_refill: Instant,
}

#[pymethods]
impl RateLimiter {
    #[new]
    fn new(capacity: f64, refill_rate: f64) -> Self {
        RateLimiter {
            capacity,
            refill_rate,
            state: Mutex::new(LimiterState {
                tokens: capacity,
                last_refill: Instant::now(),
            }),
        }
    }

    fn acquire(&self, amount: f64) {
        loop {
            let mut state = self.state.lock().unwrap();
            let now = Instant::now();
            let elapsed = now.duration_since(state.last_refill).as_secs_f64();

            // Refill tokens
            state.tokens = (state.tokens + elapsed * self.refill_rate).min(self.capacity);
            state.last_refill = now;

            if state.tokens >= amount {
                state.tokens -= amount;
                return;
            }

            // Calculate wait time
            let deficit = amount - state.tokens;
            let wait_secs = deficit / self.refill_rate;
            // Sleep without holding the lock
            drop(state);
            thread::sleep(Duration::from_secs_f64(wait_secs));
        }
    }

    fn get_tokens(&self) -> f64 {
        let state = self.state.lock().unwrap();
        let now = Instant::now();
        let elapsed = now.duration_since(state.last_refill).as_secs_f64();

        // Refill but don't update state to just peek
        let current_tokens = (state.tokens + elapsed * self.refill_rate).min(self.capacity);
        current_tokens
    }
}
