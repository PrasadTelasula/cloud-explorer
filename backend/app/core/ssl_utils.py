"""
SSL certificate generation utilities for development
"""
import os
from pathlib import Path
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core.config import settings


def generate_self_signed_cert(cert_dir: str = "certs") -> tuple[str, str]:
    """
    Generate self-signed SSL certificate for development
    
    Args:
        cert_dir: Directory to store certificates
    
    Returns:
        Tuple of (cert_path, key_path)
    """
    # Create certificates directory
    cert_path = Path(cert_dir)
    cert_path.mkdir(exist_ok=True)
    
    cert_file = cert_path / "cert.pem"
    key_file = cert_path / "key.pem"
    
    # Skip if certificates already exist and are valid
    if cert_file.exists() and key_file.exists():
        try:
            # Check if certificate is still valid (not expired)
            with open(cert_file, 'rb') as f:
                cert = x509.load_pem_x509_certificate(f.read())
                if cert.not_valid_after > datetime.utcnow():
                    print(f"Using existing SSL certificates: {cert_file}, {key_file}")
                    return str(cert_file), str(key_file)
        except Exception:
            pass  # Generate new certificates if existing ones are invalid
    
    print("Generating new self-signed SSL certificates for development...")
    
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    
    # Create certificate subject
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Development"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Local"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Cloud Explorer Development"),
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
    ])
    
    # Create certificate
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.utcnow()
    ).not_valid_after(
        datetime.utcnow() + timedelta(days=365)  # Valid for 1 year
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName("localhost"),
            x509.DNSName("127.0.0.1"),
            x509.IPAddress("127.0.0.1".encode()),
        ]),
        critical=False,
    ).add_extension(
        x509.BasicConstraints(ca=True, path_length=0),
        critical=True,
    ).add_extension(
        x509.KeyUsage(
            key_cert_sign=True,
            key_encipherment=True,
            digital_signature=True,
            content_commitment=False,
            data_encipherment=False,
            key_agreement=False,
            crl_sign=False,
            encipher_only=False,
            decipher_only=False,
        ),
        critical=True,
    ).sign(private_key, hashes.SHA256())
    
    # Write private key
    with open(key_file, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    
    # Write certificate
    with open(cert_file, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    
    # Set appropriate permissions
    os.chmod(key_file, 0o600)  # Private key should be readable only by owner
    os.chmod(cert_file, 0o644)  # Certificate can be readable by others
    
    print(f"Generated SSL certificate: {cert_file}")
    print(f"Generated SSL private key: {key_file}")
    print("Note: These are self-signed certificates for development only!")
    print("Your browser will show a security warning - this is expected.")
    
    return str(cert_file), str(key_file)


def get_ssl_context() -> tuple[str, str] | None:
    """
    Get SSL context for HTTPS server
    
    Returns:
        Tuple of (cert_path, key_path) or None if HTTPS disabled
    """
    if not settings.HTTPS_ENABLED:
        return None
    
    # Use configured paths or generate new certificates
    cert_path = settings.SSL_CERT_PATH
    key_path = settings.SSL_KEY_PATH
    
    # Check if configured certificates exist
    if os.path.exists(cert_path) and os.path.exists(key_path):
        return cert_path, key_path
    
    # Generate self-signed certificates
    return generate_self_signed_cert()


def setup_https_redirect_middleware():
    """
    Setup middleware to redirect HTTP to HTTPS in production
    """
    from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
    return HTTPSRedirectMiddleware if settings.HTTPS_ENABLED and not settings.is_development else None
