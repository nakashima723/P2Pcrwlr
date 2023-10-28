import os
from pgpy import PGPKey


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
    with open(private_key_path, "rb") as f:
        private_key_data = f.read()

    private_key, _ = PGPKey.from_blob(private_key_data)

    with open(file_path, "rb") as f:
        file_data = f.read()

    signed_data = private_key.sign(file_data)

    folder = os.path.dirname(file_path)
    filename = os.path.basename(file_path)
    with open(os.path.join(folder, filename + ".sig"), "wb") as f:
        f.write(signed_data.__bytes__())
