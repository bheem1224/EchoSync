use std::fs;
use std::io::{self, ErrorKind};
use std::path::Path;

/// High-throughput filesystem operations handling EXDEV cross-device renames.
pub struct FsOperations;

impl FsOperations {
    /// Atomic file move with fallback for cross-device/ZFS/Docker mounts (EXDEV).
    pub fn safe_move<P: AsRef<Path>, Q: AsRef<Path>>(src: P, dst: Q) -> io::Result<()> {
        let src_path = src.as_ref();
        let dst_path = dst.as_ref();

        if let Some(parent) = dst_path.parent() {
            if !parent.exists() {
                fs::create_dir_all(parent)?;
            }
        }

        // Attempt direct atomic OS rename first
        match fs::rename(src_path, dst_path) {
            Ok(()) => Ok(()),
            Err(err) => {
                let is_exdev = err.kind() == ErrorKind::CrossesDevices
                    || err.raw_os_error() == Some(18);

                if is_exdev {
                    // Fallback to chunked copy + remove for cross-device dataset mounts
                    fs::copy(src_path, dst_path)?;
                    fs::remove_file(src_path)?;
                    Ok(())
                } else {
                    Err(err)
                }
            }
        }
    }

    /// High-speed file copy, creating parent directories if missing.
    pub fn copy_file<P: AsRef<Path>, Q: AsRef<Path>>(src: P, dst: Q) -> io::Result<u64> {
        let src_path = src.as_ref();
        let dst_path = dst.as_ref();

        if let Some(parent) = dst_path.parent() {
            if !parent.exists() {
                fs::create_dir_all(parent)?;
            }
        }

        fs::copy(src_path, dst_path)
    }

    /// Safely remove file if it exists.
    pub fn delete_file<P: AsRef<Path>>(path: P) -> io::Result<()> {
        let p = path.as_ref();
        if p.exists() {
            fs::remove_file(p)?;
        }
        Ok(())
    }
}
