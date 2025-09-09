//+------------------------------------------------------------------+
//| EMA5_10_Stoch_SR_Signal.mq5                                      |
//| Semi-automated daily EOD signal + management hints indicator     |
//| - 5 / 10 EMA trend filter                                         |
//| - Stochastic cross confirmation                                    |
//| - Manual or pivot-based SR                                         |
//| - CSV logging and optional webhook (GET)                           |
//+------------------------------------------------------------------+
#property copyright "User"
#property version   "1.00"
#property indicator_chart_window
#property indicator_plots 0

#include <Trade\SymbolInfo.mqh>

//---------------------- Inputs ------------------------------
input int    EMA_fast = 5;
input int    EMA_slow = 10;

input int    Stoch_k = 14;
input int    Stoch_kSmooth = 3; // %K smoothing
input int    Stoch_d = 3;       // %D
input int    Stoch_method = MODE_SMA; // smoothing method for Stoch main (unused in iStochastic call but kept)

input double RiskPercent = 1.0;        // % equity risk per trade suggestion
input double NearSRTolerancePct = 0.5;  // tolerance to consider 'near' SR (percent)
input double TP_R = 2.0;               // TP in R multiples

// Manual SR entries (0 = ignore)
input double SR1 = 0.0;
input double SR2 = 0.0;
input double SR3 = 0.0;
input double SR4 = 0.0;

input bool   UsePivotSR = true;        // when true, detect pivot S/R automatically
input int    PivotLeft = 5;
input int    PivotRight = 5;
input int    PivotLookback = 60;       // how many bars back to search pivots

input bool   CreateChartLabel = true;  // draws label on chart when signal found
input bool   SendWebhook = false;      // enable webhook (GET)
input string WebhookURL = "";          // webhook URL (add in Tools->Options->Expert Advisors)
input string LogFileName = "EMA5_10_signals.csv"; // CSV log in MQL5/Files

input bool   AllowCounterTrend = false; // allow trades counter to EMA bias

//---------------------- Globals ------------------------------
datetime lastProcessedDailyBar = 0;

// Colors / graphics
color buyColor  = clrLime;
color sellColor = clrRed;
int    labelOffset = 30; // px above/below bar for label placement

//---------------------- Utility functions ----------------------
double ArrayOfSR[4];

void FillManualSR()
{
   ArrayOfSR[0] = SR1;
   ArrayOfSR[1] = SR2;
   ArrayOfSR[2] = SR3;
   ArrayOfSR[3] = SR4;
}

// Return true if price is within tolerance % of any SR
bool IsNearSR(double price)
{
   double tol = price * (NearSRTolerancePct/100.0);
   for(int i=0;i<4;i++)
     {
      if(ArrayOfSR[i] <= 0.0) continue;
      if(MathAbs(price - ArrayOfSR[i]) <= tol) return(true);
     }
   return(false);
}

// Find nearest SR on correct side (for buy find SR below price; for sell find SR above price)
double NearestSR(double price, bool isBuy)
{
   double best = 0.0;
   double minDist = 1e18;
   for(int i=0;i<4;i++)
     {
      double s = ArrayOfSR[i];
      if(s <= 0.0) continue;
      if(isBuy && s < price)
        {
         double d = price - s;
         if(d < minDist) { minDist = d; best = s; }
        }
      if(!isBuy && s > price)
        {
         double d = s - price;
         if(d < minDist) { minDist = d; best = s; }
        }
     }
   return(best);
}

// Append line to CSV in MQL5/Files (common folder)
void AppendCSV(string filename, string line)
{
   int handle = FileOpen(filename, FILE_READ|FILE_WRITE|FILE_CSV|FILE_COMMON, ',');
   if(handle == INVALID_HANDLE)
     {
      handle = FileOpen(filename, FILE_WRITE|FILE_CSV|FILE_COMMON, ',');
      if(handle == INVALID_HANDLE)
        {
         Print("Failed to open CSV: ", filename);
         return;
        }
     }
   // move to end
   FileSeek(handle, 0, SEEK_END);
   FileWriteString(handle, line + "\n");
   FileClose(handle);
}

