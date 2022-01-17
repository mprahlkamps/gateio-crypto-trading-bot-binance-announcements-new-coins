import re
from unittest import TestCase
from unittest.mock import MagicMock

import pytest
import requests
from requests import HTTPError


def mock_announcement_json():
    return {
        "items": [
            {"title": "Creditcoin(CTC) Gets Listed on KuCoin!"},
            {"title": "Notice Regarding the KuCoin App Push System Upgrade"},
            {"title": "KuCoin Opens UnMarshal (MARSH) Deposit Service"},
        ]
    }


@pytest.mark.skip(reason="re-enable these tests once logging is more test-friendly")
class KucoinScraperTest(TestCase):
    def setUp(self):
        from gateio_new_coins_announcements_bot.announcement_scrapers.kucoin_scraper import KucoinScraper

        self.mock_network_client = MagicMock()
        self.scraper = KucoinScraper(http_client=self.mock_network_client)

    def test_returns_announcement_if_request_is_success(self):
        self.mock_network_client.get.return_value.status_code = 200
        self.mock_network_client.get.return_value.json = MagicMock(return_value=mock_announcement_json())

        assert self.scraper.fetch_latest_announcement() == "Creditcoin(CTC) Gets Listed on KuCoin!"

        server_url = self.mock_network_client.get.call_args.args[0]
        assert re.match(r"^https://www.kucoin.com/_api", server_url)
        assert re.search(r"pageSize=[0-9]+", server_url)
        assert "page=1" in server_url
        assert "category=listing" in server_url
        assert "lang=en_US" in server_url

    def test_throws_when_http_client_throws(self):
        self.mock_network_client.get.side_effect = requests.exceptions.ConnectionError("boom!")

        with pytest.raises(requests.exceptions.ConnectionError):
            self.scraper.fetch_latest_announcement()

    def test_throws_with_bad_http_status(self):
        self.mock_network_client.get.return_value.status_code = 429
        self.mock_network_client.get.return_value.text = ""

        mock_error = HTTPError("429 Client Error: Too Many Requests")
        self.mock_network_client.get.return_value.raise_for_status = MagicMock(side_effect=mock_error)

        with pytest.raises(requests.exceptions.HTTPError):
            self.scraper.fetch_latest_announcement()

    def test_logs_when_cache_is_hit(self):
        self.mock_network_client.get.return_value.status_code = 200
        self.mock_network_client.get.return_value.json = MagicMock(return_value=mock_announcement_json())
        self.mock_network_client.get.return_value.headers = {}

        with self.assertLogs("gateio_new_coins_announcements_bot.logger", level="DEBUG") as captured:
            self.scraper.fetch_latest_announcement()

        assert "DEBUG:gateio_new_coins_announcements_bot.logger:Hit the source directly (no cache)" in captured.output

    def test_logs_when_cache_is_missed(self):
        self.mock_network_client.get.return_value.status_code = 200
        self.mock_network_client.get.return_value.json = MagicMock(return_value=mock_announcement_json())
        self.mock_network_client.get.return_value.headers = {"X-Cache": "abcde12345"}

        with self.assertLogs("gateio_new_coins_announcements_bot.logger", level="DEBUG") as captured:
            self.scraper.fetch_latest_announcement()

        assert (
            "DEBUG:gateio_new_coins_announcements_bot.logger:Response was cached. Contains headers X-Cache: abcde12345"
            in captured.output
        )
