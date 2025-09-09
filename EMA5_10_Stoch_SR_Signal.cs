//----------
// EMA5_10_Stoch_SR_Signal.cs
// cTrader cBot skeleton
//----------

// Uses daily timeframe and manual SR inputs. 
// Set autoTrade = false for signal-only.

/* cTrader notes

cTrader uses Symbol.PipValue and Symbol.PipSize — check your broker for XAUUSD units.

AutoTrade=false will only print signals; set AutoTrade=true to have the bot place trades. Test on demo first.
*/

using System;
using cAlgo.API;
using cAlgo.API.Internals;

namespace cAlgo.Robots
{
    [Robot(TimeZone = TimeZones.UTC, AccessRights = AccessRights.None)]
    public class EMA5_10_Stoch_SR_EOD : Robot
    {
        [Parameter("EMA Fast", DefaultValue = 5)]
        public int EMAFast { get; set; }
        [Parameter("EMA Slow", DefaultValue = 10)]
        public int EMASlow { get; set; }
        [Parameter("Stoch K", DefaultValue = 14)]
        public int StoK { get; set; }
        [Parameter("Stoch D", DefaultValue = 3)]
        public int StoD { get; set; }
        [Parameter("Risk %", DefaultValue = 1.0)]
        public double RiskPercent { get; set; }
        [Parameter("Auto Trade", DefaultValue = false)]
        public bool AutoTrade { get; set; }
        [Parameter("SR1 (0=off)", DefaultValue = 0.0)]
        public double SR1 { get; set; }
        [Parameter("SR2 (0=off)", DefaultValue = 0.0)]
        public double SR2 { get; set; }
        [Parameter("SR3 (0=off)", DefaultValue = 0.0)]
        public double SR3 { get; set; }
        [Parameter("SR4 (0=off)", DefaultValue = 0.0)]
        public double SR4 { get; set; }
        [Parameter("Near SR tol %", DefaultValue = 0.5)]
        public double NearSRTolPct { get; set; }
        [Parameter("Allow counter trend", DefaultValue = false)]
        public bool AllowCounterTrend { get; set; }
        [Parameter("TP (R multiples)", DefaultValue = 2.0)]
        public double TP_R { get; set; }

        private ExponentialMovingAverage emaFast;
        private ExponentialMovingAverage emaSlow;
        private StochasticOscillator stoch;

        protected override void OnStart()
        {
            emaFast = Indicators.ExponentialMovingAverage(MarketSeries.Close, EMAFast);
            emaSlow = Indicators.ExponentialMovingAverage(MarketSeries.Close, EMASlow);
            stoch = Indicators.StochasticOscillator(Samples: StoK, SmoothK: 3, SampleD: StoD);
        }

        protected override void OnBar()
        {
            // Only operate on completed daily bars
            if (MarketSeries.TimeFrame != TimeFrame.Daily) return;

            int last = MarketSeries.Close.Count - 2; // last closed bar index
            double ef = emaFast.Result[last];
            double es = emaSlow.Result[last];

            double k = stoch.PercentK[last];
            double d = stoch.PercentD[last];
            double kPrev = stoch.PercentK[last-1];
            double dPrev = stoch.PercentD[last-1];

            bool bull = ef > es;
            bool bear = ef < es;
            bool stochUp = (kPrev < dPrev) && (k > d);
            bool stochDown = (kPrev > dPrev) && (k < d);

            double price = MarketSeries.Close[last];
            bool nearSR = IsNearSR(price);

            bool buy = (AllowCounterTrend || bull) && stochUp && nearSR;
            bool sell = (AllowCounterTrend || bear) && stochDown && nearSR;

            if (buy)
            {
                Print("BUY signal at close: {0} price={1}", Symbol.Code, price);
                if (AutoTrade) PlaceTrade(true, price);
            }
            if (sell)
            {
                Print("SELL signal at close: {0} price={1}", Symbol.Code, price);
                if (AutoTrade) PlaceTrade(false, price);
            }
        }

        private bool IsNearSR(double price)
        {
            double[] arr = new double[] { SR1, SR2, SR3, SR4 };
            foreach (var s in arr)
            {
                if (s <= 0) continue;
                double tol = price * (NearSRTolPct / 100.0);
                if (Math.Abs(price - s) <= tol) return true;
            }
            return false;
        }

        private double GetNearestSR(double price, bool isBuy)
        {
            double[] arr = new double[] { SR1, SR2, SR3, SR4 };
            double best = 0;
            double minDist = double.MaxValue;
            foreach (var s in arr)
            {
                if (s <= 0) continue;
                double d = Math.Abs(price - s);
                if (d < minDist) { minDist = d; best = s; }
            }
            if (best == 0) return 0;
            if (isBuy && best >= price)
            {
                // find below
                double alt = 0; minDist = double.MaxValue;
                foreach (var s in arr) if (s>0 && s<price && Math.Abs(price-s)<minDist) { minDist=Math.Abs(price-s); alt=s; }
                if (alt>0) best = alt;
            }
            if (!isBuy && best <= price)
            {
                double alt = 0; minDist = double.MaxValue;
                foreach (var s in arr) if (s>0 && s>price && Math.Abs(price-s)<minDist) { minDist=Math.Abs(price-s); alt=s; }
                if (alt>0) best = alt;
            }
            return best;
        }

        private void PlaceTrade(bool isBuy, double price)
        {
            double sr = GetNearestSR(price, isBuy);
            if (sr <= 0) { Print("No valid SL -> skip trade"); return; }
            double stopDist = Math.Abs(price - sr);
            // compute volume: simplistic method using account balance and pip value
            double riskMoney = Account.Balance * (RiskPercent / 100.0);
            double pipValue = Symbol.PipValue;
            if (pipValue <= 0) pipValue = 1.0;
            double volume = riskMoney / (stopDist / Symbol.PipSize * pipValue);
            double minVol = Symbol.VolumeMin;
            double step = Symbol.VolumeStep;
            volume = Math.Max(minVol, Math.Floor(volume / step) * step);
            if (volume < minVol) volume = minVol;

            TradeType type = isBuy ? TradeType.Buy : TradeType.Sell;
            var result = ExecuteMarketOrder(type, Symbol, volume, "EMA5_10_Stoch");
            if (!result.IsSuccessful) Print("Trade failed: ", result.Error);
            else
            {
                Print("Order executed ticket=", result.Order.Id);
                // set TP/SL via modify
                double R = isBuy ? (price - sr) : (sr - price);
                double tpPrice = isBuy ? price + TP_R * R : price - TP_R * R;
                var pos = result.Position;
                if (pos != null) ModifyPosition(pos, sr, tpPrice);
            }
        }
    }
}