// Send webhook via GET (fallback simple)
void SendWebhookGET(string url, string message)
{
   if(StringLen(url) == 0) return;
   // Build safe GET
   string enc = UrlEncode(message);
   string full = url + (StringFind(url, "?") == -1 ? "?text=" : "&text=") + enc;
   char result[];
   int res = WebRequest("GET", full, "", NULL, 0, result, NULL);
   if(res != 200)
      Print("Webhook GET returned code: ", res, " (may be blocked or URL not listed in WebRequest options).");
}

// Very small UrlEncode for ASCII
string UrlEncode(string s)
{
   string out="";
   for(int i=0;i<StringLen(s);i++)
     {
      uchar c=StringGetCharacter(s, i);
      if((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='-'||c=='_'||c=='.'||c=='~') out+=StringSubstr(s,i,1);
      else out += "%" + IntegerToHex((int)c,2);
     }
   return(out);
}

// Simple lot suggestion based on risk % and distance (approximate).
double SuggestLots(double sl_price)
{
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double riskMoney = equity * (RiskPercent/100.0);
   double price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(sl_price<=0 || riskMoney<=0) return(SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN));

   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);

   // approximate points of SL
   double sl_points = MathAbs((price - sl_price) / point);
   if(sl_points <= 0) return(SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN));
   double valuePerLotPerPoint = 0.0;
   if(tickValue>0 && tickSize>0) valuePerLotPerPoint = tickValue / tickSize;
   if(valuePerLotPerPoint <= 0) valuePerLotPerPoint = 1.0; // fallback

   double lots = riskMoney / (sl_points * valuePerLotPerPoint);
   double minLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(minLot <= 0) minLot = 0.01;
   if(step <= 0) step = minLot;
   // round to step
   double rounded = MathFloor(lots / step) * step;
   if(rounded < minLot) rounded = minLot;
   // clamp to max
   double maxVol = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   if(maxVol > 0 && rounded > maxVol) rounded = maxVol;
   return(NormalizeDouble(rounded, 2));
}

// Draw label on chart
void DrawLabel(string name, int barIndex, string text, color clr, bool above)
{
   // remove if exists
   if(ObjectFind(0, name) != -1) ObjectDelete(0, name);
   double price = above ? High[barIndex] : Low[barIndex];
   int yoff = above ? labelOffset : -labelOffset;
   // create label
   if(!ObjectCreate(0, name, OBJ_LABEL, 0, Time[barIndex], price))
      return;
   ObjectSetInteger(0, name, OBJPROP_CORNER, 0);
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, 10);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, yoff);
   ObjectSetString(0, name, OBJPROP_TEXT, text);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
}

// Find pivot highs and lows; fill manual SR array with top few pivots (descending recency)
void FillPivotSRs()
{
   // collect pivots into a temporary array with distance criterion
   double pivots[];
   ArrayResize(pivots, 0);
   int found = 0;
   // search lookback bars for pivots
   for(int i=PivotLeft;i<PivotLookback;i++)
     {
      double ph = iHigh(_Symbol, PERIOD_D1, iHighest(_Symbol, PERIOD_D1, MODE_HIGH, PivotLeft+PivotRight+1, i-PivotLeft));
      // We'll use iCustom-like simple check using iHigh/iLow pivot function alternatives. Simpler: use iHighest/iLowest on neighborhood.
      bool isHigh = true;
      for(int j=i-PivotLeft;j<=i+PivotRight;j++)
        {
         if(j==i) continue;
         if(High[i] <= High[j]) { isHigh = false; break; }
        }
      if(isHigh)
        {
         // push
         ArrayInsert(pivots, 0, Time[i]); // store time (for sorting) — we will instead store price separately
         found++;
         if(found>=8) break;
        }
     }
   // Simpler approach: use recent swing highs/lows built from builtin pivots
   // Use ta-style pivothigh/low equivalents via iHighest/iLowest
   // We'll fill SRs from recent pivot highs and lows using iPivotHigh/Low helpers:
   int idx=0;
   for(int i=1;i<=PivotLookback && idx<4;i++)
     {
      int phIndex = iBarShift(_Symbol, PERIOD_D1, Time[i]);
      double ph = iHigh(_Symbol, PERIOD_D1, i);
      // check pivot high using neighborhood:
      bool isHigh=true;
      for(int j=i-PivotLeft;j<=i+PivotRight;j++)
        {
         if(j<0) continue;
         if(High[i] <= High[j]) { isHigh=false; break; }
        }
      if(isHigh)
        {
         ArrayOfSR[idx++] = High[i];
         if(idx>=4) break;
        }
      bool isLow=true;
      for(int j=i-PivotLeft;j<=i+PivotRight;j++)
        {
         if(j<0) continue;
         if(Low[i] >= Low[j]) { isLow=false; break; }
        }
      if(isLow && idx<4)
        {
         ArrayOfSR[idx++] = Low[i];
         if(idx>=4) break;
        }
     }
   // remaining slots keep manual SRs if set; we will keep any manual SRs already in ArrayOfSR
}

