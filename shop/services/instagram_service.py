from shop.services.instagram_poller import InstagramPoller


class InstagramService:
    def __init__(self) -> None:
        self.poller = InstagramPoller()

    @property
    def client(self):
        return self.poller.client

    @property
    def is_configured(self) -> bool:
        return self.poller.is_configured

    def poll_once(self) -> dict:
        return self.poller.poll_once()

    def warmup(self) -> None:
        self.poller.warmup()

    def get_status(self) -> dict:
        return self.poller.get_status()
