import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = ["Times New Roman", "serif"]
plt.rcParams["font.size"] = 12


def load_timeseries(substation, metric, db_path, start_date, end_date):
    conn = sqlite3.connect(db_path)
    query = f"""
        SELECT timestamp, {metric}
        FROM modbus_logs
        WHERE device_name = ?
          AND timestamp BETWEEN ? AND ?
        ORDER BY timestamp ASC
    """
    df = pd.read_sql_query(query, conn, params=(substation, start_date, end_date))
    conn.close()

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df.set_index("timestamp", inplace=True)
    return df


def wmape(y_true, y_pred):
    mask = ~np.isnan(y_true) & ~np.isnan(y_pred)
    if mask.sum() == 0:
        return np.nan
    return np.sum(np.abs(y_true[mask] - y_pred[mask])) / np.sum(np.abs(y_true[mask]))


def mae(y_true, y_pred):
    mask = ~np.isnan(y_true) & ~np.isnan(y_pred)
    if mask.sum() == 0:
        return np.nan
    return np.mean(np.abs(y_true[mask] - y_pred[mask]))

def evaluate_baselines(df):
    series = df.iloc[:, 0]  # assume single metric column
    
    daily_pred = series.shift(96) 
    daily_wmape = wmape(series[96:], daily_pred[96:])
    
    weekly_pred = series.shift(96 * 7)
    weekly_wmape = wmape(series[672:], weekly_pred[672:])
    
    return {
        "daily_wmape": daily_wmape,
        "weekly_wmape": weekly_wmape
    }




class BaseModel:
    def __init__(self, name):
        self.name = name

    def train(self, series: pd.Series):
        raise NotImplementedError

    def predict(self, timestamps: pd.DatetimeIndex) -> pd.Series:
        raise NotImplementedError

    def test(self, verification_data: pd.DataFrame):
        y_true = verification_data.iloc[:, 0]
        y_pred = self.predict(verification_data.index)

        abs_error = np.abs(y_true.values - y_pred.values)
        abs_true = np.abs(y_true.values)

        step_errors = pd.DataFrame({
            "timestamp": verification_data.index,
            "y_true": y_true.values,
            "y_pred": y_pred.values,
            "abs_error": abs_error,
            "ape": abs_error / np.where(abs_true == 0, np.nan, abs_true)
        })

        # Progressive WMAPE
        cumsum_abs_error = np.cumsum(abs_error)
        cumsum_abs_true = np.cumsum(abs_true)
        step_errors["wmape_progressive"] = cumsum_abs_error / np.where(cumsum_abs_true == 0, np.nan, cumsum_abs_true)

        return {
            "wmape_total": wmape(y_true.values, y_pred.values),
            "mae_total": mae(y_true.values, y_pred.values),
            "step_errors": step_errors
        }

class LastValueModel(BaseModel):
    def __init__(self):
        super().__init__("LastValue")
        self.last_value = None

    def train(self, series: pd.Series):
        self.last_value = series.dropna().iloc[-1]

    def predict(self, timestamps: pd.DatetimeIndex) -> pd.Series:
        return pd.Series(self.last_value, index=timestamps)

class MovingAverageModel(BaseModel):
    def __init__(self, window=24):
        super().__init__(f"MovingAverage({window})")
        self.mean_value = None
        self.window = window

    def train(self, series: pd.Series):
        self.mean_value = series.dropna().tail(self.window).mean()

    def predict(self, timestamps: pd.DatetimeIndex) -> pd.Series:
        return pd.Series(self.mean_value, index=timestamps)
    
class SeasonalNaiveModel(BaseModel):
    def __init__(self, season_lag=96):
        super().__init__(f"SeasonalNaive(lag={season_lag})")
        self.season_lag = season_lag
        self.history = None

    def train(self, series: pd.Series):
        self.history = series

    def predict(self, timestamps: pd.DatetimeIndex) -> pd.Series:
        if self.history is None or len(self.history) < self.season_lag:
            return pd.Series(self.history.dropna().iloc[-1], index=timestamps)

        preds = []
        for ts in timestamps:
            lag_ts = ts - pd.Timedelta(minutes=15 * self.season_lag)
            if lag_ts in self.history.index:
                preds.append(self.history.loc[lag_ts])
            else:
                preds.append(self.history.dropna().iloc[-1])  
        return pd.Series(preds, index=timestamps)
    
