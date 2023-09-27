from Crypto.PublicKey import ECC
from Crypto.Signature import eddsa
from Crypto.Hash import SHA512


def generate_key_pair() -> tuple[ECC.EccKey, ECC.EccKey]:
    private_key = ECC.generate(curve="ed25519")
    return (private_key, private_key.public_key())


def sign(private_key, text):
    h = SHA512.new(text.encode("utf-8"))
    signer = eddsa.new(private_key, "rfc8032")
    signature = signer.sign(h)
    return signature


def verify(public_key, text, signature):
    h = SHA512.new(text.encode("utf-8"))
    verifier = eddsa.new(public_key, "rfc8032")
    try:
        verifier.verify(h, signature)
        return True
    except ValueError:
        return False
