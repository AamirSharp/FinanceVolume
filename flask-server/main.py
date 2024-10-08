from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import pandas as pd
import numpy as np

app = Flask(__name__)
CORS(app)

@app.route("/api/fetch-data", methods=['POST'])
def fetch_data():
    data = request.json
    symbol = data.get('symbol', 'AAPL')
    interval = data.get('interval', '1min')
    percentile_threshold = data.get('percentile', 85) # Use 'percentile' to match frontend

    intraday_data = fetch_intraday_data(symbol, interval, api_key='TGQGRHVPX6C32IDI')

    if f"Time Series ({interval})" in intraday_data:
        volumes_by_minute = analyze_buy_sell_volume_by_minute(intraday_data, interval, percentile_threshold)
        if volumes_by_minute:
            return jsonify(volumes_by_minute)
        else:
            return jsonify({"message": "No significant trades found."})
    else:
        return jsonify({"message": "No intraday data available for the selected timeframe."})

def fetch_intraday_data(symbol, interval, api_key):
    url = f'https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={symbol}&interval={interval}&apikey={api_key}'
    response = requests.get(url)
    data = response.json()
    print(data)  # Print the data to debug
    return data


def analyze_buy_sell_volume_by_minute(data, interval, percentile_threshold):
    volumes_by_minute = []
    previous_close = None
    key = f"Time Series ({interval})"
    volumes = []

    if key in data:
        for time, price_data in sorted(data[key].items()):
            try:
                close = float(price_data['4. close'])
                volume = int(price_data['5. volume'])
            except KeyError:
                continue  # Skip this entry if key is missing

            volumes.append(volume)

            if previous_close is not None:
                if close > previous_close:
                    buy_volume = volume
                    sell_volume = 0
                elif close < previous_close:
                    buy_volume = 0
                    sell_volume = volume
                else:
                    buy_volume = volume / 2
                    sell_volume = volume / 2

                volumes_by_minute.append({
                    'time': time,
                    'buy_volume': buy_volume,
                    'sell_volume': sell_volume
                })

            previous_close = close
    else:
        return []

    threshold = np.percentile(volumes, percentile_threshold)

    significant_volumes = [
        volume for volume in volumes_by_minute 
        if volume['buy_volume'] > threshold or volume['sell_volume'] > threshold
    ]

    average_buy_volume = np.mean([vol['buy_volume'] for vol in significant_volumes if vol['buy_volume'] > 0])
    average_sell_volume = np.mean([vol['sell_volume'] for vol in significant_volumes if vol['sell_volume'] > 0])

    for volume in significant_volumes:
        if volume['buy_volume'] > 0:
            diff = volume['buy_volume'] - average_buy_volume
            volume['comparison'] = f"{round(diff)} more than average"
        elif volume['sell_volume'] > 0:
            diff = volume['sell_volume'] - average_sell_volume
            volume['comparison'] = f"{round(diff)} more than average"

    return significant_volumes


if __name__ == "__main__":
    app.run(debug=True, port=8080)
