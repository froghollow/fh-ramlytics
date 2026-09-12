import requests
from typing import Any, Dict, Optional, List, Union


class DanelfinAPIError(Exception):
    """Raised when the Danelfin API returns an error response."""
    pass


class DanelfinClient:
    BASE_URL = "https://apirest.danelfin.com"

    def __init__(self, api_key: str, timeout: int = 10):
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"x-api-key": self.api_key})

    # ---------------------------
    # Internal request helper
    # ---------------------------
    def _get(self, path: str, params: Dict[str, Any] = None) -> Any:
        url = f"{self.BASE_URL}{path}"
        response = self.session.get(url, params=params, timeout=self.timeout)
        #response = self.session.get(url, params=params, timeout=self.timeout, verify=False)  # Disable SSL verification TEMPORARILY
        if response.status_code == 404:
            # e.g., RYCEY not found
            print(f"API Warning {response.status_code}: {url} Not Found!")
            return {}
        elif response.status_code != 200:
            raise DanelfinAPIError(
                f"API Error {response.status_code}: {response.text}"
            )

        return response.json()

    # ---------------------------
    # Ranking Endpoint
    # ---------------------------
    def ranking(
        self,
        ticker: Optional[str] = None,
        date: Optional[str] = None,
        aiscore: Optional[int] = None,
        aiscore_min: Optional[int] = None,
        fundamental_min: Optional[int] = None,
        technical_min: Optional[int] = None,
        sentiment_min: Optional[int] = None,
        low_risk_min: Optional[int] = None,
        buy_track_record: Optional[int] = None,
        sell_track_record: Optional[int] = None,
        sector: Optional[str] = None,
        industry: Optional[str] = None,
        asset: Optional[str] = None,
        fields: Optional[str] = None,
        market: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Wrapper for GET /ranking
        """
        params = {
            "ticker": ticker,
            "date": date,
            "aiscore": aiscore,
            "aiscore_min": aiscore_min,
            "fundamental_min": fundamental_min,
            "technical_min": technical_min,
            "sentiment_min": sentiment_min,
            "low_risk_min": low_risk_min,
            "buy_track_record": buy_track_record,
            "sell_track_record": sell_track_record,
            "sector": sector,
            "industry": industry,
            "asset": asset,
            "fields": fields,
            "market": market,
        }

        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}

        return self._get("/ranking", params)

    # ---------------------------
    # Sectors
    # ---------------------------
    def list_sectors(self) -> List[Dict[str, str]]:
        """GET /sectors"""
        return self._get("/sectors")

    def sector_scores(self, slug: str) -> Dict[str, Any]:
        """GET /sectors/{slug}"""
        return self._get(f"/sectors/{slug}")

    # ---------------------------
    # Industries
    # ---------------------------
    def list_industries(self) -> List[Dict[str, str]]:
        """GET /industries"""
        return self._get("/industries")

    def industry_scores(self, slug: str) -> Dict[str, Any]:
        """GET /industries/{slug}"""
        return self._get(f"/industries/{slug}")

    # ---------------------------
    # v3 Endpoints
    # ---------------------------
    def trade_ideas(self) -> List[Dict[str, str]]:
        """GET /v3/trade-ideas"""
        return self._get("/v3/trade-ideas")

    def trading_parameters(self, ticker: str) -> List[Dict[str, str]]:
        """GET /v3/trading-parameters"""
        return self._get(f"/v3/trading-parameters?ticker={ticker}")
    
    def price_forecast(self, ticker: str) -> Dict[str, Any]:
        """GET /v3/price-forecast"""
        return self._get(f"/v3/price-forecast?ticker={ticker}")
    