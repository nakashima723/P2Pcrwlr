from unittest import TestCase, main
import encrypt.signature as es
import os
import pathlib


class TestSignature(TestCase):
    def test_verify_signature(self):
        content = "This is the data to be signed"

        private_key, public_key = es.generate_key_pair(
            "John Doe", "john.doe@example.com"
        )

        message = es.sign(content, private_key)

        self.assertTrue(public_key.verify(message))

    def test_generate_key_pair(self):
        # 現状、実行のみでassertしていない
        TEST_DIR = os.path.join(pathlib.Path(__file__).parent, "testdata", "sign")
        private_key, public_key = es.generate_key_pair(
            "John Doe", "john.doe@example.com"
        )

        with open(os.path.join(TEST_DIR, "private_key.asc"), "w") as f:
            f.write(str(private_key))

        with open(os.path.join(TEST_DIR, "public_key.asc"), "w") as f:
            f.write(str(public_key))


if __name__ == "__main__":
    main()
