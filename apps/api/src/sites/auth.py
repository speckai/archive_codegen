import base64
from datetime import datetime

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from pydantic import BaseModel


class SitesToken(BaseModel):
    user_id: str
    expires: datetime
    ip: str


def encrypt_message(message: str, public_key_pem: str) -> bytes:
    """
    Encrypts a message using the provided public key.

    :param message: The message to encrypt as a string.
    :param public_key_pem: The public key in PEM format as a string.
    :return: The encrypted message as bytes.
    """
    # Load the public key
    public_key = serialization.load_pem_public_key(
        public_key_pem.encode("utf-8"), backend=default_backend()
    )

    # Encrypt the message
    encrypted_message = public_key.encrypt(
        message.encode("utf-8"),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

    b64_message = base64.b64encode(encrypted_message).decode("utf-8")

    return b64_message
