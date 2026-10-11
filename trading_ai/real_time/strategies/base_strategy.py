class BaseStrategy:

    def generate_signal(self, client, symbol):
        """
        Must return:
        ("LONG" or "SHORT" or None, price, confidence)
        """
        raise NotImplementedError("Strategy must implement generate_signal()")