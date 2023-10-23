from unittest import TestCase, main
import encrypt.signature as es
import os
import pathlib
from pgpy import PGPKey, PGPSignature, PGPUID
from pgpy.constants import (
    PubKeyAlgorithm,
    KeyFlags,
    HashAlgorithm,
    SymmetricKeyAlgorithm,
    CompressionAlgorithm,
    KeyServerPreferences,
    EllipticCurveOID,
)


class TestSignature(TestCase):
    def test_sign_file(self):
        TEST_DIR = os.path.join(pathlib.Path(__file__).parent, "testdata", "sign")
        es.save_key(TEST_DIR, "John Doe", email="john.doe@example.com")

        es.sign_file(
            os.path.join(TEST_DIR, "sample.txt"),
            os.path.join(TEST_DIR, "private_key.asc"),
        )

        public_key, _ = PGPKey.from_file(os.path.join(TEST_DIR, "public_key.asc"))

        with open(os.path.join(TEST_DIR, "sample.txt"), "r") as f:
            sample = f.read()

        self.assertTrue(
            public_key.verify(
                sample,
                PGPSignature.from_file(os.path.join(TEST_DIR, "sample.txt.sig")),
            )
        )


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


if __name__ == "__main__":
    main()
