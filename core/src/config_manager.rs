use std::env;
use std::path::PathBuf;

pub fn get_database_path() -> PathBuf {
    if let Ok(p) = env::var("SOULSYNC_DATA_DIR") {
        PathBuf::from(p).join("music_library.db")
    } else {
        PathBuf::from("data").join("music_library.db")
    }
}
