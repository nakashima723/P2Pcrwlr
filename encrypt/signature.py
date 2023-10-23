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


def save_key(
    save_folder: str | os.PathLike[str],
    name: str,
    comment: str = "",
    email: str = "",
):
    """
    指定されたフォルダにPGP鍵（秘密鍵と公開鍵のペア）を作成する。

    Parameters
    ----------
    save_folder : str | os.PathLike[str]
        PGP鍵を保存するフォルダのパス。
    name: str
        PGP鍵のユーザIDを構成するための、作成者の名前。
    comment: str
        PGP鍵のユーザIDに付与するコメント。
    email: str
        PGP鍵のユーザIDを構成するためのメールアドレス。
    """
    private_key, public_key = generate_key_pair(name, comment, email)
    with open(os.path.join(save_folder, "private_key.asc"), "w") as f:
        f.write(str(private_key))

    with open(os.path.join(save_folder, "public_key.asc"), "w") as f:
        f.write(str(public_key))


def sign_file(
    file_path: str | os.PathLike[str], private_key_path: str | os.PathLike[str]
):
    """
    指定されたファイルに、指定した秘密鍵で署名する。

    Parameters
    ----------
    file_path: str
        署名対象のファイルのパス。
    private_key_path: str
        署名に用いる秘密鍵ファイルのパス。
    """
    with open(private_key_path, "r") as f:
        private_key_data = f.read()

    private_key, _ = PGPKey.from_blob(private_key_data)

    with open(file_path, "r") as f:
        file_data = f.read()

    signed_data = private_key.sign(file_data)

    folder = os.path.dirname(file_path)
    filename = os.path.basename(file_path)
    with open(os.path.join(folder, filename + ".sig"), "w") as f:
        f.write(str(signed_data))


def generate_key_pair(name: str, comment: str, email: str) -> tuple[PGPKey, PGPKey]:
    """
    与えられた引数からPGP鍵（秘密鍵と公開鍵のペア）を返す。

    Parameters
    ----------
    name: str
        PGP鍵のユーザIDを構成するための、作成者の名前。
    comment: str
        PGP鍵のユーザIDに付与するコメント。
    email: str
        PGP鍵のユーザIDを構成するためのメールアドレス。

    Returns
    ----------
    tuple[PGPKey, PGPKey]
        PGP公開鍵と秘密鍵の組。
    """
    # 秘密鍵の生成 (EdDSA)
    key = PGPKey.new(PubKeyAlgorithm.EdDSA, EllipticCurveOID.Ed25519)

    uid = PGPUID.new(name, comment=comment, email=email)
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
    """
    与えられた文字列に、与えられたPGP鍵によって署名し、署名されたPGPMessageを返却する。

    Parameters
    ----------
    content : str
        署名対象の文字列。
    key: PGPKey
        署名に用いるPGP鍵。

    Returns
    ----------
    PGPMessage
        署名が付与されたPGPMessage。
    """
    message = PGPMessage.new(content)
    message |= key.sign(message, hash=HashAlgorithm.SHA256)

    return message