//+------------------------------------------------------------------+
//| OnInit                                                           |
//+------------------------------------------------------------------+
int OnInit()
  {
   FillManualSR();
   // If pivot SR used and no manual SRs, fill from pivots (best effort)
   if(UsePivotSR)
     {
      // keep manual SRs first; if manual not set, attempt pivot fill
      int manualCount=0;
      for(int i=0;i<4;i++) if(ArrayOfSR[i] > 0) manualCount++;
      if(manualCount < 4)
        {
         // clear the remaining and attempt to fill with pivots
         for(int j=manualCount;j<4;j++) ArrayOfSR[j] = 0.0;
         FillPivotSRs();
        }
     }
   // create CSV header if not present
   int h = FileOpen(LogFileName, FILE_READ|FILE_CSV|FILE_COMMON, ',');
   if(h==INVALID_HANDLE)
     {
      // create and write header
      int h2 = FileOpen(LogFileName, FILE_WRITE|FILE_CSV|FILE_COMMON, ',');
      if(h2 != INVALID_HANDLE)
        {
         FileWriteString(h2, "timestamp,symbol,side,price,sl,tp,lots,R,SR_used,comment\n");
         FileClose(h2);
        }
     }
   // initialize lastProcessedDailyBar
   lastProcessedDailyBar = (datetime) iTime(_Symbol, PERIOD_D1, 1); // last closed bar
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
//| OnDeinit                                                         |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   // nothing for now
  }

