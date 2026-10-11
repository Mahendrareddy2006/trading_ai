import pandas as pd

def analyze():

    try:
        df = pd.read_csv("trade_log.csv")
    except:
        print("No trade log found.")
        return

    closed = df[df["status"] == "CLOSED"]

    if len(closed) == 0:
        print("No closed trades yet.")
        return

    wins = len(closed[closed["result"] == "WIN"])
    losses = len(closed[closed["result"] == "LOSS"])

    win_rate = wins / len(closed) * 100

    print("\n===== PERFORMANCE =====")
    print("Total Closed Trades:", len(closed))
    print("Wins:", wins)
    print("Losses:", losses)
    print("Win Rate:", round(win_rate, 2), "%")

if __name__ == "__main__":
    analyze()