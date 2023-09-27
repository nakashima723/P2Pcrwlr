from unittest import TestCase, main
import encrypt.signature as cs


class TestSignature(TestCase):
    def test_verify_signature(self):
        # テキストデータ
        text_to_sign = "This is the data to be signed."

        # キーペアの生成
        private_key, public_key = cs.generate_key_pair()

        # テキストに署名
        signature = cs.sign(private_key, text_to_sign)

        # 署名の検証
        self.assertTrue(cs.verify(public_key, text_to_sign, signature))


if __name__ == "__main__":
    main()
