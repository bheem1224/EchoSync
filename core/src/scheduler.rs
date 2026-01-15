use pyo3::prelude::*;
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;
use std::collections::{HashMap, HashSet};
use cron::Schedule;
use std::str::FromStr;
use chrono::Utc;
use log::{info, error, warn};

#[pyclass]
#[derive(Clone)]
pub struct Scheduler {
    jobs: Arc<Mutex<Vec<Arc<Job>>>>,
    running: Arc<Mutex<bool>>,
    running_jobs: Arc<Mutex<HashMap<String, Vec<String>>>>, // Job Name -> Tags
}

struct Job {
    name: String,
    schedule: Schedule,
    func: Py<PyAny>,
    tags: Vec<String>,
    next_run: Mutex<Option<chrono::DateTime<Utc>>>,
}

#[pymethods]
impl Scheduler {
    #[new]
    fn new() -> Self {
        Scheduler {
            jobs: Arc::new(Mutex::new(Vec::new())),
            running: Arc::new(Mutex::new(false)),
            running_jobs: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    fn register_job(&self, name: String, cron_expression: String, func: Py<PyAny>, tags: Vec<String>) -> PyResult<()> {
        let schedule = Schedule::from_str(&cron_expression)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Invalid cron expression: {}", e)))?;

        let mut jobs = self.jobs.lock().unwrap();
        // Calculate initial next_run
        let next_run = schedule.upcoming(Utc).next();

        jobs.push(Arc::new(Job {
            name: name.clone(),
            schedule,
            func,
            tags,
            next_run: Mutex::new(next_run),
        }));
        info!("Registered job: {}", name);
        Ok(())
    }

    fn start(&self) {
        let mut running = self.running.lock().unwrap();
        if *running {
            return;
        }
        *running = true;
        drop(running);

        let scheduler = self.clone();
        thread::spawn(move || {
            scheduler.run_loop();
        });
        info!("Scheduler started");
    }

    fn stop(&self) {
        let mut running = self.running.lock().unwrap();
        *running = false;
        info!("Scheduler stopped");
    }
}

impl Scheduler {
    fn run_loop(&self) {
        loop {
            // Check if we should stop
            {
                let running = self.running.lock().unwrap();
                if !*running {
                    break;
                }
            }

            let now = Utc::now();

            // Scope for jobs lock
            {
                let jobs = self.jobs.lock().unwrap();
                for job in jobs.iter() {
                    let mut next_run_guard = job.next_run.lock().unwrap();

                    if let Some(next) = *next_run_guard {
                        if next <= now {
                            // Check locks BEFORE updating schedule
                            if self.can_acquire_locks(&job.tags) {
                                // Update next run
                                *next_run_guard = job.schedule.upcoming(Utc).next();
                                // Release guard before spawning to avoid holding it too long (though spawn is fast)
                                drop(next_run_guard);

                                self.spawn_job(job.clone());
                            } else {
                                warn!("Job {} blocked by locks. Retrying next tick.", job.name);
                                // Do not update next_run, so it remains due
                            }
                        }
                    }
                }
            }

            thread::sleep(Duration::from_millis(500));
        }
    }

    fn can_acquire_locks(&self, tags: &[String]) -> bool {
        let running = self.running_jobs.lock().unwrap();

        for required_tag in tags {
            let (req_res, req_mode) = parse_tag(required_tag);

            for (_, active_tags) in running.iter() {
                for active_tag in active_tags {
                    let (act_res, act_mode) = parse_tag(active_tag);

                    if req_res == act_res {
                        // Conflict logic:
                        // Write vs Write -> Conflict
                        // Write vs Read -> Conflict
                        // Read vs Write -> Conflict
                        // Read vs Read -> Compatible
                        if req_mode == LockMode::Write || act_mode == LockMode::Write {
                            return false;
                        }
                    }
                }
            }
        }
        true
    }

    fn spawn_job(&self, job: Arc<Job>) {
        let running_jobs = self.running_jobs.clone();
        let name = job.name.clone();
        let tags = job.tags.clone();
        // We don't need to clone func, we use the Arc

        // Mark as running
        {
            let mut r = running_jobs.lock().unwrap();
            r.insert(name.clone(), tags.clone());
        }

        thread::spawn(move || {
            info!("Starting job: {}", name);

            Python::with_gil(|py| {
                if let Err(e) = job.func.call0(py) {
                    error!("Job {} failed: {}", name, e);
                    e.print(py);
                }
            });

            info!("Finished job: {}", name);

            // Remove from running
            let mut r = running_jobs.lock().unwrap();
            r.remove(&name);
        });
    }
}

#[derive(PartialEq, Eq, Debug)]
enum LockMode {
    Read,
    Write,
}

fn parse_tag(tag: &str) -> (&str, LockMode) {
    if let Some(res) = tag.strip_prefix("write:") {
        (res, LockMode::Write)
    } else if let Some(res) = tag.strip_prefix("read:") {
        (res, LockMode::Read)
    } else {
        (tag, LockMode::Read) // Default to shared/read
    }
}
