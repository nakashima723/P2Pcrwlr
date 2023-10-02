from pgpy.constants import (
    PubKeyAlgorithm,
    KeyFlags,
    HashAlgorithm,
    SymmetricKeyAlgorithm,
    CompressionAlgorithm,
    KeyServerPreferences,
    EllipticCurveOID,
)
from pgpy import PGPKey, PGPMessage, PGPUID


def generate_key_pair(name: str, email: str) -> tuple[PGPKey, PGPKey]:
    # 秘密鍵の生成 (EdDSA)
    key = PGPKey.new(PubKeyAlgorithm.EdDSA, EllipticCurveOID.Ed25519)

    uid = PGPUID.new(name, email=email)
    key.add_uid(
        uid,
        usage={KeyFlags.Certify, KeyFlags.Sign},
        hashes=[
            HashAlgorithm.SHA512,
            HashAlgorithm.SHA384,
            HashAlgorithm.SHA256,
            HashAlgorithm.SHA224,
        ],
        ciphers=[
            SymmetricKeyAlgorithm.AES256,
            SymmetricKeyAlgorithm.AES192,
            SymmetricKeyAlgorithm.AES128,
        ],
        compressions=[CompressionAlgorithm.Uncompressed],
        keyserver_flags=[KeyServerPreferences.NoModify],
    )
    return (key, key.pubkey)


def sign(content: str, key: PGPKey) -> PGPMessage:
    message = PGPMessage.new(content)
    print(message)
    message |= key.sign(message, hash=HashAlgorithm.SHA256)

    return message
