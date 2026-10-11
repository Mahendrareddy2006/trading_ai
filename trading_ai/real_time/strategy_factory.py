from trading_ai.real_time.strategies.ema_strategy import EMAStrategy

def get_strategy(name="ema"):

    if name == "ema":
        return EMAStrategy()

    # Future:
    # if name == "rsi":
    #     return RSIStrategy()

    raise ValueError("Unknown strategy")