def specialised_accuracy_testing(subs_to_test, db_path, models,
                                 training_windows=["day", "week", "month", "year"], outage_days=3):

    results = []

    base_start = datetime(2023, 10, 1, 0, 0, 0)
    base_end = datetime(2024, 10, 1, 0, 0, 0)

    for sub in subs_to_test:
        for model in models:
            for window in training_windows:

                if window == "day":
                    delta = relativedelta(days=1)
                elif window == "week":
                    delta = relativedelta(weeks=1)
                elif window == "month":
                    delta = relativedelta(months=1)
                elif window == "year":
                    delta = relativedelta(years=1)
                else:
                    raise ValueError(f"Unsupported window: {window}")

                train_end = base_end.replace(hour=0, minute=0, second=0)
                train_start = train_end - delta

                training_data = load_timeseries(sub, "power_apparent", db_path, train_start, train_end)

                verify_end = train_end + relativedelta(days=outage_days)
                verification_data = load_timeseries(sub, "power_apparent", db_path, train_end, verify_end)

                if training_data.empty or verification_data.empty:
                    continue

                model.train(training_data.iloc[:, 0])
                metrics = model.test(verification_data)

                results.append({
                    "model": model.name,
                    "training_window": window,
                    "substation": sub,
                    "wmape_total": metrics["wmape_total"],
                    "mae_total": metrics["mae_total"],
                    "step_errors": metrics["step_errors"]
                })

    return results
 
class LastWeekReplayModel(BaseModel):
    def __init__(self):
        super().__init__("LastWeekReplay")
        self.history = None  # full training series

    def train(self, series: pd.Series):
        # Store training history
        self.history = series.dropna().copy()

    def predict(self, timestamps: pd.DatetimeIndex) -> pd.Series:
        if self.history is None:
            raise RuntimeError("Model not trained.")

        preds = []
        extended_history = self.history.copy()

        for ts in timestamps:
            lag_ts = ts - pd.Timedelta(weeks=1)

            if lag_ts in extended_history.index:
                # Use whatever we have for that timestamp (training or earlier prediction)
                preds.append(extended_history.loc[lag_ts])
            else:
                # Fallback: use last known real value
                preds.append(extended_history.dropna().iloc[-1])

            # IMPORTANT: update extended history with this new prediction
            extended_history.loc[ts] = preds[-1]

        return pd.Series(preds, index=timestamps)


class LastDayReplayModel(BaseModel):
    def __init__(self):
        super().__init__("LastDayReplay")
        self.history = None  # full training series

    def train(self, series: pd.Series):
        # Keep all available history (non-null)
        self.history = series.dropna().copy()

    def predict(self, timestamps: pd.DatetimeIndex) -> pd.Series:
        if self.history is None:
            raise RuntimeError("Model not trained.")

        preds = []
        extended_history = self.history.copy()

        for ts in timestamps:
            lag_ts = ts - pd.Timedelta(days=1)

            if lag_ts in extended_history.index:
                preds.append(extended_history.loc[lag_ts])
            else:
                # fallback: use last known real value from history
                preds.append(extended_history.dropna().iloc[-1])

            # update extended history with this new prediction
            extended_history.loc[ts] = preds[-1]

        return pd.Series(preds, index=timestamps)

if __name__ == "__main__":
    models = [
        LastValueModel(),
        #MovingAverageModel(window=1),
        #MovingAverageModel(window=2),
        MovingAverageModel(window=4),
        #MovingAverageModel(window=4),
        MovingAverageModel(window=96),
        # MovingAverageModel(window=2*96),
        # MovingAverageModel(window=3*96),
        # SarimaModel(),
        # SeasonalNaiveModel(),
        # SeasonalNaiveModel(2*96),
        # SeasonalNaiveModel(3*96),
        # SeasonalNaiveModel(5*96),
        # SeasonalNaiveModel(7*96),
        LastWeekReplayModel(),
        LastDayReplayModel(),
        # MLPForecastModel(48),
        #MLPForecastModel(),
        # MLPForecastModel(128, 192),
    ]

    subs = [
        "100800",
        # "100900",
        # "101000",
        # "101500",
        # "101700",
        # "101800",
        # "102000",
        # "102101",
        # "102102",
        # "102300"
    ]
    db_path = "../sensitive/modbus_data.db"

    res = specialised_accuracy_testing(subs, db_path, models, training_windows=["month"], outage_days=1)

    for sub in subs:
        plt.figure(figsize=(12, 6))

        for r in res:
            if r["substation"] != sub:
                continue

            step_errors = r["step_errors"]
            wmape_step = step_errors["wmape_progressive"].values
            timestamps = np.linspace(0, 24, num=len(wmape_step))

            label = f"{r['model']} ({r['training_window']})"
            plt.plot(timestamps, wmape_step * 100, label=label, alpha=0.8)

        plt.title(f"Error Creep over Verification Period")
        plt.xlabel("Hour of Outage (h)")
        plt.ylabel("Progressive wMAPE (%)")
        
        plt.axhline(10, color='red', label="10% Error Cutoff")
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.show()

    # for sub in subs:
    #     df = load_timeseries(sub, "power_apparent", db_path, "2024-01-01", "2024-06-30")
    #     results = evaluate_baselines(df)
    #     print(results)
        