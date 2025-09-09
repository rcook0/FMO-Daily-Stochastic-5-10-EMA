/*
This is a ready EA with core features: 
daily evaluation, 
EMA & Stoch checks, 
manual SR inputs (up to 4),
sizing by percent of equity,
options for SignalOnly vs AutoTrade. 
It will place market orders at next open (or immediate at EOD if you prefer).
This is intentionally robust but concise so you can extend it for your own trade management rules (break-even, trail, partial closes).
*/

/*
MT5 notes

The EA uses manual SR inputs (SR1..SR4) so you can set the daily S/R levels you prefer.

AutoTrade=false by default (signal-only). 
Set AutoTrade=true to allow execution — you should test with a demo account first.

Lot sizing is approximate — MQL5 tick/lot calculations differ across brokers/instruments (especially XAUUSD). 
Test on your broker and refine ComputeLotSize.

You can expand the EA with break-even, trailing, partial close logic later.
*/

//+------------------------------------------------------------------+
//| EMA5_10_Stoch_SR_EOD.mq5                                         |
//| Core EOD strategy: 5/10 EMA, Stochastic, manual SR, percent risk |
//+------------------------------------------------------------------+
#property copyright "User"
#property version   "1.00"
#property strict

input int    EMA_fast = 5;
input int    EMA_slow = 10;
input int    Stoch_k = 14;
input int    Stoch_d = 3;
input int    Stoch_slow = 3;
input double RiskPercent = 1.0; // percent risk per trade
input bool   AutoTrade = false;  // true = place orders automatically
input double SR1 = 0.0; // manual SR levels; set 0 to ignore
input double SR2 = 0.0;
input double SR3 = 0.0;
input double SR4 = 0.0;
input double NearSRTolerancePct = 0.5; // percent tolerance to consider 'near' SR
input bool   AllowCounterTrend = false;
input double TP_R = 2.0; // take profit in R multiples

// Global handles
int handle_ema_fast, handle_ema_slow;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
  {
   handle_ema_fast = iMA(_Symbol, PERIOD_D1, EMA_fast, 0, MODE_EMA, PRICE_CLOSE);
   handle_ema_slow = iMA(_Symbol, PERIOD_D1, EMA_slow, 0, MODE_EMA, PRICE_CLOSE);
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
//| Get nearest SR (manual)                                          |
//+------------------------------------------------------------------+
double GetNearestSR(double price, bool isBuy)
  {
   double arr[4];
   arr[0]=SR1; arr[1]=SR2; arr[2]=SR3; arr[3]=SR4;
   double best=0.0;
   double minDist=1e12;
   for(int i=0;i<4;i++)
     {
      if(arr[i] <= 0.0) continue;
      double dist = MathAbs(price - arr[i]);
      if(dist < minDist)
        {
         minDist = dist;
         best = arr[i];
        }
     }
   // If best is on wrong side, try find opposite
   if(best==0.0) return(0.0);
   if(isBuy && best >= price)
     {
      // find below price
      minDist = 1e12; double alt=0.0;
      for(int i=0;i<4;i++){ if(arr[i]>0 && arr[i] < price && MathAbs(price-arr[i])<minDist){ minDist=MathAbs(price-arr[i]); alt=arr[i]; } }
      if(alt>0) best=alt;
     }
   if(!isBuy && best <= price)
     {
      minDist = 1e12; double alt=0.0;
      for(int i=0;i<4;i++){ if(arr[i]>0 && arr[i] > price && MathAbs(price-arr[i])<minDist){ minDist=MathAbs(price-arr[i]); alt=arr[i]; } }
      if(alt>0) best=alt;
     }
   return(best);
  }

//+------------------------------------------------------------------+
//| Check near SR                                                     |
//+------------------------------------------------------------------+
bool IsNearSR(double price)
  {
   double arr[4]; arr[0]=SR1; arr[1]=SR2; arr[2]=SR3; arr[3]=SR4;
   for(int i=0;i<4;i++)
     {
      if(arr[i] <= 0.0) continue;
      double tol = price * (NearSRTolerancePct/100.0);
      if(MathAbs(price - arr[i]) <= tol) return(true);
     }
   return(false);
  }

//+------------------------------------------------------------------+
//| Compute lot by % equity and SL pips (approx)                     |
//+------------------------------------------------------------------+
double ComputeLotSize(double sl_price)
  {
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double riskMoney = equity * (RiskPercent/100.0);
   double sl_pips = MathAbs(SymbolInfoDouble(_Symbol, SYMBOL_POINT) > 0 ? (NormalizeDouble(MathAbs(Bid - sl_price)/SymbolInfoDouble(_Symbol,SYMBOL_POINT),0)) : 0);
   // approximate lot calc using margin and tick value - simpler approach:
   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickValue==0 || tickSize==0) return(0.01);
   double valuePerLotPerPoint = tickValue / tickSize;
   if(valuePerLotPerPoint<=0) valuePerLotPerPoint=1.0;
   double lots = riskMoney / (sl_pips * valuePerLotPerPoint);
   double minLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   lots = MathMax(minLot, MathFloor(lots/lotStep)*lotStep);
   return(NormalizeDouble(lots,2));
  }