//+------------------------------------------------------------------+
//| OnTick - evaluate once per closed daily bar                      |
//+------------------------------------------------------------------+
void OnTick()
  {
   // get last closed daily bar time
   datetime lastClosed = (datetime) iTime(_Symbol, PERIOD_D1, 1);
   if(lastClosed == 0) return;

   if(lastClosed == lastProcessedDailyBar) return; // already processed this bar
   lastProcessedDailyBar = lastClosed;

   // Now evaluate conditions using D1 values
   // EMA
   double emaF = iMA(_Symbol, PERIOD_D1, EMA_fast, 0, MODE_EMA, PRICE_CLOSE, 1); // last closed bar
   double emaS = iMA(_Symbol, PERIOD_D1, EMA_slow, 0, MODE_EMA, PRICE_CLOSE, 1);

   // Stochastic main & signal on closed bar and previous bar
   double k_cur = 0.0, d_cur = 0.0, k_prev=0.0, d_prev=0.0;
   // iStochastic returns values for specified shift; we request index 1 (last closed) and 2 (previous)
   k_cur = iStochastic(_Symbol, PERIOD_D1, Stoch_k, Stoch_kSmooth, Stoch_d, MODE_SMA, MODE_MAIN, 1);
   d_cur = iStochastic(_Symbol, PERIOD_D1, Stoch_k, Stoch_kSmooth, Stoch_d, MODE_SMA, MODE_SIGNAL, 1);
   k_prev = iStochastic(_Symbol, PERIOD_D1, Stoch_k, Stoch_kSmooth, Stoch_d, MODE_SMA, MODE_MAIN, 2);
   d_prev = iStochastic(_Symbol, PERIOD_D1, Stoch_k, Stoch_kSmooth, Stoch_d, MODE_SMA, MODE_SIGNAL, 2);

   // price on close
   double price = iClose(_Symbol, PERIOD_D1, 1);

   // refresh manual SR array
   FillManualSR();
   // if pivot pipeline requested, refresh pivot SRs and merge manual (manual take priority)
   if(UsePivotSR)
     {
      // preserve manual by copying them then filling empty slots with pivots
      double manual[4];
      int mc=0;
      for(int i=0;i<4;i++){ manual[i]=ArrayOfSR[i]; if(manual[i]>0) mc++; }
      // temporarily zero and fill pivots
      for(int i=0;i<4;i++) ArrayOfSR[i]=manual[i];
      FillPivotSRs();
      // If FillPivotSRs set entries into ArrayOfSR they will replace zeros; simple approach used above.
     }

   // near SR?
   bool nearSR = IsNearSR(price);

   bool bull = emaF > emaS;
   bool bear = emaF < emaS;
   bool stochCrossUp = (k_prev < d_prev) && (k_cur > d_cur);
   bool stochCrossDown = (k_prev > d_prev) && (k_cur < d_cur);

   bool buyCond = (AllowCounterTrend || bull) && stochCrossUp && nearSR;
   bool sellCond = (AllowCounterTrend || bear) && stochCrossDown && nearSR;

   // process signals
   if(buyCond || sellCond)
     {
      bool isBuy = buyCond;
      double sr_used = NearestSR(price, isBuy);
      double sl = sr_used;
      double tp = 0.0;
      double Rdist = 0.0;
      if(sl > 0)
        {
         if(isBuy) { Rdist = price - sl; tp = price + TP_R * Rdist; }
         else { Rdist = sl - price; tp = price - TP_R * Rdist; }
        }
      // suggest lots
      double suggestedLots = SuggestLots(sl);

      // compute R:R
      double rr = 0.0;
      if(Rdist > 0) rr = TP_R;

      // compose CSV line
      string side = isBuy ? "BUY" : "SELL";
      string timestamp = TimeToString(lastClosed, TIME_DATE|TIME_MINUTES);
      string csv = StringFormat("%s,%s,%s,%.5f,%.5f,%.5f,%.2f,%.2f,%.5f,%s",
                                timestamp, _Symbol, side, price, sl, tp, suggestedLots, rr, sr_used, "EOD_signal");
      AppendCSV(LogFileName, csv);

      // send webhook if set
      if(SendWebhook && StringLen(WebhookURL) > 0)
        {
         string msg = StringFormat("%s %s signal at %.5f SL=%.5f TP=%.5f lots=%.2f R=%.2f", _Symbol, side, price, sl, tp, suggestedLots, rr);
         SendWebhookGET(WebhookURL, msg);
        }

      // draw label on chart (at the bar where the signal happened)
      if(CreateChartLabel)
        {
         int idx = iBarShift(_Symbol, Period(), lastClosed, false); // find bar index on current chart matching lastClosed
         if(idx < 0) idx = 1; // fallback
         string labName = StringFormat("EOD_SIG_%s_%s", TimeToString(lastClosed, TIME_DATE), side);
         string labText = StringFormat("%s\nPrice: %.5f\nSL: %.5f\nTP: %.5f\nLots: %.2f", side, price, sl, tp, suggestedLots);
         DrawLabel(labName, idx, labText, isBuy ? buyColor : sellColor, isBuy);
        }

      // print management hints to Experts log
      PrintFormat("%s signal on %s: price=%.5f SL=%.5f TP=%.5f lots=%.2f R=%.2f",
                  side, TimeToString(lastClosed, TIME_DATE|TIME_MINUTES), price, sl, tp, suggestedLots, rr);
      PrintFormat("Management hints: At +1R consider partial close or move SL to BE. Trail below 10 EMA or opposite SR.");

     } // end if signal

   else
     {
      // optional: print nothing to avoid noise
      // Print("No valid EOD setup at ", TimeToString(lastClosed, TIME_DATE|TIME_MINUTES));
     }
  }
//+------------------------------------------------------------------+
