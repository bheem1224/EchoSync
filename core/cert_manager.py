import os
from pathlib import Path
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import datetime

from core.settings import config_manager
from core.tiered_logger import get_logger

logger = get_logger("cert_manager")

def generate_ssl_certs():
    """Generates a self-signed SSL certificate and key pair if they don't exist.

    The certificates are saved to the 'ssl' subdirectory inside the data directory
    configured by config_manager.

    Returns:
        tuple: (cert_path, key_path) as strings.
    """
    ssl_dir = config_manager.data_dir / 'ssl'

    try:
        ssl_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create SSL directory {ssl_dir}: {e}")
        return None, None

    cert_path = ssl_dir / 'cert.pem'
    key_path = ssl_dir / 'key.pem'

    if cert_path.exists() and key_path.exists():
        logger.debug(f"SSL certificates already exist at {ssl_dir}")
        return str(cert_path), str(key_path)

    logger.info(f"Generating new self-signed SSL certificate at {ssl_dir}")

    try:
        # Generate our key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # Generate a self-signed cert
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"California"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, u"San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"SoulSync"),
            x509.NameAttribute(NameOID.COMMON_NAME, u"soulsync.local"),
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
            datetime.datetime.utcnow()
        ).not_valid_after(
            # Our certificate will be valid for 10 years
            datetime.datetime.utcnow() + datetime.timedelta(days=3650)
        ).add_extension(
            x509.SubjectAlternativeName([x509.DNSName(u"localhost")]),
            critical=False,
        ).sign(private_key, hashes.SHA256())

        # Write our certificate out to disk
        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        # Write our private key out to disk
        with open(key_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            ))

        logger.info(f"Successfully generated self-signed SSL certificate")
        return str(cert_path), str(key_path)

    except Exception as e:
        logger.error(f"Failed to generate SSL certificates: {e}")
        return None, None