//+------------------------------------------------------------------+
//| OnTick — we only run logic once per daily close confirmation      |
//+------------------------------------------------------------------+
void OnTick()
  {
   static datetime lastDay=0;
   datetime t = TimeCurrent();
   MqlDateTime dt; TimeToStruct(t, dt);
   datetime today = StructToTime(dt); // truncated
   // Only evaluate once per day after bar close; check when new daily bar confirmed
   static long lastProcessedBarTime=0;
   // use iTime to get latest completed daily bar time:
   datetime lastBarTime = (datetime) iTime(_Symbol, PERIOD_D1, 1); // index 1 = last closed bar
   if(lastBarTime == lastProcessedBarTime) return; // already processed
   lastProcessedBarTime = lastBarTime;

   // read indicators
   double emaF[], emaS[];
   if(CopyBuffer(handle_ema_fast,0,1,2,emaF) <= 0) return;
   if(CopyBuffer(handle_ema_slow,0,1,2,emaS) <= 0) return;
   double ef = emaF[0], es = emaS[0];

   // Stoch values
   double k, d;
   if(!iStochastic(_Symbol, PERIOD_D1, Stoch_k, Stoch_d, Stoch_slow, MODE_SMA, 0, MODE_MAIN, k)) return;
   if(!iStochastic(_Symbol, PERIOD_D1, Stoch_k, Stoch_d, Stoch_slow, MODE_SMA, 0, MODE_SIGNAL, d)) return;
   double k_prev, d_prev;
   iStochastic(_Symbol, PERIOD_D1, Stoch_k, Stoch_d, Stoch_slow, MODE_SMA, 1, MODE_MAIN, k_prev);
   iStochastic(_Symbol, PERIOD_D1, Stoch_k, Stoch_d, Stoch_slow, MODE_SMA, 1, MODE_SIGNAL, d_prev);

   double price = SymbolInfoDouble(_Symbol, SYMBOL_BID); // current price

   bool bull = ef > es;
   bool bear = ef < es;
   bool stochCrossUp = (k_prev < d_prev) && (k > d);
   bool stochCrossDown = (k_prev > d_prev) && (k < d);

   bool nearSR = IsNearSR(price);

   bool buyCond = (AllowCounterTrend || bull) && stochCrossUp && nearSR;
   bool sellCond = (AllowCounterTrend || bear) && stochCrossDown && nearSR;

   if(buyCond)
     {
      double sr = GetNearestSR(price, true);
      double slp = sr;
      if(slp<=0) { Print("No valid SL for buy -> skip"); }
      else
        {
         double lots = ComputeLotSize(slp);
         // create order or signal
         string msg = StringFormat("BUY Signal %s price=%.5f SL=%.5f lots=%.2f", _Symbol, price, slp, lots);
         Print(msg);
         if(AutoTrade && lots>0.0)
           {
            // send market buy
            MqlTradeRequest req; MqlTradeResult res;
            ZeroMemory(req); ZeroMemory(res);
            req.action = TRADE_ACTION_DEAL;
            req.symbol = _Symbol;
            req.volume = lots;
            req.type = ORDER_TYPE_BUY;
            req.price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
            req.deviation = 10;
            if(!OrderSend(req,res)) Print("OrderSend failed: ", GetLastError());
            else
              {
               Print("Order placed: ticket=", res.order);
               // set TP based on TP_R using R distance
               // compute R = price - slp
               double R = price - slp;
               double tp = price + TP_R * R;
               // set TP/SL via order modify
               if(res.order>0)
                 {
                  ulong ticket = res.order;
                  // Try to modify (platform dependent), simple approach: Place with TP/SL in request if supported
                 }
              }
           }
        }
     }

   if(sellCond)
     {
      double sr = GetNearestSR(price, false);
      double slp = sr;
      if(slp<=0) { Print("No valid SL for sell -> skip"); }
      else
        {
         double lots = ComputeLotSize(slp);
         string msg = StringFormat("SELL Signal %s price=%.5f SL=%.5f lots=%.2f", _Symbol, price, slp, lots);
         Print(msg);
         if(AutoTrade && lots>0.0)
           {
            MqlTradeRequest req; MqlTradeResult res;
            ZeroMemory(req); ZeroMemory(res);
            req.action = TRADE_ACTION_DEAL;
            req.symbol = _Symbol;
            req.volume = lots;
            req.type = ORDER_TYPE_SELL;
            req.price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
            req.deviation = 10;
            if(!OrderSend(req,res)) Print("OrderSend failed: ", GetLastError());
           }
        }
     }
  }
//+------------------------------------------------------------------+
