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
import os


def save_key(name: str, email: str, save_folder: str | os.PathLike[str]):
    private_key, public_key = generate_key_pair(name, email)
    with open(os.path.join(save_folder, "private_key.asc"), "w") as f:
        f.write(str(private_key))

    with open(os.path.join(save_folder, "public_key.asc"), "w") as f:
        f.write(str(public_key))


def sign_file(
    file_path: str | os.PathLike[str], private_key_path: str | os.PathLike[str]
):
    with open(private_key_path, "r") as f:
        private_key_data = f.read()

    private_key, _ = PGPKey.from_blob(private_key_data)

    with open(file_path, "r") as f:
        file_data = f.read()

    signed_data = private_key.sign(file_data)

    # TODO: 引数からファイル名を読み取って出力する署名のファイル名を動的に設定
    with open("sample_signed.txt", "w") as f:
        f.write(str(signed_data))


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
