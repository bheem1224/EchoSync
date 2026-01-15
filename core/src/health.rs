use pyo3::prelude::*;
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use rusqlite::Connection;
use reqwest::blocking::Client; // Using blocking client to return HashMap directly without async complexity in Python

#[pyclass]
pub struct HealthMonitor {
    targets: Arc<Mutex<HashMap<String, String>>>,
    client: Client,
}

#[pymethods]
impl HealthMonitor {
    #[new]
    fn new() -> Self {
        let mut targets = HashMap::new();
        targets.insert("internet".to_string(), "https://8.8.8.8".to_string()); // 8.8.8.8 doesn't respond to GET usually, but maybe ping?
        // Prompt says "internet" -> "8.8.8.8". HTTP GET to IP might fail if no server.
        // Google DNS is 8.8.8.8.
        // Better check: http://google.com or http://1.1.1.1
        // But let's follow prompt example or use a reliable HTTP endpoint.
        // "8.8.8.8" is usually for ICMP. Reqwest is HTTP.
        // Let's use "https://www.google.com" for internet check,
        // OR stick to prompt if it implies just mapping.
        // Prompt: 'new(): Initializes with default checks (e.g., "internet" -> "8.8.8.8")'
        // If I try to GET https://8.8.8.8, it will likely timeout or fail SSL.
        // I'll use "https://connectivitycheck.gstatic.com/generate_204" which is standard.
        // Or if prompt meant the KEY is internet and VALUE is 8.8.8.8, and I implement ICMP?
        // Prompt says "Pings all registered URLs concurrently (using tokio or reqwest)".
        // "reqwest" implies HTTP.
        // I'll use a reliable HTTP URL for "internet".
        targets.insert("internet".to_string(), "https://www.google.com".to_string());

        HealthMonitor {
            targets: Arc::new(Mutex::new(targets)),
            client: Client::builder().timeout(std::time::Duration::from_secs(5)).build().unwrap(),
        }
    }

    fn register_target(&self, name: String, url: String) {
        let mut t = self.targets.lock().unwrap();
        t.insert(name, url);
    }

    fn check_database(&self, path: String) -> bool {
        match Connection::open(&path) {
            Ok(conn) => {
                // Try a simple query
                conn.query_row("SELECT 1", [], |_| Ok(())).is_ok()
            },
            Err(_) => false,
        }
    }

    fn check_all(&self) -> HashMap<String, bool> {
        // "Pings all registered URLs concurrently"
        // Since we are returning a sync HashMap, we can use Rayon (parallel iterator) or just threads.
        // Reqwest blocking client is thread safe (Arc internally).
        // Or we can use `std::thread::spawn`.
        // Given the list is likely small, threads are fine.

        let targets = {
            let t = self.targets.lock().unwrap();
            t.clone()
        };

        let mut handles = vec![];
        let client = self.client.clone();

        for (name, url) in targets {
            let c = client.clone();
            let handle = std::thread::spawn(move || {
                let res = c.get(&url).send();
                let status = res.is_ok() && res.unwrap().status().is_success();
                (name, status)
            });
            handles.push(handle);
        }

        let mut results = HashMap::new();
        for h in handles {
            if let Ok((name, status)) = h.join() {
                results.insert(name, status);
            }
        }

        results
    }
}
