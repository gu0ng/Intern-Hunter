class WebLoaderDisabled:
    """V1 intentionally avoids automated recruiting-site crawling."""

    def load(self, url: str) -> str:
        raise NotImplementedError("V1 only supports manually pasted JD text.")

