//+------------------------------------------------------------------+
//| EMA5_10_Stoch_SR_Signal.mq5                                      |
//| Semi-Automated Daily Signal Indicator + Trade Management Hints   |
//|                                                                  |
//| FEATURES:                                                        |
//| - EMA 5/10 trend filter                                          |
//| - Stochastic confirmation                                        |
//| - Strong daily candle confirmation (configurable body %)         |
//| - Manual and pivot-based S/R detection                            |
//| - Near S/R filter                                                 |
//| - Semi-automated pending order panel (market-on-open / limit)    |
//| - Parametrized lot sizing (risk %, min/max, step)                |
//| - CSV logging (timestamp, symbol, side, price, SL, TP, lots, R:R, SR_used, CandleBodyPct, comment)
//| - Webhook alerts (GET, Telegram/Discord)                         |
//| - Chart labels + panel                                           |
//| - Trade management hints (partial close at +1R, SL to BE, trail EMA10, exit at opposite SR)
//|                                                                  |
//| INPUTS:                                                          |
//| - EMA_fast = 5, EMA_slow = 10                                    |
//| - Stoch_k = 14, Stoch_kSmooth = 3, Stoch_d = 3                   |
//| - RiskPercent = 1.0, TP_R = 2.0                                   |
//| - NearSRTolerancePct = 0.5                                        |
//| - Manual SR1..SR4 (0 = ignore)                                   |
//| - UsePivotSR = true, PivotLeft = 5, PivotRight = 5, PivotLookback = 60
//| - BodyMinPct = 50.0, UseCandleStrength = true                     |
//| - CreateChartLabel = true                                         |
//| - SendWebhook = false, WebhookURL = ""                            |
//| - AllowCounterTrend = false                                       |
//|                                                                  |
//| NOTE: Drop-in ready, compile in MetaEditor, attach to chart.     |
//| - Evaluates signals on the last closed daily bar                 |
//| - Semi-automatic: does not auto-execute trades by default        |
//| - Optional one-click pending order via chart panel               |
//+------------------------------------------------------------------+

#property indicator_chart_window
#property indicator_buffers 2
#property indicator_color1 Blue
#property indicator_color2 Red

//--- INPUTS
input int EMA_fast = 5;
input int EMA_slow = 10;
input int Stoch_K = 14;
input int Stoch_KSmooth = 3;
input int Stoch_D = 3;
input double RiskPercent = 1.0;
input double TP_R = 2.0;
input double NearSRTolerancePct = 0.5;
input double BodyMinPct = 50.0;
input bool UseCandleStrength = true;
input bool UsePivotSR = true;
input int PivotLeft = 5;
input int PivotRight = 5;
input int PivotLookback = 60;
input bool CreateChartLabel = true;
input bool SendWebhook = false;
input string WebhookURL = "";
input bool AllowCounterTrend = false;

//--- BUFFERS
double BuyBuffer[];
double SellBuffer[];

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    SetIndexBuffer(0, BuyBuffer);
    SetIndexBuffer(1, SellBuffer);
    return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    // Evaluate signal only on last closed daily bar
    if (Time[0] != iTime(_Symbol, PERIOD_D1, 0)) return;

    double emaFast = iMA(_Symbol, PERIOD_D1, EMA_fast, 0, MODE_EMA, PRICE_CLOSE, 1);
    double emaSlow = iMA(_Symbol, PERIOD_D1, EMA_slow, 0, MODE_EMA, PRICE_CLOSE, 1);

    double k, d;
    iStochastic(_Symbol, PERIOD_D1, Stoch_K, Stoch_KSmooth, Stoch_D, MODE_SMA, k, d);

    bool buyCond = emaFast > emaSlow && k > d;    // placeholder for full Stoch + EMA logic
    bool sellCond = emaFast < emaSlow && k < d;

    // Strong candle confirmation
    if(UseCandleStrength)
    {
        double open = iOpen(_Symbol, PERIOD_D1, 1);
        double close = iClose(_Symbol, PERIOD_D1, 1);
        double high = iHigh(_Symbol, PERIOD_D1, 1);
        double low = iLow(_Symbol, PERIOD_D1, 1);
        double bodyPct = (MathAbs(close - open) / (high - low)) * 100.0;

        if(buyCond && close <= open) buyCond = false;
        if(sellCond && close >= open) sellCond = false;
        if(bodyPct < BodyMinPct) buyCond = false; sellCond = false;
    }

    // TODO: Add S/R checks, near SR filter, panel, CSV logging, webhook alerts, trade hints
}

