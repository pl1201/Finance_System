//+------------------------------------------------------------------+
//| SwingPivotExport.mq5                                              |
//| Cùng quy tắc Python swing_pivot v1.1.0 (nến ĐÃ ĐÓNG).             |
//| Chạy script trên chart → ghi CSV vào MQL5/Files.                  |
//| Không dùng nến index 0 (đang hình thành, series MT5).             |
//+------------------------------------------------------------------+
#property copyright "Market Structure Lab"
#property version   "1.10"
#property script_show_inputs

input int    InpLeft = 3;
input int    InpRight = 3;
input double InpEqTol = 0.0;
input double InpBosBuffer = 0.0;
input bool   InpEnableChoch = true;

int OnStart()
  {
   int rates_total = Bars(_Symbol, _Period);
   if(rates_total < InpLeft + InpRight + 2)
     {
      Print("Không đủ nến.");
      return(0);
     }

   datetime t[];
   double o[], h[], l[], c[];
   ArraySetAsSeries(t, false);
   ArraySetAsSeries(o, false);
   ArraySetAsSeries(h, false);
   ArraySetAsSeries(l, false);
   ArraySetAsSeries(c, false);
   int n = CopyTime(_Symbol, _Period, 1, rates_total - 1, t);  // bỏ nến 0 đang chạy
   CopyOpen(_Symbol, _Period, 1, n, o);
   CopyHigh(_Symbol, _Period, 1, n, h);
   CopyLow(_Symbol, _Period, 1, n, l);
   CopyClose(_Symbol, _Period, 1, n, c);
   if(n <= 0)
      return(0);

   string fname = "swing_pivot_1.1.0_" + _Symbol + ".csv";
   int fh = FileOpen(fname, FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
   if(fh == INVALID_HANDLE)
     {
      Print("Không ghi được file.");
      return(0);
     }
   FileWrite(fh, "structure_type", "event_bar_index", "confirmed_bar_index",
             "price", "event_id", "algorithm_version", "symbol", "timeframe");

   // Trạng thái giống Python (rút gọn): pivot strict + BOS close + CHoCH khi bias.
   int lastHighIdx = -1;
   int lastLowIdx = -1;
   double lastHighPx = 0, lastLowPx = 0;
   string lastHighLabel = "", lastLowLabel = "";
   string bias = "none";
   int lastHH = -1, lastHL = -1, lastLH = -1, lastLL = -1;
   bool highBroken[];
   bool lowBroken[];
   ArrayResize(highBroken, n);
   ArrayResize(lowBroken, n);
   ArrayInitialize(highBroken, false);
   ArrayInitialize(lowBroken, false);
   int highIds[], lowIds[];
   double highPx[], lowPx[];
   int nHigh = 0, nLow = 0;

   for(int i = 0; i < n; i++)
     {
      int cand = i - InpRight;
      if(cand >= InpLeft)
        {
         bool isH = true, isL = true;
         for(int j = cand - InpLeft; j <= cand + InpRight; j++)
           {
            if(j == cand) continue;
            if(h[j] >= h[cand]) isH = false;
            if(l[j] <= l[cand]) isL = false;
           }
         if(isH)
           {
            string eid = StringFormat("SWING_HIGH@%d>%d", cand, i);
            FileWrite(fh, "SWING_HIGH", cand, i, h[cand], eid, "1.1.0", _Symbol, EnumToString(_Period));
            if(lastHighIdx >= 0)
              {
               string lab = "EQH";
               if(h[cand] > lastHighPx + InpEqTol) lab = "HH";
               else if(h[cand] < lastHighPx - InpEqTol) lab = "LH";
               FileWrite(fh, lab, cand, i, h[cand], lab + StringFormat("@%d>%d", cand, i), "1.1.0", _Symbol, EnumToString(_Period));
               lastHighLabel = lab;
               if(lab == "HH") lastHH = nHigh;
               if(lab == "LH") lastLH = nHigh;
               if(lastHighLabel == "HH" && lastLowLabel == "HL") bias = "bullish";
               if(lastHighLabel == "LH" && lastLowLabel == "LL") bias = "bearish";
               if(lastHighLabel == "HH" && lastLowLabel == "LL") bias = "none";
              }
            ArrayResize(highPx, nHigh + 1);
            ArrayResize(highIds, nHigh + 1);
            highPx[nHigh] = h[cand];
            highIds[nHigh] = cand;
            nHigh++;
            lastHighIdx = cand;
            lastHighPx = h[cand];
           }
         if(isL)
           {
            string eid = StringFormat("SWING_LOW@%d>%d", cand, i);
            FileWrite(fh, "SWING_LOW", cand, i, l[cand], eid, "1.1.0", _Symbol, EnumToString(_Period));
            if(lastLowIdx >= 0)
              {
               string lab = "EQL";
               if(l[cand] > lastLowPx + InpEqTol) lab = "HL";
               else if(l[cand] < lastLowPx - InpEqTol) lab = "LL";
               FileWrite(fh, lab, cand, i, l[cand], lab + StringFormat("@%d>%d", cand, i), "1.1.0", _Symbol, EnumToString(_Period));
               lastLowLabel = lab;
               if(lab == "HL") lastHL = nLow;
               if(lab == "LL") lastLL = nLow;
               if(lastHighLabel == "HH" && lastLowLabel == "HL") bias = "bullish";
               if(lastHighLabel == "LH" && lastLowLabel == "LL") bias = "bearish";
               if(lastHighLabel == "HH" && lastLowLabel == "LL") bias = "none";
              }
            ArrayResize(lowPx, nLow + 1);
            ArrayResize(lowIds, nLow + 1);
            lowPx[nLow] = l[cand];
            lowIds[nLow] = cand;
            nLow++;
            lastLowIdx = cand;
            lastLowPx = l[cand];
           }
        }

      // BOS/CHoCH theo close, mức active = swing cùng phía mới nhất chưa phá.
      int actH = -1;
      for(int k = nHigh - 1; k >= 0; k--)
         if(!highBroken[k]) { actH = k; break; }
      if(actH >= 0 && c[i] > highPx[actH] + InpBosBuffer)
        {
         string typ = "BOS_UP";
         if(InpEnableChoch && bias != "none")
           {
            bool major = false;
            if(bias == "bullish" && lastHH >= 0 && actH == lastHH) major = true;
            if(bias == "bearish" && lastLH >= 0 && actH == lastLH) major = true;
            if(bias == "bullish" && lastHH >= 0 && c[i] > highPx[lastHH] + InpBosBuffer) major = true;
            if(bias == "bearish" && lastLH >= 0 && c[i] > highPx[lastLH] + InpBosBuffer) major = true;
            if(bias == "bearish" && major) typ = "CHOCH_UP";
            else if(bias == "bullish" && major) typ = "BOS_UP";
            else typ = "BOS_INTERNAL_UP";
           }
         string eid = StringFormat("%s@%d>%d", typ, i, i);
         FileWrite(fh, typ, i, i, highPx[actH], eid, "1.1.0", _Symbol, EnumToString(_Period));
         for(int k = 0; k < nHigh; k++)
            if(!highBroken[k] && c[i] > highPx[k] + InpBosBuffer)
               highBroken[k] = true;
         if(typ == "CHOCH_UP")
           {
            bias = "bullish";
            lastHighLabel = ""; lastLowLabel = "";
            lastHH = lastHL = lastLH = lastLL = -1;
           }
        }

      int actL = -1;
      for(int k = nLow - 1; k >= 0; k--)
         if(!lowBroken[k]) { actL = k; break; }
      if(actL >= 0 && c[i] < lowPx[actL] - InpBosBuffer)
        {
         string typ = "BOS_DOWN";
         if(InpEnableChoch && bias != "none")
           {
            bool major = false;
            if(bias == "bearish" && lastLL >= 0 && actL == lastLL) major = true;
            if(bias == "bullish" && lastHL >= 0 && actL == lastHL) major = true;
            if(bias == "bearish" && lastLL >= 0 && c[i] < lowPx[lastLL] - InpBosBuffer) major = true;
            if(bias == "bullish" && lastHL >= 0 && c[i] < lowPx[lastHL] - InpBosBuffer) major = true;
            if(bias == "bullish" && major) typ = "CHOCH_DOWN";
            else if(bias == "bearish" && major) typ = "BOS_DOWN";
            else typ = "BOS_INTERNAL_DOWN";
           }
         string eid = StringFormat("%s@%d>%d", typ, i, i);
         FileWrite(fh, typ, i, i, lowPx[actL], eid, "1.1.0", _Symbol, EnumToString(_Period));
         for(int k = 0; k < nLow; k++)
            if(!lowBroken[k] && c[i] < lowPx[k] - InpBosBuffer)
               lowBroken[k] = true;
         if(typ == "CHOCH_DOWN")
           {
            bias = "bearish";
            lastHighLabel = ""; lastLowLabel = "";
            lastHH = lastHL = lastLH = lastLL = -1;
           }
        }
     }

   FileClose(fh);
   Print("Đã ghi ", fname, " (", n, " nến đóng). Bỏ nến đang hình thành.");
   return(0);
  }
