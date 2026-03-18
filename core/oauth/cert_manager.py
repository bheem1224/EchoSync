import os
from pathlib import Path
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from datetime import timedelta

from time_utils import utc_now
from core.tiered_logger import get_logger

logger = get_logger("cert_manager")

def ensure_ssl_certs(data_dir: str = "data") -> tuple[str, str]:
    """
    Generates self-signed SSL certificates for the OAuth sidecar if they do not exist.

    Args:
        data_dir: The base data directory where the `ssl` folder will be created.

    Returns:
        A tuple of (cert_path, key_path)
    """
    ssl_dir = Path(data_dir) / "ssl"
    ssl_dir.mkdir(parents=True, exist_ok=True)

    cert_path = ssl_dir / "cert.pem"
    key_path = ssl_dir / "key.pem"

    if cert_path.exists() and key_path.exists():
        logger.debug(f"SSL certificates already exist at {ssl_dir}")
        return str(cert_path), str(key_path)

    logger.info("Generating self-signed SSL certificates for OAuth sidecar...")

    try:
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # Generate public certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "SoulSync"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ])

        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            utc_now()
        ).not_valid_after(
            # Certificate valid for 10 years
            utc_now() + timedelta(days=3650)
        ).add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost")]),
            critical=False,
        ).sign(private_key, hashes.SHA256())

        # Write private key to disk
        with open(key_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))

        # Write certificate to disk
        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        logger.info(f"Successfully generated SSL certificates at {ssl_dir}")
        return str(cert_path), str(key_path)

    except Exception as e:
        logger.error(f"Failed to generate SSL certificates: {e}", exc_info=True)
        raise RuntimeError(f"Certificate generation failed: {e}")
