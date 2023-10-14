from unittest import TestCase, main
import encrypt.signature as es
import os
import pathlib
from pgpy import PGPKey, PGPSignature


class TestSignature(TestCase):
    def test_verify_signature(self):
        content = "This is the data to be signed"

        private_key, public_key = es.generate_key_pair(
            "John Doe", "john.doe@example.com"
        )

        message = es.sign(content, private_key)

        self.assertTrue(public_key.verify(message))

    def test_sign_file(self):
        TEST_DIR = os.path.join(pathlib.Path(__file__).parent, "testdata", "sign")
        es.save_key("John Doe", "john.doe@example.com", TEST_DIR)

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


if __name__ == "__main__":
    main()
