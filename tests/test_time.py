import ntplib
from unittest import TestCase, main
from unittest.mock import MagicMock
import utils.time as ut


class TestTime(TestCase):
    def test_ntp_exception(self):
        with self.assertRaises(ut.TimeException):
            mock = MagicMock(side_effect=ntplib.NTPException("例外が発生することのテスト"))
            ntplib.NTPClient.request = mock

            ut.fetch_jst()


if __name__ == "__main__":
    main()
